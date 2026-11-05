# Member 1 — ESP32 Firmware Developer

## Role
You own the ESP32-side software. Your job is to scan the router's Wi-Fi broadcast, measure RSSI and send structured readings to the Windows laptop over USB serial. You are not responsible for the Python graph or CSV application.

## Files you own
`firmware/esp32_wifi_scanner/esp32_wifi_scanner.ino`

You may add supporting firmware files in this folder if necessary. Coordinate major changes with Member 4.

## Tasks
1. **Prepare environment:** install Arduino IDE or the agreed ESP32 environment, install ESP32 board support, select the correct board and COM port.
2. **Scan Wi-Fi:** configure the ESP32 to scan nearby Wi-Fi access points. Confirm that the router broadcasts a 2.4 GHz network. Identify the target using SSID and, if possible, BSSID.
3. **Read measurements:** obtain SSID, BSSID, channel, RSSI in dBm and ESP32 uptime in milliseconds if available.
4. **Transmit data:** send one record per target-router reading over USB serial.
5. **Test hardware:** upload to the physical ESP32, open the serial monitor at 115200 baud, verify router discovery and confirm repeated numeric RSSI readings.

## Required output format
```text
DATA,<esp32_millis>,"<ssid>","<bssid>",<channel>,<rssi>
```
Example:
```text
DATA,12345,"LabRouter","AA:BB:CC:DD:EE:FF",6,-57
```
Do not change this format without agreement with Members 2 and 4. Keep debug messages distinguishable from measurement records.

## Deliverables
- Completed firmware source in the owned folder.
- Evidence that it compiles and uploads to the actual ESP32.
- At least 10 valid serial measurement records.
- ESP32 board model, router SSID/BSSID and channel.
- Baud rate and approximate scan interval.
- Short explanation of the firmware and known limitations.

## Acceptance criteria
Firmware compiles for the team's board, detects the selected 2.4 GHz router, reads RSSI and emits records in the agreed format. Member 2 must be able to parse the output without changing the data contract.

## Dependencies and communication
You need the physical ESP32 for final hardware testing, the router's 2.4 GHz SSID, and agreement on the serial format. You can begin before the Python application is ready by using the Arduino serial monitor.

## Report to Member 4
State whether compilation, upload, router discovery and serial output succeeded. Provide at least 10 sample records and report blockers.

**Important:** Fake readings help other members develop their software, but only the real ESP32 and router verify actual Wi-Fi scanning and RSSI measurement.
