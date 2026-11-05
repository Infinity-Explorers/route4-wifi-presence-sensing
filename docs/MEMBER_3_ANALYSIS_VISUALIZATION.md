# Tasneem — Signal Analysis and Visualization Developer

## Role
You display RSSI measurements and analyze how they vary across room conditions. You help the team interpret its data; you do not own ESP32 firmware or serial-port acquisition.

## File you own
`python/visualizer.py`

Coordinate input fields with Member 2 and integration interfaces with Member 4.

## Tasks
1. **Live graph:** show RSSI in dBm with clear axes; update as readings arrive and remain readable over time.
2. **Empty-room baseline:** use an agreed initial period with the room empty and equipment stationary. Calculate a baseline such as mean RSSI; optionally calculate standard deviation.
3. **Compare readings:** compare current readings with the baseline. Suggested statuses: `CALIBRATING`, `STABLE` and `POSSIBLE_CHANGE`.
4. **Document the method:** explain baseline duration, number of samples, threshold selection and how the status is determined.
5. **Analyze sessions:** compare `EMPTY`, `OCCUPIED_STILL` and `MOVEMENT` sessions where available. Useful metrics include mean, minimum, maximum, standard deviation and time-series plots.
6. **Use simulation first:** develop and test the graph with fake/sample readings before real ESP32 data is available.

## Deliverables
- Completed `python/visualizer.py`.
- Working live RSSI graph with clear labels and dBm units.
- Explanation of baseline and change-detection method.
- Screenshot of graph using simulated data.
- Graphs and analysis from real experiments when available.
- Short conclusion describing observations and limitations.

## Acceptance criteria
The graph updates when readings arrive, displays RSSI in dBm, is readable, and works with the data structure agreed with Member 2. Baseline and threshold logic are documented. The analysis does not call a signal change proof of human presence.

## Dependencies and communication
You need parsed RSSI readings from Member 2, agreement on function inputs and experimental labels from Member 4. You do not need to wait for the ESP32; use simulated readings first.

## Report to Mostafa
Report whether the graph works with simulation, what input structure it expects, how baseline/threshold are calculated, and provide screenshots and real-data observations when available.

**Scientific caution:** A person may make RSSI rise or fall depending on the environment and signal path. Multipath, interference and other environmental changes also affect RSSI. The graph shows signal behavior; it does not independently prove presence.
