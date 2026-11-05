# Route 4 — Testing Plan and Evidence

## Purpose and result labels
Use this document to test each module and the complete system. Mark each test:
- `PASS`: expected behavior observed.
- `FAIL`: expected behavior not observed.
- `NOT TESTED`: test not yet performed.

For every test, record date, responsible member, setup, result and evidence.

## Member 1 — ESP32 firmware

### F1: Compilation and upload
Expected: firmware compiles and uploads to the team's actual ESP32 board.
Evidence: build/upload result and board model.

### F2: Router discovery
Expected: ESP32 detects the selected router's 2.4 GHz broadcast.
Evidence: serial output showing SSID/BSSID and channel.

### F3: RSSI readings
Expected: numeric RSSI values in dBm are produced repeatedly.
Evidence: at least 10 valid records.

### F4: Serial format
Expected: output follows the agreed format:
```text
DATA,<esp32_millis>,"<ssid>","<bssid>",<channel>,<rssi>
```
Evidence: sample output accepted by Member 2's parser.

## Member 2 — Data acquisition

### D1: Valid record parsing
Input:
```text
DATA,12345,"LabRouter","AA:BB:CC:DD:EE:FF",6,-57
```
Expected fields: uptime 12345, SSID LabRouter, BSSID AA:BB:CC:DD:EE:FF, channel 6, RSSI -57 dBm.

### D2: Invalid-line handling
Input: blank line, startup message and malformed record.
Expected: safely ignored or reported; application does not crash.

### D3: CSV logging
Expected: CSV created with a header, one row per valid reading, correct timestamp and fields, and file opens in Excel.

### D4: Serial connection
Expected: reads from selected COM port at agreed baud rate and gives a useful error if port is unavailable or device disconnects.

## Member 3 — Visualization and analysis

### V1: Graph update
Expected: graph updates when new RSSI readings arrive.

### V2: Labels and units
Expected: RSSI is displayed in dBm with understandable axes/title.

### V3: Baseline
Expected: baseline is calculated from the agreed empty-room period; method and sample count are recorded.

### V4: Change indicator
Expected: agreed states such as `CALIBRATING`, `STABLE` and `POSSIBLE_CHANGE` are shown. Threshold and method are documented. Indicator is not presented as proof of human presence.

## Member 4 — Integration

### I1: Router to ESP32
Expected: ESP32 detects the target router and reads RSSI.

### I2: ESP32 to laptop
Expected: valid serial records reach the laptop over USB.

### I3: Laptop modules
Expected: parser receives records, logger saves them and visualization displays them.

### I4: Full pipeline
Expected:
```text
Router -> Wi-Fi signal -> ESP32 -> USB serial -> Python -> CSV + live graph
```

### I5: Stability
Expected: system runs for an agreed test period without crashing; team checks for missing, malformed or repeated records.

## Room experiment plan
Use the same router and ESP32 positions for comparison sessions.

Suggested conditions:
1. `EMPTY`: room empty and equipment stationary.
2. `OCCUPIED_STILL`: one person in the room, relatively still.
3. `MOVEMENT`: a person moves through the room or enters/leaves.

For each session record:
- Session label.
- Date and start/end time.
- Router model, 2.4 GHz SSID/BSSID and channel.
- ESP32 board model.
- Approximate router-to-ESP32 distance.
- Router and ESP32 positions/orientations.
- Environmental changes.
- CSV filename.

If time permits, collect at least three sessions per condition, approximately 2–3 minutes each. This is a practical initial target, not proof of statistical sufficiency.

## Test result log
Copy and complete this table:

| Test ID | Responsible | Date | Result | Evidence / file | Notes |
|---|---|---|---|---|---|
| F1–F4 | Member 1 | | | | |
| D1–D4 | Member 2 | | | | |
| V1–V4 | Member 3 | | | | |
| I1–I5 | Member 4 | | | | |

Use `PASS`, `FAIL` or `NOT TESTED` in the Result column.

## Final evidence checklist
- [ ] Firmware compilation/upload evidence.
- [ ] ESP32 serial output sample.
- [ ] Example CSV.
- [ ] Live graph screenshot.
- [ ] Empty-room data.
- [ ] Occupied/movement data.
- [ ] Comparison graphs or analysis.
- [ ] Completed test log.
- [ ] Known limitations and unresolved issues.

## Interpretation warning
RSSI is affected by people, reflections, multipath, interference, router behavior and other environmental factors. A person may make RSSI rise or fall. Describe what the team's own tests show; do not claim confirmed or reliable presence detection without sufficient validation.
