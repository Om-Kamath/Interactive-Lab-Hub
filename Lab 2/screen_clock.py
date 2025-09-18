import time
import subprocess
import digitalio
import board
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.st7789 as st7789
import adafruit_mpr121

# Configuration for CS and DC pins (these are FeatherWing defaults on M0/M4):
cs_pin = digitalio.DigitalInOut(board.D5) 
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None

# Config for display baudrate (default max is 24mhz):
BAUDRATE = 64000000

# Setup SPI bus using hardware SPI:
spi = board.SPI()

# Create the ST7789 display:
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

# Setup capacitive touch sensor
i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

# Create blank image for drawing.
height = disp.width  # we swap height/width to rotate it to landscape!
width = disp.height
image = Image.new("RGB", (width, height))
rotation = 90

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Turn on the backlight
backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = True

# Load fonts
try:
    # Large font for clock
    clock_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    # Medium font for timer
    timer_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 41)
    # Small font for labels
    label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
except:
    # Fallback to default font if TTF not available
    clock_font = ImageFont.load_default()
    timer_font = ImageFont.load_default()
    label_font = ImageFont.load_default()

# App state
class AppState:
    def __init__(self):
        self.mode = "clock"  # "clock" or "timer"
        self.timer_duration = 0
        self.timer_start_time = 0
        self.timer_remaining = 0
        self.last_touch_state = [False] * 12
        
    def start_timer(self, minutes):
        self.mode = "timer"
        self.timer_duration = minutes * 60  # Convert to seconds
        self.timer_start_time = time.time()
        self.timer_remaining = self.timer_duration
        
    def update_timer(self):
        if self.mode == "timer":
            elapsed = time.time() - self.timer_start_time
            self.timer_remaining = max(0, self.timer_duration - elapsed)
            if self.timer_remaining <= 0:
                self.mode = "clock"  # Timer finished, return to clock
                
    def return_to_clock(self):
        self.mode = "clock"

app_state = AppState()

def check_touch_inputs():
    """Check for touch input and handle mode changes"""
    for i in range(12):
        current_touch = mpr121[i].value
        # Detect rising edge (touch started)
        if current_touch and not app_state.last_touch_state[i]:
            if i == 0:
                # Touch 0 returns to clock
                app_state.return_to_clock()
                print("Returning to clock mode")

            elif i == 11:
                app_state.start_timer(25)
                print("Pomdoro Mode")
            else:
                # Touch 1-11 starts timer for that many minutes
                app_state.start_timer(i)
                print(f"Starting {i} minute timer")
        
        app_state.last_touch_state[i] = current_touch

def draw_clock():
    """Draw the minimalist clock display"""
    # Clear screen with black background
    draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 0))
    
    # Get current time
    current_time = time.strftime("%H:%M")
    current_date = time.strftime("%m/%d")
    
    # Get text dimensions for centering
    time_bbox = draw.textbbox((0, 0), current_time, font=clock_font)
    date_bbox = draw.textbbox((0, 0), current_date, font=label_font)
    
    time_width = time_bbox[2] - time_bbox[0]
    time_height = time_bbox[3] - time_bbox[1]
    date_width = date_bbox[2] - date_bbox[0]
    date_height = date_bbox[3] - date_bbox[1]
    
    # Center the time
    time_x = (width - time_width) // 2
    time_y = (height - time_height) // 2 - 10
    
    # Center the date below time
    date_x = (width - date_width) // 2
    date_y = time_y + time_height + 10
    p
    # Draw time in white
    draw.text((time_x, time_y), current_time, font=clock_font, fill=(255, 255, 255))
    
    # Draw date in gray
    draw.text((date_x, date_y), current_date, font=label_font, fill=(128, 128, 128))
    
    # Draw small instruction at bottom
    instruction = "Touch 11 for Pomodoro."
    inst_bbox = draw.textbbox((0, 0), instruction, font=label_font)
    inst_width = inst_bbox[2] - inst_bbox[0]
    inst_x = (width - inst_width) // 2
    draw.text((inst_x, height - 20), instruction, font=label_font, fill=(64, 64, 64))

def draw_timer():
    """Draw the timer display"""
    # Clear screen with dark blue background
    draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 40))
    
    # Update timer state
    app_state.update_timer()
    
    # Format remaining time
    minutes = int(app_state.timer_remaining // 60)
    seconds = int(app_state.timer_remaining % 60)
    time_text = f"{minutes:02d}:{seconds:02d}"
    
    # Get text dimensions
    time_bbox = draw.textbbox((0, 0), time_text, font=timer_font)
    time_width = time_bbox[2] - time_bbox[0]
    time_height = time_bbox[3] - time_bbox[1]
    
    # Center the timer
    time_x = (width - time_width) // 2
    time_y = (height - time_height) // 2 - 15
    
    # Choose color based on remaining time
    if app_state.timer_remaining > 60:
        color = (0, 255, 0)  # Green
    elif app_state.timer_remaining > 10:
        color = (255, 255, 0)  # Yellow
    else:
        color = (255, 0, 0)  # Red
    
    # Draw timer text
    draw.text((time_x, time_y), time_text, font=timer_font, fill=color)
    
    # Draw progress bar
    bar_width = width - 20
    bar_height = 8
    bar_x = 10
    bar_y = time_y + time_height + 15
    
    # Background bar
    draw.rectangle((bar_x, bar_y, bar_x + bar_width, bar_y + bar_height), 
                  outline=(100, 100, 100), fill=(50, 50, 50))
    
    # Progress bar
    if app_state.timer_duration > 0:
        progress = app_state.timer_remaining / app_state.timer_duration
        fill_width = int(bar_width * progress)
        draw.rectangle((bar_x, bar_y, bar_x + fill_width, bar_y + bar_height), 
                      fill=color)
    
    # Instructions
    instruction = "Touch 0 to return to clock"
    inst_bbox = draw.textbbox((0, 0), instruction, font=label_font)
    inst_width = inst_bbox[2] - inst_bbox[0]
    inst_x = (width - inst_width) // 2
    draw.text((inst_x, height - 20), instruction, font=label_font, fill=(150, 150, 150))
    
    # Timer finished message
    if app_state.timer_remaining <= 0:
        finished_text = "TIME'S UP!"
        finished_bbox = draw.textbbox((0, 0), finished_text, font=timer_font)
        finished_width = finished_bbox[2] - finished_bbox[0]
        finished_x = (width - finished_width) // 2
        draw.text((finished_x, bar_y + 20), finished_text, font=timer_font, fill=(255, 255, 255))

# Main loop
while True:
    try:
        # Check for touch inputs
        check_touch_inputs()
        
        # Draw appropriate screen based on mode
        if app_state.mode == "clock":
            draw_clock()
        else:
            draw_timer()
        
        # Display the image
        disp.image(image, rotation)
        
        # Small delay
        time.sleep(0.1)
        
    except KeyboardInterrupt:
        print("\nExiting...")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)