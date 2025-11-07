# Morse Code Symbol-Based Transmission

## Changes Made

### Transmitter (`final_submission.py`)

**Changed payload from:**
```json
{
  "message": "HELLO",
  "morse": ".... . .-.. .-.. ---",
  "timestamp": 1699308123.456,
  "count": 1
}
```

**To:**
```json
{
  "symbols": ".... . .-.. .-.. ---",
  "timestamp": 1699308123.456,
  "count": 1
}
```

### Key Changes:
1. ✅ Only morse symbols (dots and dashes) are transmitted
2. ✅ No decoded text sent over MQTT
3. ✅ Receiver decodes the symbols locally
4. ✅ Spaces between letters preserved in symbol string
5. ✅ Topic changed to: `IDD/lab6/morse/coolguys/symbol`

## How It Works

### **Transmitter Side:**
```
Button Presses → Morse Symbols → Track Symbols String → Publish Symbols
   ....              ....              ....                ....
   .                 . (space)         .... .              .... .
   .-..              .-.. (space)      .... . .-..         .... . .-..
   etc.
```

### **Receiver Side:**
```
Receive Symbols → Split by Spaces → Decode Each → Display Text
".... . .-.. .-.. ---"  
   ↓
["....", ".", ".-..", ".-..", "---"]
   ↓
['H', 'E', 'L', 'L', 'O']
   ↓
"HELLO"
```

## Example Session

### Transmitter Output:
```
Press .... (pause 1s)
[....] = 'H'
Word so far: 'H'
Symbols so far: '....'

Press . (pause 1s)
[.] = 'E'
Word so far: 'HE'
Symbols so far: '.... .'

(Wait 5 seconds)

============================================================
5 SECOND PAUSE DETECTED - PUBLISHING MESSAGE
============================================================
Published symbols: .... . .-.. .-.. ---
Sent symbols: '.... . .-.. .-.. ---'
Decoded as: 'HELLO'
============================================================
```

### Receiver Output:
```
============================================================
Message Received at 14:30:45
============================================================
Symbols:     .... . .-.. .-.. ---
Decoded:     HELLO
Count:       #1
============================================================
```

### Display Shows:
```
┌────────────────────────────────┐
│ MORSE RECEIVER          #1    │
│ Symbols: .... . .-.. .-.. ---  │
│                               │
│      HELLO                    │
│                               │
│ 14:30:45                      │
└────────────────────────────────┘
```

## Benefits

✅ **Efficient**: Only raw symbols transmitted (smaller payload)
✅ **Flexible**: Receiver can decode or show raw symbols
✅ **Educational**: Shows the actual morse code pattern
✅ **Distributed**: Different receivers could decode differently
✅ **Debugging**: Easy to verify transmission accuracy

## Testing

### Run Transmitter:
```bash
python final_submission.py
```

### Run Receiver:
```bash
python morse_display_receiver.py
```

### Send Test Message:
```
Tap: ... --- ...  (SOS)
Wait 5 seconds
→ Symbols transmitted: "... --- ..."
→ Receiver decodes to: "SOS"
```
