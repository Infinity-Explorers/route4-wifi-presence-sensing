# Member 2 — Data Acquisition and CSV Developer

## Role
You receive measurement records from the ESP32, parse them into structured fields, add timestamps and save them to CSV. You own the data acquisition path, not the ESP32 firmware or final graph design.

## Files you own
- `python/serial_reader.py`
- `python/data_logger.py`

Coordinate data structures and interface changes with Members 3 and 4.

## Tasks
1. **Understand the record:** parse `DATA,<esp32_millis>,"<ssid>","<bssid>",<channel>,<rssi>`.
2. **Read serial:** open the selected Windows COM port at the agreed baud rate (initially 115200), continuously read lines and decode safely.
3. **Parse valid records:** extract uptime, SSID, BSSID, channel and RSSI with suitable data types.
4. **Handle invalid input:** ignore or report blank lines, startup messages and malformed records without crashing.
5. **Log CSV:** save one row per valid reading with a header. Recommended columns: `timestamp_utc`, `esp32_millis`, `ssid`, `bssid`, `channel`, `rssi_dbm`. The integrated application may also add `baseline_dbm`, `status` and `session_label`.
6. **Handle errors:** wrong or busy COM port, disconnected ESP32, serial timeout and file-write failures should produce useful messages.

## Start without hardware
Use this sample record to test parsing:
```text
DATA,12345,"LabRouter","AA:BB:CC:DD:EE:FF",6,-57
```
Verify the parsed values and CSV output. You can start immediately; do not wait for Member 1.

## Deliverables
- Completed `serial_reader.py`.
- Completed `data_logger.py`.
- Evidence that valid records are parsed correctly.
- Evidence that malformed lines are handled safely.
- Example CSV with a header and several readings.
- Instructions for COM port and baud rate.
- Short explanation of implementation and limitations.

## Acceptance criteria
The reader can receive from the selected COM port, valid records become structured readings, invalid lines do not crash the app, each valid reading is timestamped and saved, and the CSV opens correctly in Excel.

## Dependencies and communication
You need Member 1's agreed serial format, Member 3's expected input structure and Member 4's confirmed COM port/baud rate. Discuss interface changes before implementing them.

## Report to Member 4
Report the COM port tested, whether real readings arrived, number of valid records saved, CSV filename and any connection/parsing issues.

**Important:** You can build and test using sample records before the ESP32 is ready. Real hardware testing is still required for final integration.
