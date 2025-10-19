#!/usr/bin/env python3
"""
Lab 4: Gesture and Joystick Controlled Servo
Uses APDS9960 gesture sensor AND Qwiic Joystick to control servo position.

GESTURE CONTROL:
- LEFT: Rotate 180 degrees counter-clockwise (to min position)
- RIGHT: Rotate 180 degrees clockwise (to max position)
- UP: Rotate 15 degrees clockwise
- DOWN: Rotate 15 degrees counter-clockwise

JOYSTICK CONTROL:
- Move joystick LEFT/RIGHT: Continuously control servo position (0-180 degrees)
"""

import time
import board
import sys
import traceback
from adafruit_apds9960.apds9960 import APDS9960
from adafruit_servokit import ServoKit
import qwiic_joystick

# Setup
print("\nGesture and Joystick Controlled Servo - Lab 4")
print("=" * 60)
print("GESTURE CONTROL:")
print("  LEFT  -> Rotate to 0 degrees (full counter-clockwise)")
print("  RIGHT -> Rotate to 180 degrees (full clockwise)")
print("  UP    -> Rotate 15 degrees clockwise")
print("  DOWN  -> Rotate 15 degrees counter-clockwise")
print()
print("JOYSTICK CONTROL:")
print("  Move LEFT/RIGHT -> Continuously control position (0-180 degrees)")
print("=" * 60)
print()

# Initialize gesture sensor
i2c = board.I2C()
apds = APDS9960(i2c)
apds.enable_proximity = True
apds.enable_gesture = True

# Uncomment and adjust rotation if sensor is mounted differently
# apds.rotation = 270  # Adjust if gestures are reversed

# Initialize joystick
joystick = qwiic_joystick.QwiicJoystick()

if not joystick.connected:
    print("WARNING: Joystick not connected! Only gesture control will work.")
    joystick_enabled = False
else:
    joystick.begin()
    print("Joystick connected. Firmware Version: %s" % joystick.version)
    joystick_enabled = True

# Initialize servo
kit = ServoKit(channels=16)
servo = kit.servo[2]  # Using servo channel 2 - adjust if needed

# Set servo pulse width range (adjust based on your servo's datasheet)
servo.set_pulse_width_range(500, 2500)

# Servo configuration
SERVO_MIN = 0      # Minimum angle (degrees)
SERVO_MAX = 180    # Maximum angle (degrees)
STEP_SIZE = 30     # Degrees to move for gesture UP/DOWN
current_angle = 90 # Start at center position

# Joystick configuration
JOYSTICK_CENTER = 512   # Joystick center position (0-1023 range)
JOYSTICK_DEADZONE = 50  # Dead zone around center to prevent drift (reduced for better response)
JOYSTICK_MIN = 0        # Joystick minimum value
JOYSTICK_MAX = 1023     # Joystick maximum value

# Add debug flag to see joystick values
DEBUG_JOYSTICK = True   # Set to False to hide debug output

# Initialize servo to center
servo.angle = current_angle
print("Servo initialized to %d degrees" % current_angle)
time.sleep(0.5)

def move_servo_to(target_angle, description):
    """
    Move servo to target angle with bounds checking and feedback.
    
    Args:
        target_angle: Desired servo angle (0-180)
        description: Human-readable description of movement
    """
    global current_angle
    
    # Clamp angle to valid range
    target_angle = max(SERVO_MIN, min(SERVO_MAX, target_angle))
    
    if target_angle == current_angle:
        print("Already at %d degrees (limit reached)" % current_angle)
        return
    
    # Determine direction
    if target_angle > current_angle:
        direction = "CW"
    else:
        direction = "CCW"
    
    # Move servo
    servo.angle = target_angle
    
    # Visual feedback
    bar_position = int((target_angle / SERVO_MAX) * 20)
    position_bar = "-" * bar_position + "O" + "-" * (20 - bar_position)
    
    print("%s (%s) | %3d -> %3d degrees | [%s]" % (description, direction, current_angle, target_angle, position_bar))
    
    current_angle = target_angle

def handle_gesture(gesture_code):
    """
    Process gesture and move servo accordingly.
    
    Args:
        gesture_code: Integer code from APDS9960 (0x01-0x04)
    """
    if gesture_code == 0x01:  # UP
        new_angle = current_angle + STEP_SIZE
        move_servo_to(new_angle, "UP swipe")
        
    elif gesture_code == 0x02:  # DOWN
        new_angle = current_angle - STEP_SIZE
        move_servo_to(new_angle, "DOWN swipe")
        
    elif gesture_code == 0x03:  # LEFT
        move_servo_to(SERVO_MIN, "LEFT swipe")
        
    elif gesture_code == 0x04:  # RIGHT
        move_servo_to(SERVO_MAX, "RIGHT swipe")

def map_joystick_to_angle(joystick_x):
    """
    Map joystick horizontal position to servo angle.
    
    Args:
        joystick_x: Horizontal joystick value (0-1023)
    
    Returns:
        Servo angle (0-180) or None if in deadzone
    """
    # Debug output
    if DEBUG_JOYSTICK:
        distance_from_center = abs(joystick_x - JOYSTICK_CENTER)
        if distance_from_center > 5:  # Only print if joystick moved
            print("Joystick X: %d (distance from center: %d)" % (joystick_x, distance_from_center))
    
    # Check if in deadzone (near center)
    if abs(joystick_x - JOYSTICK_CENTER) < JOYSTICK_DEADZONE:
        return None
    
    # Map joystick range (0-1023) to servo range (0-180)
    # Left (0) = 0 degrees, Right (1023) = 180 degrees
    angle = int((joystick_x / JOYSTICK_MAX) * SERVO_MAX)
    
    # Clamp to valid range
    angle = max(SERVO_MIN, min(SERVO_MAX, angle))
    
    if DEBUG_JOYSTICK:
        print("  -> Mapped to angle: %d" % angle)
    
    return angle

def handle_joystick():
    """
    Read joystick and control servo position continuously.
    
    Returns:
        True if joystick controlled servo, False if no movement
    """
    global current_angle
    
    if not joystick_enabled:
        return False
    
    try:
        # SOLUTION 4: Add delays and better error handling
        time.sleep(0.01)  # Small delay before I2C read
        
        # Read horizontal joystick position
        joystick_x = joystick.horizontal
        
        # Debug output to confirm reading
        if DEBUG_JOYSTICK:
            print("Successfully read joystick: %d" % joystick_x)
        
        time.sleep(0.01)  # Small delay after I2C read
        
        # Map to servo angle
        target_angle = map_joystick_to_angle(joystick_x)
        
        if target_angle is not None:
            # Always update servo position based on joystick
            servo.angle = target_angle
            
            # Update current angle
            if abs(target_angle - current_angle) > 2:  # Only report significant changes
                current_angle = target_angle
                return True
        
        return False
        
    except Exception as e:
        # SOLUTION 4: Detailed error reporting
        print("ERROR reading joystick: %s" % str(e))
        traceback.print_exc()
        return False

def main():
    """Main control loop - handles both gesture and joystick input"""
    print("\nSystem ready!")
    print("Use gestures for discrete movements or joystick for continuous control")
    if joystick_enabled:
        print("Joystick enabled - Move it left/right to test!")
    print()
    
    last_display_time = 0
    display_interval = 0.2  # Show status more frequently
    
    # SOLUTION 3: Don't check gesture every loop - reduce I2C bus contention
    gesture_check_interval = 0.1  # Check gestures every 100ms instead of every loop
    last_gesture_check = 0
    
    try:
        while True:
            current_time = time.time()
            
            # SOLUTION 3: Check for gestures less frequently to reduce I2C traffic
            if current_time - last_gesture_check > gesture_check_interval:
                try:
                    gesture = apds.gesture()
                    
                    if gesture:
                        handle_gesture(gesture)
                        # Small delay to prevent gesture spam
                        time.sleep(0.3)
                    
                    last_gesture_check = current_time
                    
                except Exception as e:
                    print("ERROR reading gesture sensor: %s" % str(e))
            
            # Check joystick (continuous control) - runs every loop
            if joystick_enabled:
                joystick_moved = handle_joystick()
                
                # Display current position periodically
                if joystick_moved and not DEBUG_JOYSTICK:
                    if current_time - last_display_time > display_interval:
                        bar_position = int((current_angle / SERVO_MAX) * 20)
                        position_bar = "-" * bar_position + "O" + "-" * (20 - bar_position)
                        print("Joystick | Position: %3d degrees | [%s]" % (current_angle, position_bar))
                        last_display_time = current_time
            
            # Smaller delay for more responsive joystick
            time.sleep(0.02)
                
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        # Return servo to center on exit
        print("Returning servo to center position...")
        servo.angle = 90
        time.sleep(0.5)
        print("Servo centered. Goodbye!")

if __name__ == '__main__':
    main()