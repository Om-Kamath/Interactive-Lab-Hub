# Distributed Interaction

\*\***NAMES OF COLLABORATORS HERE**\*\*
<br> **Karl Muller (km2262)**
<br> **Om Kamath (ok97)**

---

## Part A: MQTT Messaging

**Testing Listener**
<img width="1226" height="94" alt="Pasted Graphic" src="https://github.com/user-attachments/assets/744c965e-ccaa-4dc1-a3df-b303d2b2ef94" />

**Testing Publisher**
<img width="1425" height="19" alt="Pasted Graphic 1" src="https://github.com/user-attachments/assets/c5eea771-2870-4fb5-b5a8-cbf98b7a42d6" />

<img width="1788" height="708" alt="Pasted Graphic 2" src="https://github.com/user-attachments/assets/bc9068a7-25b0-4844-89f4-e255c4460ddc" />


**Idea**
- Morse Code communicator with multiple pi to one server

---

## Part B: Collaborative Pixel Grid

**📸 Include: Screenshot of grid + photo of your Pi setup** <br>

<img height="400" alt="image" src="https://github.com/user-attachments/assets/c2293121-8532-407a-8040-fa152fa8a92e" />


---

### **1. Project Description** <br>
**What does it do? Why interesting? User experience?** <br>
We built a distributed system using MQTT where multiple Raspberry Pi devices with Qwiic buttons transmit Morse code (dots and dashes) to a shared MQTT broker. A central Flask server with a web dashboard listens to the topic and displays decoded letters, full messages, and transmission history for each Pi in real time.

This project is interesting because it transforms simple tactile inputs (button presses) into distributed, real time communication using networked microcontrollers. The user presses the button for short (dot) or long (dash) durations. After a pause, the system automatically decodes the Morse sequence and displays the letter. Each Pi has its own message stream, making the experience collaborative and transparent.

### **2. Architecture Diagram**
- Hardware, connections, data flow
- Label input/computation/output

<img src="https://github.com/Om-Kamath/Interactive-Lab-Hub/blob/88d92294263031d6eee4de1daec5f72a943ebb2f/Lab%206/image%20(1).png"/>

### **3. Build Documentation**

**Devices:**<br>
- 2 or 3 (as many can connect as they want) rpi5 with qwiic button  connected to GPIO header
- Laptop running Flask + MQTT Subscriber Dashboard

**MQTT Topic:**<br>
- `IDD/lab6/morse/coolguys/symbol`
- Payload: `{ "symbol": ".", "device_id": "karl" }` or `{ "symbol": "-", "device_id": "om" }`

**Code Snippets:**<br>
Important Files: (AI helped on this, espcially styling of the dashboard, thats why it looks cool !) 
- [Server](src/server/app.py) 
- [Pi Publiser](src/pi/qwiic_button_publisher.py)
- [Morse Decoder helper](src/server/morse.py)

Publisher function [src/pi/qwiic_button_publisher.py](src/pi/qwiic_button_publisher.py): <br>
```python
def publish_message(client, morse_symbols):
    """Publish morse symbols to the MQTT broker"""
    global message_count
    message_count += 1
    
    payload = json.dumps({
        'symbol': morse_symbols,
        'device_id': 'om',
        'timestamp': time.time(),
        'count': message_count
    })
    
    result = client.publish(MQTT_TOPIC, payload)
    
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"Published symbols: {morse_symbols}")
    else:
        print(f"Publish failed with code {result.rc}")
    
    return result
```
<br>Where `morse_symbols` were either a dot or dash of current symbol sent from qwiic button. Dot determine by button holding threshold [src/pi/qwiic_button_publisher.py](src/pi/qwiic_button_publisher.py): <br>
```python
...
    if press_duration < DOT_THRESHOLD:
        current_morse += '.'
        print('.', end='', flush=True)
    else:
        current_morse += '-'
        print('-', end='', flush=True)
...
```
<br> Server would listen for the topic, extract the symbol [src/server/app.py](src/server/app.py):
```python
    def ingest_symbol(self, payload: Dict[str, object]) -> None:
        symbol = payload.get("symbol")
        if symbol not in VALID_SYMBOLS:
            logger.debug("Ignoring payload without symbol: %s", payload)
            return
        ...

```
<br> Server would then try to string together symbols based on timing intervals, message would then be decoded and displayed [src/server/app.py](src/server/app.py): 
```python
    def finalize_letter(self, event_time: datetime):
        pattern = "".join(item["symbol"] for item in self.current_symbols)
        if not pattern:
            return None
        letter = decode_morse(pattern)
        entry = {
            "type": "letter",
            "letter": letter,
            "pattern": pattern,
            "timestamp": event_time.isoformat(),
        }
        self.decoded_message += letter
        ...
```
<br> Morse code decoder function [src/server/morse.py](src/server/morse.py):
```python
MORSE_CODE: Dict[str, str] = {
    ".-": "A",
    "-...": "B",
    "-.-.": "C",
    "-..": "D",
    ".": "E",
    "..-.": "F",
    "--.": "G",
    "....": "H",
    "..": "I",
    ".---": "J",
    "-.-": "K",
    ".-..": "L",
    "--": "M",
    "-.": "N",
    "---": "O",
    ".--.": "P",
    "--.-": "Q",
    ".-.": "R",
    "...": "S",
    "-": "T",
    "..-": "U",
    "...-": "V",
    ".--": "W",
    "-..-": "X",
    "-.--": "Y",
    "--..": "Z",
    "-----": "0",
    ".----": "1",
    "..---": "2",
    "...--": "3",
    "....-": "4",
    ".....": "5",
    "-....": "6",
    "--...": "7",
    "---..": "8",
    "----.": "9",
    ".-.-.-": ".",
    "--..--": ",",
    "..--..": "?",
    ".----.": "'",
    "-.-.--": "!",
    "-..-.": "/",
    "-.--.": "(",
    "-.--.-": ")",
    ".-...": "&",
    "---...": ":",
    "-.-.-.": ";",
    "-...-": "=",
    ".-.-.": "+",
    "-....-": "-",
    "..--.-": "_",
    ".-..-.": '"',
    "...-..-": "$",
    ".--.-.": "@",
}

VALID_SYMBOLS = {".", "-"}


def decode_morse(pattern: str) -> str:
    """Return the decoded character for a dot/dash pattern (or '?' if unknown)."""
    cleaned = (pattern or "").strip()
    if not cleaned:
        return ""
    return MORSE_CODE.get(cleaned, "?")
```

**Photos/Video of Setup**<br>
Each device publishing is a Pi Setup with qwiic button:<br>
<img width="1129" height="852" alt="image" src="https://github.com/user-attachments/assets/577d4bf6-16fe-44fb-8d62-87308ce58684" />

Main Server Listening for messages, with two and three publisher: <br>
<img width="1794" height="997" alt="Pasted Graphic 4" src="https://github.com/user-attachments/assets/77ee2903-19cf-4fb6-a700-a449597278ad" />
<img width="1800" height="983" alt="Pasted Graphic 5" src="https://github.com/user-attachments/assets/c60c43b5-9fb8-46b4-a764-9fc01ced4a07" />

Publisher console output: <br>
<img width="897" height="790" alt="Pasted Graphic 6" src="https://github.com/user-attachments/assets/266aff74-d938-4a32-8884-1b47d3f7091e" />

Server listener console output: <br>
<img width="1225" height="971" alt="Pasted Graphic 7" src="https://github.com/user-attachments/assets/72f03ea9-70ab-4c77-ba5b-967a898332e1" />


Three Pis connected to server: <br>
<img width="1209" height="792" alt="image" src="https://github.com/user-attachments/assets/1d1c676b-1178-49d1-a8b5-60d5c2492d51" />

Video interaction: <br>
[Testing a message sent to server via morse code](https://drive.google.com/file/d/1acjt-gmCmJrJb8e_gwvGKI7I_mBhHAgy/view?usp=sharing)

<br><br>
### **4. User Testing**
Tested with two other users, able to use two pis at the same time. <br>

Photo/videos: <br>
[User Interaction](https://drive.google.com/file/d/1COBvnrb5_AXRhYh_Up_i9It5O5BaiEGn/view?usp=sharing)<br><br>
<img width="898" height="789" alt="Morse MQTT Grid" src="https://github.com/user-attachments/assets/8f201618-b5a9-4cab-b899-4b9b650428a0" />
<img width="716" height="705" alt="image" src="https://github.com/user-attachments/assets/93386e66-4e26-498e-ab79-cd40bf70f037" />

What did they think before trying? <br>
- “No idea how it would work”
- “Assumed it might lag or not update right away”

What surprised them? <br>
- “It worked better than expected”
- “I liked seeing my letter appear pretty quickly”
- “The dashboard made it feel collaborative”

What would they change? <br>
- “The button lag made it hard to time correctly sometimes”
	- Here they were referring to when to know when clicking the button for a dot vs a dash would pass the timing threshold for becoming a dash over a dot 	
- “Maybe add sound feedback when press is registered”

### **5. Reflection**
What worked well? <br>
- The majority of this lab went pretty well. The qwiic button detection was reliable, the MQTT pub/sub worked pretty smoothly, the dashboard listener server gave clear real time feedback, and labeled devices and symbol/letter history allow us to construct a message out of user morse code requests.

Challenges with distributed interaction? <br>
- A couple challenges we hit were around latency. We originally used the APDS 9960 as a morse reader by when we tapped it (blocking light), it would make a dot or dash publish event. The timing and lighting detection was unreliable in this scenario which made us switch to using the qwiic button, which was much better for making a clear dot/dash. There was a little latency is the MQTT server interaction that made UI updates a little slower than expected. It was also interesting dealing with multi device input and deduplication. By having a count and device label with each device, it made it clear where each message was coming from. 

How did sensor events work? <br>
- Using the qwiic button, sensor events were fairly straighforward. We had dot and dash events based on the duration of the button press, folowed by letter and word separation based on another timing threshold. If you pressed (dot/dash) with a short pause (~2 seconds) and then entered more symbols, that would signify to the server you are onto the next letter. If you had a pause longer than the letter threshold, the server would take it as a word break. Overall the sensor events worked well, just took a lot of finetuning in regards to timing and when to send over events to the topic. 

What would you improve? <br>
- Probably would take the user suggestion of add auditory feedback on button presses, tweaking the timing thresholds of the button presses more to make it more natural instead of a user guessing when to next press, and maybe making dot and dash two seperate buttons to make this even more clear.

---
