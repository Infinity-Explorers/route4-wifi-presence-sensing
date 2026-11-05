# Route 4 — Wi-Fi RSSI-Based Human Presence Sensing

## Project purpose
Route 4 is an experimental prototype investigating whether changes in Wi-Fi received signal strength (RSSI) can indicate possible human presence or movement in a room. The router broadcasts Wi-Fi signals, an ESP32 scans the router and measures RSSI, and a Windows laptop receives, stores and displays the readings.

This is an experiment, not a proven commercial or safety-grade presence detector.

## System operation
1. The router broadcasts its 2.4 GHz Wi-Fi network.
2. The ESP32 scans nearby Wi-Fi access points and reads RSSI for the target router.
3. The ESP32 sends readings to the laptop over USB serial.
4. Python software receives and parses the readings.
5. The software saves measurements to CSV and displays a live graph.
6. The team compares empty-room measurements with occupied-room or movement measurements.

**Connections:** Router to ESP32 is wireless. ESP32 to laptop is USB. The ESP32 does not need to join the router's network or know its password for passive scanning. The laptop does not need to connect to the router for this basic setup.

## Team responsibilities and ownership

| Member | Role | Files / ownership | Expected delivery |
|---|---|---|---|
| Menna | ESP32 Firmware Developer | `firmware/esp32_wifi_scanner/` | Tested firmware, router discovery and RSSI serial records |
| Yousef | Data Acquisition Developer | `python/serial_reader.py`, `python/data_logger.py` | Serial reading, parsing and timestamped CSV logging |
| Tasneem | Signal Analysis & Visualization Developer | `python/visualizer.py` | Live RSSI graph, baseline comparison and documented analysis |
| Mostafa | Integration & Testing Lead | `README.md`, `docs/`, `tests/README.md`; coordinate `python/main.py` integration | Complete pipeline, experiments, test evidence and final demonstration |

Each member must read their detailed assignment in `docs/`.

## Shared serial data contract
Member 1 produces this exact record; Member 2 parses it:

```text
DATA,<esp32_millis>,"<ssid>","<bssid>",<channel>,<rssi>
```

Example:

```text
DATA,12345,"LabRouter","AA:BB:CC:DD:EE:FF",6,-57
```

Fields: ESP32 uptime in milliseconds, SSID, BSSID, Wi-Fi channel and RSSI in dBm. Do not change field order or meaning without agreement between Members 1, 2 and 4. Initial baud rate: 115200.

## Three-day plan

### Day 1 — Independent development
- Menna: compile and start testing the ESP32 scanner.
- Yousef: implement parsing and CSV logging using sample records.
- Tasneem: build graph and analysis using simulated readings.
- Mostafa: prepare repository, confirm hardware details, agree on the data format and check progress.
**Checkpoint:** each member demonstrates independent progress. Members 2 and 3 must not wait for the physical ESP32.

### Day 2 — Integration
- Test Member 1 firmware on the real ESP32.
- Confirm router detection and valid serial output.
- Connect Member 2's reader and logger to real data.
- Connect parsed readings to Member 3's graph.
- Check the complete pipeline and fix interface issues.
**Checkpoint:** real readings appear live and are saved to CSV.

### Day 3 — Experiments and demonstration
- Record empty-room readings.
- Record occupied-still and/or movement readings.
- Repeat conditions where time allows.
- Compare graphs and measurements.
- Document results, limitations and unresolved issues.
- Prepare final demonstration and report.
**Checkpoint:** team demonstrates the complete prototype and explains what the data supports.

## Experimental rules
Keep router and ESP32 positions and orientations fixed during comparison sessions. Record room layout, approximate distance, SSID/BSSID, channel, test condition, session time and unusual environmental changes. Suggested labels: `EMPTY`, `OCCUPIED_STILL`, `MOVEMENT`.

Do not assume a person always makes RSSI decrease. Reflections, multipath, interference, router behavior and other environmental changes can make RSSI rise or fall.

## Git collaboration
- Each member mainly edits their assigned files.
- Use a separate branch per member.
- Commit small, understandable changes.
- Push the branch and open a Pull Request for review.
- Discuss changes to shared interfaces before making them.
- Member 4 integrates continuously rather than waiting until Day 3.

Suggested branches: `Menna/firmware`, `Yousef/data-acquisition`, `Tasneem/visualization`, `Mostafa/integration`.

## Final acceptance criteria
1. ESP32 detects the target router's 2.4 GHz broadcast.
2. ESP32 emits valid RSSI records over USB serial.
3. Laptop parses the records.
4. Readings are saved to timestamped CSV.
5. Live graph displays readings.
6. Empty-room and occupied/movement experiments are recorded and compared.
7. Team documents findings and limitations without overstating detection reliability.
