import logging
import os
import sys
import time
import threading
import math
import queue
from datetime import datetime, timezone, timedelta

import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from gemini_client import GeminiPlanner
from gtfs_loader import GTFSData

try:
    import qwiic_led_stick
except ImportError:
    qwiic_led_stick = None

# --- Rotary Encoder Setup (Adafruit STEMMA QT / Seesaw) ---
try:
    import board
    from adafruit_seesaw import seesaw, rotaryio, digitalio
    
    i2c = board.I2C()
    seesaw_encoder = seesaw.Seesaw(i2c, addr=0x36)  # Default address for STEMMA QT encoder
    
    # Configure the encoder
    seesaw_encoder.pin_mode(24, seesaw_encoder.INPUT_PULLUP)  # Button pin
    encoder = rotaryio.IncrementalEncoder(seesaw_encoder)
    button = digitalio.DigitalIO(seesaw_encoder, 24)
    
    twist_connected = True
    print("STEMMA QT Rotary Encoder connected!")
except ImportError as e:
    print(f"Adafruit Seesaw library not found: {e}")
    twist_connected = False
    encoder = None
    button = None
except Exception as e:
    print(f"Error initializing STEMMA QT encoder: {e}")
    twist_connected = False
    encoder = None
    button = None

# Event queue for frontend polling
encoder_event_queue = queue.Queue()

# --- Encoder Polling Loop ---
def encoder_loop():
    if not twist_connected or encoder is None:
        print("Encoder loop not starting - encoder not connected")
        return
        
    last_position = 0
    last_button = True  # Button is pulled up, so True = not pressed
    loop_iter = 0
    
    print("Encoder polling loop started!")
    
    while True:
        try:
            # Read position (rotation)
            position = encoder.position
            
            # Debug: Print status every 2 seconds (20 iterations) to verify it's alive
            if loop_iter % 20 == 0:
                button_pressed = not button.value  # Inverted because of pullup
                print(f"[Debug] Encoder Position: {position}, Button: {button_pressed}")
            loop_iter += 1

            if position > last_position:
                diff = position - last_position
                print(f"Encoder: Counter-Clockwise (Diff: {diff}, Total: {position})")
                encoder_event_queue.put('ccw')
                last_position = position
            elif position < last_position:
                diff = last_position - position
                print(f"Encoder: Clockwise (Diff: {diff}, Total: {position})")
                encoder_event_queue.put('cw')
                last_position = position
            
            # Read Button (Click) - button.value is False when pressed (pullup)
            button_state = button.value
            if not button_state and last_button:  # Just pressed
                print("Encoder: Click")
                encoder_event_queue.put('click')
            last_button = button_state
                
        except Exception as e:
            print(f"Error reading encoder: {e}")
            
        time.sleep(0.05)  # Poll at 20Hz for smoother response

# Start encoder thread
if twist_connected:
    print("Starting encoder polling thread...")
    enc_thread = threading.Thread(target=encoder_loop, daemon=True)
    enc_thread.start()
    print("Encoder thread started!")
else:
    print("Encoder thread NOT started (twist_connected is False)")


FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))

# Fixed NYC origin (Grand Central Terminal) for all routing.
DEFAULT_ORIGIN = {
    "label": "Grand Central Terminal",
    "lat": 40.7527,
    "lon": -73.9772,
}

WEATHER_CODE_MAP = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Foggy", "🌫"),
    48: ("Foggy", "🌫"),
    51: ("Light drizzle", "🌦"),
    53: ("Drizzle", "🌧"),
    55: ("Heavy drizzle", "🌧"),
    61: ("Light rain", "🌧"),
    63: ("Rain", "🌧"),
    65: ("Heavy rain", "🌧"),
    66: ("Freezing rain", "🌧"),
    67: ("Freezing rain", "🌧"),
    71: ("Snowfall", "❄️"),
    73: ("Snowfall", "❄️"),
    75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "🌨"),
    80: ("Rain showers", "🌦"),
    81: ("Rain showers", "🌦"),
    82: ("Heavy showers", "🌧"),
    85: ("Snow showers", "🌨"),
    86: ("Snow showers", "🌨"),
    95: ("Thunderstorm", "⛈"),
    96: ("Thunderstorm", "⛈"),
    99: ("Thunderstorm", "⛈"),
}


def _to_timestamp(value: str | None) -> float | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
        if "T" in normalized:
            dt = datetime.fromisoformat(normalized)
        else:
            dt = datetime.fromisoformat(f"{normalized}T00:00:00+00:00")
        return dt.timestamp()
    except ValueError:
        return None

# --- Configuration ---
# The SparkX Qwiic LED Stick on the Pi has 10 LEDs.
LED_COUNT = 10 

# Brightness scaling as a human-friendly percent (0-100). Use 10% plus the
# hardware limiter on the stick to keep output modest.
BRIGHTNESS_PERCENT = 10.0
ROUTE_CACHE_TTL = 300  # seconds

# Global state for LEDs
# Each element: {'r': 0, 'g': 0, 'b': 0, 'mode': 'static'}
led_state = [{'r': 0, 'g': 0, 'b': 0, 'mode': 'static'} for _ in range(LED_COUNT)]
last_output = [(None, None, None) for _ in range(LED_COUNT)]
last_error_ts = 0
update_counter = 0
state_lock = threading.Lock()
route_cache: dict[str, dict[str, object]] = {}
cache_lock = threading.Lock()

def _percent_to_scale(brightness_percent: float | int | None = None) -> float:
    """Convert a 0-100 percent to a 0.0-1.0 scale."""
    if brightness_percent is None:
        brightness_percent = BRIGHTNESS_PERCENT
    return max(0.0, min(1.0, float(brightness_percent) / 100.0))

def scale_color(r, g, b, brightness_percent: float | int | None = None):
    """Return RGB tuple scaled by a brightness percent and clamped to 0-255 as ints."""
    brightness_scale = _percent_to_scale(brightness_percent)
    def clamp(v):
        return max(0, min(255, int(v)))
    scaled = (clamp(r * brightness_scale), clamp(g * brightness_scale), clamp(b * brightness_scale))
    return scaled

# --- Initialize Qwiic LED Stick ---
my_stick = None
stick_connected = False

if qwiic_led_stick:
    try:
        my_stick = qwiic_led_stick.QwiicLEDStick()

        if my_stick.begin() == False:
            print("\nThe Qwiic LED Stick isn't connected to the system. Please check your connection", \
                file=sys.stderr)
            stick_connected = False
        else:
            print("\nQwiic LED Stick connected!")
            stick_connected = True
            try:
                # Hardware brightness (0-31). Keep as low as possible.
                my_stick.set_all_LED_brightness(1)
            except Exception as exc:
                print(f"Unable to set hardware brightness: {exc}", file=sys.stderr)
            r, g, b = scale_color(0, 0, 0)
            my_stick.set_all_LED_color(r, g, b) # Turn off all LEDs (scaled)
    except Exception as e:
        print(f"Error initializing Qwiic Stick: {e}")
        stick_connected = False
else:
    print("qwiic_led_stick library not found. Please install it.")
    stick_connected = False


def _ensure_led_stick():
    global stick_connected, my_stick
    if stick_connected:
        return True
    if not qwiic_led_stick:
        return False
    try:
        device = qwiic_led_stick.QwiicLEDStick()
        if device.begin():
            my_stick = device
            stick_connected = True
            # Force re-sync of cached outputs on reconnect.
            global last_output
            last_output = [(None, None, None) for _ in range(LED_COUNT)]
            try:
                my_stick.set_all_LED_brightness(1)
            except Exception as exc:
                print(f"Unable to set hardware brightness on reconnect: {exc}", file=sys.stderr)
            r, g, b = scale_color(0, 0, 0)
            my_stick.set_all_LED_color(r, g, b)
            print("Qwiic LED Stick reconnected!")
            return True
    except Exception as exc:
        print(f"[LED] reconnect failed: {exc}", file=sys.stderr)
    return False


def _set_led_color(idx_1_based: int, r: int, g: int, b: int, attempts: int = 3, delay: float = 0.02):
    """Write a single LED with small retries to survive transient I2C hiccups."""
    global stick_connected
    if not stick_connected:
        return False

    for attempt in range(1, attempts + 1):
        try:
            my_stick.set_single_LED_color(idx_1_based, r, g, b)
            return True
        except OSError as exc:
            print(f"[LED] I2C error LED {idx_1_based} attempt {attempt}/{attempts}: {exc} | colors={r},{g},{b} | BRIGHTNESS_PERCENT={BRIGHTNESS_PERCENT}", file=sys.stderr)
            time.sleep(delay)
            continue
        except Exception as exc:
            print(f"[LED] Unexpected error LED {idx_1_based} attempt {attempt}/{attempts}: {exc} | colors={r},{g},{b} | BRIGHTNESS_PERCENT={BRIGHTNESS_PERCENT}", file=sys.stderr)
            break

    stick_connected = False
    return False

# --- Load supporting services ---
gtfs_data = GTFSData()

load_dotenv()

try:
    gemini_planner = GeminiPlanner()
except Exception as exc:
    print(f"Gemini planner unavailable: {exc}", file=sys.stderr)
    gemini_planner = None


# --- Animation Loop ---
def animation_loop():
    global stick_connected
    while True:
        if not stick_connected:
            ok = _ensure_led_stick()
            if not ok:
                time.sleep(0.2)
                continue

        t = time.time()
        # Breathing effect: sine wave from 0.2 to 1.0 of the target brightness
        fade_factor = (math.sin(t * 3) + 1) / 2 # 0.0 to 1.0, approx 0.5Hz
        
        with state_lock:
            for i, led in enumerate(led_state):
                if i >= LED_COUNT: break
                
                r, g, b = led['r'], led['g'], led['b']
                mode = led.get('mode', 'static')
                
                if mode == 'blink':
                    # Apply fade factor to the brightness (percent-based)
                    current_percent = BRIGHTNESS_PERCENT * (0.2 + 0.8 * fade_factor)
                    r_out, g_out, b_out = scale_color(r, g, b, brightness_percent=current_percent)
                else:
                    r_out, g_out, b_out = scale_color(r, g, b)
                
                # Skip static LEDs that haven't changed to reduce I2C traffic.
                if mode == 'static' and last_output[i] == (r_out, g_out, b_out):
                    continue
                last_output[i] = (r_out, g_out, b_out)

                # Debug log occasionally (e.g. every 5 seconds)
                if i == 0 and int(t * 20) % 100 == 0:
                    print(f"LED 1 (scaled): ({r_out}, {g_out}, {b_out})")

                ok = _set_led_color(i + 1, r_out, g_out, b_out)
                if not ok:
                    print(f"[LED] giving up for now after failed writes; stick_connected={stick_connected}")
                    break
    
        time.sleep(0.1) # Slow down to ease I2C load

# Start animation thread
anim_thread = threading.Thread(target=animation_loop, daemon=True)
anim_thread.start()

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)


# -----------------------
# Subway + Gemini helpers
# -----------------------

def _ensure_gemini_ready():
    if not gemini_planner:
        raise RuntimeError("Gemini client not configured. Set GEMINI_API_KEY first.")


def _build_prompt_variables(payload: dict) -> dict:
    origin = payload.get("origin", {})
    destination = payload.get("destination", {})
    user_context = payload.get("user_context", "")
    maps_instruction = ""

    if payload.get("maps_link"):
        maps_instruction = (
            "Go to this Google Maps URL and return the detailed steps: "
            f"{payload['maps_link']}"
        )

    return {
        "current_time": payload.get("current_time") or datetime.now(timezone.utc).isoformat(),
        "origin_label": origin.get("label", "Unknown location"),
        "origin_lat": origin.get("lat", ""),
        "origin_lon": origin.get("lon", ""),
        "destination_label": destination.get("label", "Destination"),
        "event_start": payload.get("event_start", ""),
        "user_context": user_context,
        "maps_instruction": maps_instruction,
    }


def _merge_with_gtfs(gemini_response: dict, payload: dict) -> dict:
    """Fill missing stops using the static GTFS snapshot when possible."""

    if not gemini_response:
        return gemini_response

    route = gemini_response.get("route") or {}
    stops = route.get("stops") or []

    origin_label = payload.get("origin", {}).get("label")
    destination_label = payload.get("destination", {}).get("label")
    line = (gemini_response.get("next_train") or {}).get("line")

    if (not stops) and origin_label and destination_label and line:
        try:
            gtfs_stops = gtfs_data.stop_sequence_for_route(line, origin_label, destination_label)
        except Exception as exc:
            print(f"GTFS lookup failed: {exc}")
            gtfs_stops = None

        if gtfs_stops:
            route["stops"] = gtfs_stops
            gemini_response["route"] = route

    return gemini_response


def _cache_get(key: str):
    """Return cached route if fresh, otherwise evict."""
    now = time.time()
    with cache_lock:
        entry = route_cache.get(key)
        if not entry:
            return None
        if now - entry.get("ts", 0) > ROUTE_CACHE_TTL:
            route_cache.pop(key, None)
            return None
        return entry.get("value")


def _cache_set(key: str, value: dict):
    with cache_lock:
        route_cache[key] = {"value": value, "ts": time.time()}


def _plan_cache_key(payload: dict) -> str:
    dest_label = (payload.get("destination") or {}).get("label") or ""
    event_start = payload.get("event_start") or ""
    return f"plan|{dest_label.strip().lower()}|{event_start}"


def _maps_cache_key(payload: dict) -> str:
    maps_link = payload.get("maps_link") or ""
    dest_label = (payload.get("destination") or {}).get("label") or ""
    return f"maps|{maps_link}|{dest_label.strip().lower()}"

def _describe_weather(code: int | None) -> tuple[str, str]:
    if code is None:
        return ("Conditions unavailable", "⛅")
    return WEATHER_CODE_MAP.get(code, ("Conditions unknown", "⛅"))


# -----------------------
# API endpoints
# -----------------------


@app.route('/api/config', methods=['GET'])
def get_frontend_config():
    return jsonify({
        "googleClientId": os.environ.get('GOOGLE_CLIENT_ID', ''),
        "defaultDestination": os.environ.get('DEFAULT_DESTINATION', 'Manhattanville 125th St'),
        "geminiModel": os.environ.get('GEMINI_MODEL', 'gemini-3-pro-preview'),
    })


@app.route('/api/weather', methods=['GET'])
def get_weather():
    lat = float(request.args.get('lat', DEFAULT_ORIGIN['lat']))
    lon = float(request.args.get('lon', DEFAULT_ORIGIN['lon']))
    params = {
        'latitude': lat,
        'longitude': lon,
        'current': 'temperature_2m,weather_code',
        'temperature_unit': 'celsius',
    }

    try:
        resp = requests.get('https://api.open-meteo.com/v1/forecast', params=params, timeout=5)
        resp.raise_for_status()
        current = resp.json().get('current') or {}
    except Exception as exc:
        app.logger.error('Weather API error: %s', exc)
        return jsonify({'error': 'Unable to load weather data'}), 502

    temp_c = current.get('temperature_2m')
    code = current.get('weather_code')
    description, icon = _describe_weather(code)
    temp_f = None
    if temp_c is not None:
        temp_f = temp_c * 9 / 5 + 32

    return jsonify({
        'temperature_c': temp_c,
        'temperature_f': temp_f,
        'condition': description,
        'icon': icon,
        'code': code,
    })


@app.route('/api/events/next', methods=['POST'])
def get_next_calendar_event():
    data = request.json or {}
    access_token = data.get('access_token')
    if not access_token:
        return jsonify({'error': 'Missing Google access token'}), 400

    params = {
        'calendarId': 'primary',
        'singleEvents': 'true',
        'orderBy': 'startTime',
        'timeMin': data.get('time_min') or datetime.now(timezone.utc).isoformat(),
        'timeMax': data.get('time_max') or (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        'timeZone': 'America/New_York',
        'maxResults': 50,
    }

    resp = requests.get(
        'https://www.googleapis.com/calendar/v3/calendars/primary/events',
        headers={'Authorization': f'Bearer {access_token}'},
        params=params,
        timeout=10,
    )

    if resp.status_code != 200:
        app.logger.error('Google Calendar API error: %s', resp.text)
        return jsonify({'error': 'Google Calendar API error', 'details': resp.text}), 502

    items = resp.json().get('items', [])
    upcoming_events = []
    for event in items:
        location = event.get('location')
        start = event.get('start', {})
        end = event.get('end', {})
        start_val = start.get('dateTime') or start.get('date')
        end_val = end.get('dateTime') or end.get('date')
        day_key = None
        start_ts = _to_timestamp(start_val)
        if start_val:
            day_key = start_val.split('T')[0]
        upcoming_events.append({
            'id': event.get('id'),
            'summary': event.get('summary'),
            'location': location,
            'has_location': bool(location),
            'start': start_val,
            'end': end_val,
            'start_day': day_key,
            'start_timestamp': start_ts,
        })

    if not upcoming_events:
        return jsonify({'error': 'No upcoming events found'}), 404

    return jsonify({'events': upcoming_events})


@app.route('/api/routes/plan', methods=['POST'])
def plan_route():
    data = request.json or {}
    # Force all plans to originate from Grand Central regardless of client payload.
    data['origin'] = DEFAULT_ORIGIN.copy()
    data['current_time'] = datetime.now(timezone.utc).isoformat()
    cache_key = _plan_cache_key(data)

    cached = _cache_get(cache_key)
    if cached:
        app.logger.info('Serving cached Gemini plan for %s', cache_key)
        return jsonify(cached)

    try:
        _ensure_gemini_ready()
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 500

    if not data.get('destination'):
        return jsonify({'error': 'Destination information missing'}), 400

    try:
        app.logger.info('Gemini plan_route start cache_key=%s dest=%s start=%s', cache_key, data.get("destination"), data.get("event_start"))
        gemini_payload = gemini_planner.plan_route(prompt_variables=_build_prompt_variables(data))
        app.logger.info('Gemini plan response: %s', gemini_payload)
        enriched = _merge_with_gtfs(gemini_payload, data)
        _cache_set(cache_key, enriched)
    except Exception as exc:
        app.logger.exception('Gemini plan_route failed')
        return jsonify({'error': 'Gemini request failed', 'details': str(exc)}), 500

    return jsonify(enriched)


@app.route('/api/routes/detail', methods=['POST'])
def plan_route_from_maps():
    data = request.json or {}
    if not data.get('maps_link'):
        return jsonify({'error': 'maps_link is required'}), 400
    data['current_time'] = datetime.now(timezone.utc).isoformat()
    cache_key = _maps_cache_key(data)

    cached = _cache_get(cache_key)
    if cached:
        app.logger.info('Serving cached Gemini detail for %s', cache_key)
        return jsonify(cached)

    try:
        _ensure_gemini_ready()
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 500

    data.setdefault('destination', {'label': 'Destination'})
    try:
        app.logger.info('Gemini detail start cache_key=%s maps_link=%s', cache_key, data.get("maps_link"))
        gemini_payload = gemini_planner.plan_route(prompt_variables=_build_prompt_variables(data))
        app.logger.info('Gemini detail response: %s', gemini_payload)
        _cache_set(cache_key, gemini_payload)
    except Exception as exc:
        app.logger.exception('Gemini detail request failed')
        return jsonify({'error': 'Gemini request failed', 'details': str(exc)}), 500

    return jsonify(gemini_payload)


@app.route('/update-leds', methods=['POST'])
def update_leds():
    try:
        data = request.json
        # Support both old format (list of colors) and new format (list of dicts)
        payload = data.get('leds', [])
        
        # If 'leds' is missing, check for 'colors' (backward compatibility)
        if not payload and 'colors' in data:
            payload = [{'r': c[0], 'g': c[1], 'b': c[2], 'mode': 'static'} for c in data['colors']]

        print(f"Received {len(payload)} LED updates")
        
        if not stick_connected and not _ensure_led_stick():
            return jsonify({"status": "warning", "message": "LED Stick not connected"}), 200

        with state_lock:
            for i in range(LED_COUNT):
                if i < len(payload):
                    item = payload[i]
                    # Handle if item is just a list [r,g,b] (mixed format safety)
                    if isinstance(item, list):
                         led_state[i] = {'r': item[0], 'g': item[1], 'b': item[2], 'mode': 'static'}
                    else:
                        led_state[i] = {
                            'r': item.get('r', 0),
                            'g': item.get('g', 0),
                            'b': item.get('b', 0),
                            'mode': item.get('mode', 'static')
                        }
                else:
                    # Turn off remaining
                    led_state[i] = {'r': 0, 'g': 0, 'b': 0, 'mode': 'static'}
                # Force next loop to send updated value (even if same as before).
                last_output[i] = (None, None, None)
            global update_counter
            update_counter += 1
            # Log first few LEDs and brightness settings for visibility.
            preview = led_state[: min(3, LED_COUNT)]
            print(f"[LED] update #{update_counter} payload preview={preview} BRIGHTNESS_PERCENT={BRIGHTNESS_PERCENT}")
        
        return jsonify({"status": "success", "message": "LEDs updated"})
        
    except Exception as e:
        print(f"Error updating LEDs: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "online", 
        "led_connected": stick_connected,
        "encoder_connected": twist_connected if 'twist_connected' in globals() else False
    })


@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve the dashboard assets from the same Flask origin."""
    target_path = os.path.join(FRONTEND_DIR, path)
    if not os.path.exists(target_path) or os.path.isdir(target_path):
        path = 'index.html'
    return send_from_directory(FRONTEND_DIR, path)

@app.route('/api/encoder-event')
def get_encoder_event():
    try:
        # Long-polling: wait up to 30 seconds for an event
        event = encoder_event_queue.get(timeout=30)
        return jsonify({'event': event})
    except queue.Empty:
        # Timeout - no event, return none
        return jsonify({'event': 'none'})
    except Exception as e:
        return jsonify({'event': 'none', 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
