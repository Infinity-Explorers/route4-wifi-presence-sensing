"""
Main Integration Application for Route 4: Wi-Fi Presence Sensing.
Coordinated by Mostafa (Member 4 - Integration Lead).

Connects:
- Member 1: ESP32 Firmware Telemetry (waiting for firmware)
- Member 2: Serial Reader & CSV Data Logger (Yousef)
- Member 3: Real-Time Signal Analysis & Dark-Themed GUI Visualizer (Tasneem)
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import signal
import sys
import time
from typing import Optional, List, Iterator

# Ensure python directory is in sys.path
sys.path.insert(0, os.path.dirname(__file__))

from serial_reader import (
    DEFAULT_BAUD,
    Reading,
    SerialConnectionError,
    SerialReader,
    available_ports,
)
from data_logger import (
    CSVLogger,
    DataLoggerError,
    make_session_path,
    SUGGESTED_LABELS,
)
from visualizer import RSSIVisualizer

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

log = logging.getLogger("route4.main")


class SimulatedSerialSource:
    """Generates synthetic RSSI readings conforming to the agreed data contract."""

    def __init__(self, target_bssid: str = "AA:BB:CC:DD:EE:FF", target_ssid: str = "LabRouter"):
        self.target_bssid = target_bssid
        self.target_ssid = target_ssid
        self.base_rssi = -55.0
        self.cycle = 0
        self.start_time = time.monotonic()

    def read_available(self) -> List[Reading]:
        """Generates 1 reading every ~300ms."""
        self.cycle += 1
        elapsed_ms = int((time.monotonic() - self.start_time) * 1000)

        # Simulate movement disturbance every 15-22 cycles
        is_movement = (self.cycle % 35) in range(15, 23)
        noise = random.gauss(0, 5.0 if is_movement else 0.8)
        rssi = int(round(self.base_rssi + noise))
        # Keep within valid bounds
        rssi = max(-95, min(-30, rssi))

        reading = Reading(
            esp32_millis=elapsed_ms,
            ssid=self.target_ssid,
            bssid=self.target_bssid,
            channel=6,
            rssi_dbm=rssi,
        )
        return [reading]

    def readings(self) -> Iterator[Reading]:
        while True:
            for r in self.read_available():
                yield r
            time.sleep(0.3)

    def close(self):
        pass


def parse_arguments(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Route 4: Integrated Wi-Fi Presence Sensing System"
    )
    parser.add_argument(
        "--port",
        type=str,
        default=None,
        help="ESP32 serial port (e.g. COM3 or /dev/ttyUSB0). If omitted, scans available ports.",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=DEFAULT_BAUD,
        help=f"Serial baud rate (default: {DEFAULT_BAUD})",
    )
    parser.add_argument(
        "--label",
        type=str,
        default="EMPTY",
        choices=SUGGESTED_LABELS,
        help="Experimental session condition: EMPTY, OCCUPIED_STILL, or MOVEMENT",
    )
    parser.add_argument(
        "--bssid",
        type=str,
        default=None,
        help="Target router BSSID filter (e.g. AA:BB:CC:DD:EE:FF)",
    )
    parser.add_argument(
        "--calibrate",
        type=int,
        default=15,
        help="Number of initial samples to establish the empty-room baseline (default: 15)",
    )
    parser.add_argument(
        "--simulate",
        "--mock",
        dest="simulate",
        action="store_true",
        help="Run in simulation mode without physical ESP32 hardware",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Disable GUI and run in headless console logging mode",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Custom CSV destination path (default: data/<label>_<UTC_TIMESTAMP>.csv)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Stop session after N seconds",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Stop session after N valid records",
    )
    return parser.parse_args(argv)


def select_port(explicit_port: Optional[str]) -> Optional[str]:
    """Resolves COM port or prompts the user with available ports."""
    if explicit_port:
        return explicit_port

    ports = available_ports()
    if not ports:
        return None

    if len(ports) == 1:
        print(f"[INFO] Auto-selected single available port: {ports[0][0]} ({ports[0][1]})")
        return ports[0][0]

    print("\nAvailable COM Ports:")
    for idx, (p, desc) in enumerate(ports, start=1):
        print(f"  [{idx}] {p} - {desc}")
    print("Please specify a port using '--port <PORT>' or run with '--simulate'.\n")
    return None


def print_banner(mode: str, label: str, csv_path: str, baud: int):
    print("=" * 65)
    print("   ROUTE 4: WI-FI RSSI PRESENCE SENSING SYSTEM")
    print("=" * 65)
    print(f"  Mode           : {mode}")
    print(f"  Session Label  : {label}")
    print(f"  CSV Output     : {csv_path}")
    print(f"  Baud Rate      : {baud}")
    print("  Controls       : Press Ctrl+C or close plot window to stop")
    print("=" * 65 + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_arguments(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # 1. Resolve Data Source
    reader = None
    if args.simulate:
        reader = SimulatedSerialSource(target_bssid=args.bssid or "AA:BB:CC:DD:EE:FF")
        mode_str = "SIMULATION (Synthetic Telemetry)"
    else:
        port = select_port(args.port)
        if not port:
            print("[ERROR] No ESP32 serial port specified or found.")
            print("Tip: Connect your ESP32 or pass '--simulate' to test without hardware.")
            return 1
        reader = SerialReader(port=port, baudrate=args.baud, target_bssid=args.bssid)
        try:
            reader.open()
        except SerialConnectionError as exc:
            print(f"[ERROR] Failed to open serial port: {exc}", file=sys.stderr)
            return 2
        mode_str = f"LIVE ESP32 ({port})"

    # 2. Setup CSV Logger
    csv_path = args.out or make_session_path(args.label)
    try:
        logger = CSVLogger(csv_path, extra_columns=["status", "session_label"])
        logger.open()
    except DataLoggerError as exc:
        print(f"[ERROR] Could not initialize CSV logger: {exc}", file=sys.stderr)
        if reader and hasattr(reader, "close"):
            reader.close()
        return 3

    print_banner(mode_str, args.label, csv_path, args.baud)

    # 3. Setup Metrics Tracking
    session_start = time.monotonic()
    valid_count = 0
    rssi_min: Optional[int] = None
    rssi_max: Optional[int] = None
    rssi_sum = 0
    running = True

    def handle_sigint(signum, frame):
        nonlocal running
        print("\n[INFO] Interrupt caught, completing session...")
        running = False

    signal.signal(signal.SIGINT, handle_sigint)

    # 4. Live Visualization vs Headless Mode
    if not args.no_plot:
        vis = RSSIVisualizer(
            calibration_count=args.calibrate,
            title=f"Route 4: Wi-Fi Presence Sensing [{args.label}]",
        )

        def on_anim_frame(_):
            nonlocal valid_count, rssi_min, rssi_max, rssi_sum, running

            if not running:
                plt.close(vis.fig)
                return vis.line, vis.rssi_text, vis.status_text

            elapsed = time.monotonic() - session_start
            if args.duration and elapsed >= args.duration:
                print("\n[INFO] Target duration reached.")
                running = False
                plt.close(vis.fig)
                return vis.line, vis.rssi_text, vis.status_text

            if args.max_records and valid_count >= args.max_records:
                print("\n[INFO] Target max records reached.")
                running = False
                plt.close(vis.fig)
                return vis.line, vis.rssi_text, vis.status_text

            # Pull waiting readings non-blockingly
            try:
                incoming = reader.read_available()
            except SerialConnectionError as exc:
                print(f"\n[ERROR] Connection lost: {exc}")
                running = False
                plt.close(vis.fig)
                return vis.line, vis.rssi_text, vis.status_text

            for r in incoming:
                status, _ = vis.add_reading(r.rssi_dbm, elapsed_seconds=round(elapsed, 2))
                logger.log(r, session_label=args.label, status=status)

                valid_count += 1
                rssi_sum += r.rssi_dbm
                rssi_min = r.rssi_dbm if rssi_min is None else min(rssi_min, r.rssi_dbm)
                rssi_max = r.rssi_dbm if rssi_max is None else max(rssi_max, r.rssi_dbm)

                indicator = " [!]" if status == "POSSIBLE_CHANGE" else "    "
                print(
                    f"[{valid_count:4d}] {r.rssi_dbm:3d} dBm | ch{r.channel:2d} | Status: {status:<18}{indicator}"
                )

            return vis.update_plot()

        ani = FuncAnimation(vis.fig, on_anim_frame, interval=250, cache_frame_data=False)
        try:
            plt.show()
        except KeyboardInterrupt:
            pass

    else:
        # Headless console logging
        print("[INFO] Running in headless mode (no GUI).")
        try:
            while running:
                elapsed = time.monotonic() - session_start
                if args.duration and elapsed >= args.duration:
                    break
                if args.max_records and valid_count >= args.max_records:
                    break

                r = reader.read_reading() if hasattr(reader, "read_reading") else None
                if r is None and isinstance(reader, SimulatedSerialSource):
                    sim_batch = reader.read_available()
                    r = sim_batch[0] if sim_batch else None
                    time.sleep(0.3)

                if r is None:
                    continue

                valid_count += 1
                rssi_sum += r.rssi_dbm
                rssi_min = r.rssi_dbm if rssi_min is None else min(rssi_min, r.rssi_dbm)
                rssi_max = r.rssi_dbm if rssi_max is None else max(rssi_max, r.rssi_dbm)

                logger.log(r, session_label=args.label, status="LOGGED")
                print(f"[{valid_count:4d}] {r.rssi_dbm:3d} dBm  ch{r.channel}  {r.ssid}")
        except KeyboardInterrupt:
            pass

    # 5. Clean teardown and Summary Report
    duration_total = round(time.monotonic() - session_start, 1)
    logger.close()
    if reader and hasattr(reader, "close"):
        reader.close()

    mean_rssi = round(rssi_sum / valid_count, 2) if valid_count > 0 else 0.0

    print("\n" + "=" * 50)
    print("       ROUTE 4: SESSION SUMMARY REPORT")
    print("=" * 50)
    print(f"  Condition Label : {args.label}")
    print(f"  Records Saved   : {valid_count}")
    print(f"  Duration        : {duration_total} seconds")
    print(f"  RSSI Min        : {rssi_min} dBm")
    print(f"  RSSI Max        : {rssi_max} dBm")
    print(f"  RSSI Mean       : {mean_rssi} dBm")
    print(f"  Saved File      : {csv_path}")
    print("=" * 50 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
