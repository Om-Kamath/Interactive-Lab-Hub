#!/usr/bin/env python3
"""
Lab 4: Gesture-Controlled Servo
Uses APDS9960 gesture sensor to control servo position via hand gestures.
- LEFT: Rotate 180 degrees counter-clockwise (to min position)
- RIGHT: Rotate 180 degrees clockwise (to max position)
- UP: Rotate 15 degrees clockwise
- DOWN: Rotate 15 degrees counter-clockwise
"""

import time
import board
from adafruit_apds9960.apds9960 import APDS9960
from adafruit_servokit import ServoKit

# Setup
print("\nGesture-Controlled Servo - Lab 4")
print("=" * 50)
print("Swipe to control servo:")
print("  LEFT  -> Rotate to 0 degrees (full counter-clockwise)")
print("  RIGHT -> Rotate to 180 degrees (full clockwise)")
print("  UP    -> Rotate 15 degrees clockwise")
print("  DOWN  -> Rotate 15 degrees counter-clockwise")
print("=" * 50)
print()

# Initialize gesture sensor
i2c = board.I2C()
apds = APDS9960(i2c)
apds.enable_proximity = True
apds.enable_gesture = True

# Uncomment and adjust rotation if sensor is mounted differently
# apds.rotation = 270  # Adjust if gestures are reversed

# Initialize servo
kit = ServoKit(channels=16)
servo = kit.servo[2]  # Using servo channel 2 - adjust if needed

# Set servo pulse width range (adjust based on your servo's datasheet)
servo.set_pulse_width_range(500, 2500)

# Servo configuration
SERVO_MIN = 0      # Minimum angle (degrees)
SERVO_MAX = 180    # Maximum angle (degrees)
STEP_SIZE = 30     # Degrees to move for LEFT/RIGHT gestures
current_angle = 90 # Start at center position

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

def main():
    """Main gesture recognition loop"""
    print("System ready! Start swiping...\n")
    
    try:
        while True:
            gesture = apds.gesture()
            
            if gesture:
                handle_gesture(gesture)
                
                # Small delay to prevent gesture spam
                time.sleep(0.3)
                
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        # Return servo to center on exit
        print("Returning servo to center position...")
        servo.angle = 90
        time.sleep(0.5)
        print("Servo centered. Goodbye!")

if __name__ == '__main__':
    main()