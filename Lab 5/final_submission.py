#!/usr/bin/env python3
"""
Moondream Vision with Display Output
Captures image from webcam, asks Moondream for food suggestion,
and displays the response on Adafruit RGB display
"""

import cv2
import requests
import base64
import time
import digitalio
import board
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.st7789 as st7789
import textwrap
import urllib.parse
import subprocess

# Setup button on GPIO 23
button = digitalio.DigitalInOut(board.D23)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# Setup Display
cs_pin = digitalio.DigitalInOut(board.D5)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None
BAUDRATE = 64000000

spi = board.SPI()
disp = st7789.ST7789(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
    width=135,
    height=240,
    x_offset=53,
    y_offset=40,
)

# Display configuration
height = disp.width  # Swap for landscape
width = disp.height
rotation = 270  # Upside down (was 90, now 270 for 180° flip)

# Turn on backlight
backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = True

# Load fonts - Fitbit-style: bigger, bolder, more readable
try:
    # Larger fonts for Fitbit appeal
    main_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    bold_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    large_header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
except:
    main_font = ImageFont.load_default()
    bold_font = ImageFont.load_default()
    small_font = ImageFont.load_default()
    header_font = ImageFont.load_default()
    large_header_font = ImageFont.load_default()

# Fitbit-inspired color palette
BG_COLOR = (0, 0, 0)              # Pure black background
TEXT_COLOR = (255, 255, 255)      # Bright white text
ACCENT_COLOR = (0, 200, 255)      # Fitbit cyan/aqua accent
BOLD_COLOR = (255, 255, 255)      # White for bold emphasis
HEADER_COLOR = (0, 200, 255)      # Cyan for headers (Fitbit style)
SUBTITLE_COLOR = (180, 180, 180)  # Light gray for subtitles

import re

def say(text, language='en'):
    """Convert text to speech using Google TTS."""
    # Clean text: remove any non-ASCII characters that might cause encoding issues
    clean_text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Replace common issues
    clean_text = clean_text.replace('--', '-')  # Remove double dashes
    clean_text = ' '.join(clean_text.split())  # Normalize whitespace
    
    if not clean_text.strip():
        print("[WARNING] Text became empty after cleaning, skipping TTS")
        return
    
    encoded_text = urllib.parse.quote_plus(clean_text)
    tts_url = f"http://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q={encoded_text}&tl={language}"
    
    try:
        subprocess.run([
            '/usr/bin/mplayer',
            '-ao', 'alsa',
            '-really-quiet',
            '-noconsolecontrols',
            tts_url
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error playing audio: {e}")
    except FileNotFoundError:
        print("Error: mplayer not found. Install with: sudo apt-get install mplayer")

def parse_markdown_line(line):
    """
    Parse a single line of markdown and return formatted segments
    Returns: list of (text, font, color) tuples
    """
    segments = []
    
    # Check for headers (# Header)
    if line.startswith('# '):
        return [('header', line[2:].strip())]
    elif line.startswith('## '):
        return [('header', line[3:].strip())]
    
    # Check for bullet points (- item or * item)
    if line.strip().startswith(('- ', '* ')):
        line = '• ' + line.strip()[2:]
    
    # Check for numbered lists (1. item)
    if re.match(r'^\d+\.\s', line.strip()):
        line = line.strip()
    
    # Parse inline markdown (bold, italic)
    # Bold: **text** or __text__
    # Italic: *text* or _text_
    
    pattern = r'(\*\*.*?\*\*|__.*?__|(?<!\*)\*(?!\*).*?(?<!\*)\*(?!\*)|(?<!_)_(?!_).*?(?<!_)_(?!_))'
    parts = re.split(pattern, line)
    
    for part in parts:
        if not part:
            continue
        
        if part.startswith('**') and part.endswith('**'):
            # Bold text
            segments.append(('bold', part[2:-2]))
        elif part.startswith('__') and part.endswith('__'):
            # Bold text
            segments.append(('bold', part[2:-2]))
        elif part.startswith('*') and part.endswith('*') and not part.startswith('**'):
            # Italic text (render as normal since we don't have italic font)
            segments.append(('normal', part[1:-1]))
        elif part.startswith('_') and part.endswith('_') and not part.startswith('__'):
            # Italic text (render as normal)
            segments.append(('normal', part[1:-1]))
        else:
            # Normal text
            segments.append(('normal', part))
    
    return segments if segments else [('normal', line)]

def draw_formatted_text(draw, text, x, y, max_width):
    """
    Draw text with inline markdown formatting - Fitbit style
    Returns: height of drawn text
    """
    segments = parse_markdown_line(text)
    current_x = x
    line_height = 22  # Bigger line height for readability
    
    for seg_type, seg_text in segments:
        if seg_type == 'header':
            # Draw header in Fitbit cyan with larger font
            draw.text((x, y), seg_text, font=large_header_font, fill=HEADER_COLOR)
            return line_height + 8  # Extra spacing after header
        elif seg_type == 'bold':
            # Draw bold text
            draw.text((current_x, y), seg_text, font=bold_font, fill=BOLD_COLOR)
            bbox = draw.textbbox((current_x, y), seg_text, font=bold_font)
            current_x = bbox[2] + 2
        else:
            # Draw normal text
            draw.text((current_x, y), seg_text, font=main_font, fill=TEXT_COLOR)
            bbox = draw.textbbox((current_x, y), seg_text, font=main_font)
            current_x = bbox[2] + 2
    
    return line_height

def display_message(text, title=None):
    """
    Fitbit-style display with markdown rendering support
    Supports: **bold**, # headers, bullet points (- or *), numbered lists
    Optional small title at top in cyan
    """
    image = Image.new("RGB", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(image)
    
    y_offset = 12
    
    # Optional title (Fitbit cyan accent)
    if title:
        draw.text((12, y_offset), title.upper(), font=small_font, fill=ACCENT_COLOR)
        y_offset += 28
    
    # Process text line by line for markdown
    lines = text.split('\n')
    
    # Word wrap only non-markdown lines (adjusted for bigger font and smaller display)
    wrapped_lines = []
    max_display_lines = 6  # Limit total lines to prevent overflow
    
    for line in lines:
        line = line.strip()
        if not line:
            wrapped_lines.append('')
            continue
        
        # Don't wrap headers, bullets, or numbered lists
        if (line.startswith('#') or 
            line.startswith(('- ', '* ')) or 
            re.match(r'^\d+\.\s', line)):
            wrapped_lines.append(line)
        else:
            # Wrap long lines - reduced width for larger 18pt font
            wrapper = textwrap.TextWrapper(width=22, break_long_words=True, max_lines=3)
            wrapped = wrapper.wrap(line)
            wrapped_lines.extend(wrapped if wrapped else [''])
    
    # Draw each line with markdown formatting
    lines_drawn = 0
    for line in wrapped_lines:
        # Stop if we're running out of space or hit line limit
        if y_offset > height - 35 or lines_drawn >= max_display_lines:
            # Add ellipsis if text is cut off (in cyan accent)
            if lines_drawn > 0:
                draw.text((12, y_offset - 22), "...", font=small_font, fill=ACCENT_COLOR)
            break
        
        # Draw the formatted line
        line_height = draw_formatted_text(draw, line, 12, y_offset, width - 24)
        y_offset += line_height
        lines_drawn += 1
    
    # Display
    disp.image(image, rotation)

def display_status(message):
    """
    Fitbit-style centered status message with cyan accent
    """
    image = Image.new("RGB", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(image)
    
    # Draw a small cyan dot/indicator (Fitbit style)
    dot_x = width // 2
    dot_y = height // 2 - 25
    draw.ellipse([dot_x-3, dot_y-3, dot_x+3, dot_y+3], fill=ACCENT_COLOR)
    
    # Center the message below dot
    bbox = draw.textbbox((0, 0), message, font=bold_font)
    text_width = bbox[2] - bbox[0]
    
    x = (width - text_width) // 2
    y = height // 2 - 5
    
    draw.text((x, y), message, font=bold_font, fill=TEXT_COLOR)
    disp.image(image, rotation)

def capture_image(filename="captured_image.jpg"):
    """Capture image from webcam using OpenCV"""
    print("Opening camera...")
    
    # Open webcam (same as infer.py and hand_pose.py)
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return None
    
    print("Camera warming up...")
    # Let camera warm up - need more time for proper exposure
    time.sleep(2)
    for i in range(30):
        cap.read()
    
    # Capture frame
    print("Smile! Capturing in 3...")
    time.sleep(1)
    print("2...")
    time.sleep(1)
    print("1...")
    time.sleep(1)
    print("*CLICK*")
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("Error: Could not capture image")
        return None
    
    # Save image
    cv2.imwrite(filename, frame)
    print(f"Image saved as: {filename}")
    return filename

def display_food_suggestion(json_response):
    """
    Display food suggestion from JSON format with voice output
    Expected format: {
        "food": "Pizza", 
        "description": "Quick and delicious...",
        "dialog": "Hey there! You should totally try pizza because..."
    }
    """
    import json as json_module
    
    try:
        # Parse JSON response
        data = json_module.loads(json_response)
        food_item = data.get("food", "Unknown")
        description = data.get("description", "No description available")
        dialog = data.get("dialog", description)  # Fallback to description if no dialog
        
        # Format for display with markdown
        formatted_text = f"# {food_item}\n\n{description}"
        
        # Display on screen
        display_message(formatted_text)
        
        # Small pause before speaking
        time.sleep(0.5)
        
        # Show speaking indicator
        display_status("🔊 Speaking...")
        
        # Speak the dialog
        print(f"\n[VOICE] Speaking: {dialog}")
        say(dialog)
        
        # Return to food display after speaking
        time.sleep(0.3)
        display_message(formatted_text)
        
    except json_module.JSONDecodeError as e:
        print(f"[WARNING] Could not parse JSON: {e}")
        print(f"Raw response: {json_response}")
        # Fallback: just display the raw text
        display_message(json_response, title="food")

def ask_moondream(image_path, prompt=None):
    
    # Default prompt requests JSON format with dialog
    if prompt is None:
        prompt = '''Based on the image, suggest a food I should eat purely based on the weather and time, not the location.
    Respond ONLY with valid JSON in this exact format:
    {
        "food": "Food Name",
        "description": "ONE short sentence (max 15 words) with **bold** emphasis on key word",
        "dialog": "Friendly conversational explanation (2-3 sentences) of why this food is great. Make it warm, encouraging, and personable - like a friend giving advice."
    }

    IMPORTANT RULES:
    - Use ONLY plain ASCII characters (no em-dashes, smart quotes, or fancy punctuation)
    - Use regular hyphens (-) instead of em-dashes (—)
    - Use regular quotes (") instead of smart quotes ("")
    - Use regular apostrophes (') instead of curly apostrophes (')
    - Keep description VERY SHORT - it must fit on a small screen!
    - Keep it simple and clean!

    Example:
    {
        "food": "Pasta Carbonara",
        "description": "A **creamy** Italian dish perfect for comfort.",
        "dialog": "Hey! I think you should try pasta carbonara. It's super comforting and comes together really quickly. Plus, who doesn't love that creamy, savory goodness?"
    }

    Keep the dialog natural and conversational - imagine you're talking to a friend!'''
    
    # Encode image to base64
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    print(f"\nAsking Moondream: {prompt[:50]}...")
    print("\nMoondream: ", end="", flush=True)
    
    # Show "Processing..." on display
    display_status("Processing...")
    
    try:
        # Query Moondream with streaming
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3-vl:235b-cloud",
                "prompt": prompt,
                "images": [image_data],
                "stream": True
            },
            timeout=300,  # Increased timeout to 5 minutes
            stream=True
        )
        
        if response.status_code == 200:
            full_response = ""
            for line in response.iter_lines():
                if line:
                    import json
                    chunk = json.loads(line)
                    token = chunk.get('response', '')
                    print(token, end="", flush=True)
                    full_response += token
            
            print("\n")  # New line after response
            
            # Display the response on screen
            # Check if this is a food suggestion (default prompt)
            if prompt is None or "suggest a food" in prompt.lower():
                # Parse and display as structured food suggestion
                display_food_suggestion(full_response)
            else:
                # Display as plain text for follow-up questions
                display_message(full_response)
            
            return full_response
        else:
            error_msg = f"Error: {response.status_code}"
            print(f"\n{error_msg}")
            display_status(error_msg)
            return None
    except requests.exceptions.Timeout:
        timeout_msg = "Timeout - Model is taking too long"
        print(f"\n[TIMEOUT] Moondream is taking too long. The model might be processing a large image.")
        print("Tip: Try using a smaller image or wait for the model to finish loading.")
        display_status(timeout_msg)
        return None
    except Exception as e:
        error_msg = f"Error: {str(e)[:30]}"
        print(f"\n[ERROR] {e}")
        display_status(error_msg)
        return None

def main():
    print("Moondream Simple Vision Demo")
    print("=" * 50)
    print("Press GPIO 23 button to refresh food suggestion!")
    print("Type 'quit' to exit, or ask questions about the image.")
    
    # Show minimal welcome message on display
    display_status("Ready")
    time.sleep(1)
    
    # Capture initial image
    image_path = capture_image()
    
    if not image_path:
        print("Failed to capture image. Exiting.")
        display_status("Error")
        return
    
    # Get initial food suggestion
    current_response = ask_moondream(image_path)
    
    # Button state tracking
    last_button_state = button.value
    last_button_time = time.time()
    button_debounce = 0.5  # 500ms debounce
    
    try:
        # Main loop - check button and allow questions
        print("\n" + "="*50)
        print("Press button to refresh suggestion")
        print("Ask questions about the image (or 'quit' to exit):")
        
        import threading
        import select
        import sys
        
        def check_button():
            """Check button state in loop"""
            nonlocal last_button_state, last_button_time, image_path, current_response
            
            while True:
                current_button_state = button.value
                current_time = time.time()
                
                # Button pressed (False because pull-up)
                if not current_button_state and last_button_state:
                    if current_time - last_button_time > button_debounce:
                        print("\n[BUTTON] Refreshing food suggestion...")
                        display_status("Refreshing...")
                        
                        # Capture new image
                        new_image = capture_image()
                        if new_image:
                            image_path = new_image
                            current_response = ask_moondream(image_path)
                        
                        last_button_time = current_time
                        print("\nYou: ", end="", flush=True)
                
                last_button_state = current_button_state
                time.sleep(0.1)  # Check every 100ms
        
        # Start button checking in background thread
        button_thread = threading.Thread(target=check_button, daemon=True)
        button_thread.start()
        
        # Interactive question loop
        while True:
            try:
                question = input("\nYou: ").strip()
                
                if question.lower() in ['quit', 'exit', 'q']:
                    display_status("—")  # Minimal goodbye
                    time.sleep(0.5)
                    break
                    
                if question:
                    result = ask_moondream(image_path, question)
                    if result is None:
                        print("Error getting response. Try again or type 'quit' to exit.")
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\nExiting...")
                break
    
    finally:
        print("\nDone!")
        # No cleanup needed for digitalio

if __name__ == "__main__":
    main()
