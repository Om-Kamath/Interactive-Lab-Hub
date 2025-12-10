# Final Project - RailReady

Group: Karl Muller (km2262), Om Kamath (ok97)


### Project plan

> A subway tracker that syncs with your class schedule to suggest the best time to leave and the train to choose.

### Additional Components:
* A dot matrix / LCD Display

---

### System Architecture Flow

1.  **Button/Hotkey**
    * *Context:* or scheduled trigger
    * *Flows to:* Planner Fetch
2.  **Planner Fetch**
    * *Context:* ICS/Google; buffer=60m
    * *Input:* Calendar Data
    * *Flows to:* Transit Compute
3.  **Transit Compute**
    * *Context:* GTFS + GTFS-RT
    * *Input:* Transit Feeds
    * *Flows to:* Leave-Time
4.  **Leave-Time**
    * *Context:* reliability-aware
    * *Flows to:* TTS Output
5.  **TTS Output**
    * *Context:* Speaker: 'Leave in 8 min'

---

### Project Milestones

| Milestone | Date | Notes |
| :--- | :--- | :--- |
| **Fetching MTA data** | 11/17 | Selecting the best API for bringing data. |
| **Fetching Calender Data** | 11/21 | Converting `.ics` files to something that is readable. Potential use of LLMs here. |
| **Connect display and wiring everything up** | 11/23 | Creating an enclosure for this. Performing user testing. First prototype. |
| **Functional check-off** | December 1 | Changes based on user feedback. |

### Functioning project

### Documentation of design process

![Design Prototype 1](./design-railready.png)

4. Archive of all code, design patterns, etc. used in the final design. (As with labs, the standard should be that the documentation would allow you to recreate your project if you woke up with amnesia.)
5. Video of someone using your project
6. Reflections on process (What have you learned or wish you knew at the start?)

7. Group work distribution questionnaire


