# Mostafa — Integration and Testing Lead

## Role

You coordinate the four members and ensure their separate contributions work together as one prototype. You are not expected to write every module. You define integration expectations, check deliverables, identify blockers early, organize experiments and prepare the final demonstration.

## Main responsibilities

### 1. Team coordination

- Confirm each member understands their assignment and owns the correct files.
- Set short progress checkpoints and ask for evidence, not only verbal updates.
- Ensure Members 2 and 3 start with simulated data instead of waiting for the ESP32.
- Identify blockers and coordinate help.

### 2. Repository and interfaces

- Maintain `README.md`, `docs/` and `tests/README.md`.
- Coordinate branches, commits and Pull Requests.
- Keep the serial data format consistent.
- Agree changes to shared fields and function interfaces before they are made.
- Do not overwrite another member's work without discussion.

### 3. Hardware preparation

Record the ESP32 board model, router model, 2.4 GHz SSID, BSSID/channel if available, Windows COM port and serial baud rate.

The router sends Wi-Fi signals wirelessly to the ESP32. The ESP32 connects to the laptop by USB. The laptop runs the Python application.

### 4. Software integration

Connect the modules in order:

1. Member 1 firmware produces serial records.
2. Member 2 reader receives and parses them.
3. Member 2 logger saves them to CSV.
4. Member 3 visualization displays the readings and analysis.
5. The application runs the full pipeline on Windows.

If the graph does not update, trace the pipeline step by step: firmware output, serial connection, parsing, data passing and visualization.

### 5. Experiments

Organize empty-room, occupied-still and movement/entry-exit sessions where possible. Keep router and ESP32 positions/orientations fixed. Record room layout, approximate distance, session label, time, channel and environmental changes. Repeat conditions when time allows.

### 6. Final demonstration

Prepare system explanation, live demonstration, sample CSVs, graphs, experimental observations, limitations, future improvements and team contribution summary.

## Files you coordinate

- `README.md`
- `docs/`
- `tests/README.md`
- `python/main.py` only if the team assigns you ownership of the application entry point.

Members 1–3 own their assigned implementation files. Your role is to integrate and verify them.

## Three-day plan

### Day 1 — Setup and independent progress

- Create the shared repository and invite the team.
- Confirm file ownership and branches.
- Confirm router and ESP32 details.
- Agree the exact serial data contract.
- Check the laptop software environment and simulation workflow.
- Collect evidence of each member's progress and identify blockers.

**Day 1 delivery:** repository and responsibilities organized, hardware details recorded, interface agreed and progress checked.

### Day 2 — End-to-end integration

- Test Member 1 firmware on the real ESP32.
- Verify target-router discovery and serial format.
- Connect Member 2's reader and CSV logger to real readings.
- Connect the readings to Member 3's graph.
- Resolve issues with the relevant owner.
- Run a stable test and check for missing/corrupt records.

**Day 2 delivery:** real router-to-ESP32-to-laptop pipeline, live graph and CSV logging.

### Day 3 — Validation and demonstration

- Organize empty-room and occupied/movement sessions.
- Repeat trials where possible.
- Check data and graph results.
- Record limitations and unexpected behavior.
- Prepare final demonstration and report.

**Day 3 delivery:** demo, test evidence, experiment data, graphs and final summary.

## Integration checklist

- [ ] Router is powered and 2.4 GHz network is broadcasting.
- [ ] ESP32 is connected to laptop by USB.
- [ ] Windows recognizes the COM port.
- [ ] ESP32 detects the target router.
- [ ] Firmware outputs valid records.
- [ ] Member 2 parses records correctly.
- [ ] CSV is created and contains valid readings.
- [ ] Member 3 graph updates from real readings.
- [ ] Baseline/status behavior is documented.
- [ ] Empty-room and occupied/movement sessions are recorded.
- [ ] Results and limitations are documented.
- [ ] Final demonstration can be repeated.

## Your deliverables

1. Organized repository and clear team documentation.
2. Agreed data contract and integration instructions.
3. Integrated application receiving real ESP32 measurements.
4. Evidence of serial reception, CSV logging and graph display.
5. Completed test log with pass/fail/not-tested results.
6. Experiment files and comparison graphs.
7. Final demonstration plan and short report.
8. Summary of each member's contribution.

## Progress report format

Ask each member to report:

- Completed:
- Evidence:
- Current problem:
- Next task:
- Help needed:

Do not accept “finished” without a commit, test output, screenshot, sample data or other evidence.

## Limitations

RSSI changes due to people, reflections, multipath, interference, router behavior, device orientation and other environmental factors. A person may make RSSI rise or fall. Do not claim confirmed or reliable presence detection unless repeated experiments support that conclusion. Use `POSSIBLE_CHANGE` for an unvalidated signal-change indicator.
