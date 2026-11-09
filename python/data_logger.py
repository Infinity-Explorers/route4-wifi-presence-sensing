from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import datetime, timezone
from typing import Iterable, Optional

try:
    from serial_reader import (
        DEFAULT_BAUD,
        Reading,
        SerialConnectionError,
        SerialReader,
    )
except ImportError:
    from python.serial_reader import (
        DEFAULT_BAUD,
        Reading,
        SerialConnectionError,
        SerialReader,
    )

BASE_COLUMNS = ["timestamp_utc", "esp32_millis", "ssid", "bssid", "channel", "rssi_dbm"]
SUGGESTED_LABELS = ("EMPTY", "OCCUPIED_STILL", "MOVEMENT")


class DataLoggerError(RuntimeError):
    """The CSV file could not be created or written."""


def utc_now_iso() -> str:
    """Current UTC time, ISO 8601 with milliseconds, e.g. 2026-11-07T10:30:15.123Z"""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def make_session_path(label: str = "session", directory: str = "data") -> str:
    """data/<label>_<YYYYMMDD_HHMMSS>.csv (UTC) so files never overwrite each other."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in label) or "session"
    return os.path.join(directory, f"{safe}_{stamp}.csv")


class CSVLogger:
    def __init__(self, path: str, extra_columns: Iterable[str] = ()):
        self.path = path
        self.columns = BASE_COLUMNS + [c for c in extra_columns if c not in BASE_COLUMNS]
        self.rows_written = 0
        self._file = None
        self._writer = None

    # -- lifecycle ----------------------------------------------------------
    def open(self) -> None:
        if self._file is not None:
            return
        try:
            folder = os.path.dirname(self.path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            # "x" = never silently overwrite an existing recording.
            # utf-8-sig adds the BOM that makes Excel read UTF-8 correctly.
            self._file = open(self.path, "x", newline="", encoding="utf-8-sig")
            self._writer = csv.DictWriter(self._file, fieldnames=self.columns)
            self._writer.writeheader()
            self._file.flush()
        except FileExistsError as exc:
            raise DataLoggerError(f"{self.path} already exists; refusing to overwrite it.") from exc
        except OSError as exc:
            raise DataLoggerError(
                f"Cannot create {self.path}: {exc}. Check the folder exists, "
                "you have write permission, and the disk is not full."
            ) from exc

    def close(self) -> None:
        if self._file is not None:
            try:
                self._file.close()
            finally:
                self._file = None
                self._writer = None

    def __enter__(self) -> "CSVLogger":
        self.open()
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # -- logging ------------------------------------------------------------
    def log(self, reading: Reading, **extra) -> None:
        """Append one row. Missing extra columns are left blank."""
        if self._writer is None:
            raise DataLoggerError("Logger is not open. Call open() first.")
        row = {"timestamp_utc": utc_now_iso(), **reading.as_dict()}
        for col in self.columns[len(BASE_COLUMNS):]:
            row[col] = extra.get(col, "")
        try:
            self._writer.writerow(row)
            self._file.flush()
        except (OSError, ValueError) as exc:
            raise DataLoggerError(
                f"Failed writing to {self.path}: {exc}. Disk full, file locked or removed?"
            ) from exc
        self.rows_written += 1


# ---------------------------------------------------------------------------
# Recording session (reader + logger)
# ---------------------------------------------------------------------------
def run_logging(
    port: Optional[str],
    baud: int = DEFAULT_BAUD,
    label: str = "UNLABELED",
    out_path: Optional[str] = None,
    duration: Optional[float] = None,
    max_records: Optional[int] = None,
    target_bssid: Optional[str] = None,
    silence_warn_s: float = 5.0,
    reader: Optional[SerialReader] = None,
    verbose: bool = True,
) -> dict:
    """Record readings to CSV until duration / max_records / Ctrl+C.

    Returns a summary dict (also useful for the report to Mostafa).
    """
    reader = reader or SerialReader(port, baud, target_bssid=target_bssid)
    path = out_path or make_session_path(label)
    summary = {
        "port": port or "(injected)", "baud": baud, "label": label, "csv_file": path,
        "valid_records_saved": 0, "malformed": 0, "ignored": 0, "filtered": 0,
        "rssi_min": None, "rssi_max": None, "rssi_mean": None,
        "duration_s": 0.0, "stopped_because": "", "error": "",
    }
    rssi_sum = 0
    started = last_valid = time.monotonic()

    try:
        with reader, CSVLogger(path, extra_columns=("session_label",)) as logger:
            while True:
                now = time.monotonic()
                if duration is not None and now - started >= duration:
                    summary["stopped_because"] = "duration reached"
                    break
                if max_records is not None and logger.rows_written >= max_records:
                    summary["stopped_because"] = "max records reached"
                    break

                r = reader.read_reading()
                if r is None:
                    if now - last_valid >= silence_warn_s:
                        print(f"WARNING: no valid readings for {now - last_valid:.0f}s - "
                              "check ESP32 power/USB, baud rate and that it sees the router.",
                              file=sys.stderr)
                        last_valid = now  # warn again after another interval
                    continue

                last_valid = now
                logger.log(r, session_label=label)
                summary["valid_records_saved"] += 1
                rssi_sum += r.rssi_dbm
                lo, hi = summary["rssi_min"], summary["rssi_max"]
                summary["rssi_min"] = r.rssi_dbm if lo is None else min(lo, r.rssi_dbm)
                summary["rssi_max"] = r.rssi_dbm if hi is None else max(hi, r.rssi_dbm)
                if verbose:
                    print(f"[{logger.rows_written}] {r.rssi_dbm} dBm  ch{r.channel}  {r.ssid}")
    except KeyboardInterrupt:
        summary["stopped_because"] = "stopped by user (Ctrl+C)"
    except (SerialConnectionError, DataLoggerError) as exc:
        summary["stopped_because"] = "error"
        summary["error"] = str(exc)
    finally:
        s = reader.stats
        summary.update(malformed=s.malformed, ignored=s.ignored, filtered=s.filtered)
        summary["duration_s"] = round(time.monotonic() - started, 1)
        if summary["rssi_min"] is not None:
            summary["rssi_mean"] = round(rssi_sum / summary["valid_records_saved"], 2)
    return summary


def print_summary(summary: dict) -> None:
    print("\n=== Session summary (for the report to Mostafa) ===")
    for key, value in summary.items():
        if value not in ("", None):
            print(f"{key:>22}: {value}")


def main(argv: Optional[list] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    ap = argparse.ArgumentParser(description="Log Route 4 RSSI readings to a timestamped CSV.")
    ap.add_argument("--port", required=False, help="COM port, e.g. COM5 (see: serial_reader.py --list)")
    ap.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    ap.add_argument("--label", default="UNLABELED", help="EMPTY / OCCUPIED_STILL / MOVEMENT")
    ap.add_argument("--out", help="CSV path (default: data/<label>_<UTC time>.csv)")
    ap.add_argument("--duration", type=float, help="stop after N seconds")
    ap.add_argument("--max-records", type=int, help="stop after N valid readings")
    ap.add_argument("--bssid", help="only log this router BSSID")
    args = ap.parse_args(argv)

    if args.label not in SUGGESTED_LABELS:
        print(f"Note: label {args.label!r} is not one of {SUGGESTED_LABELS}.", file=sys.stderr)

    summary = run_logging(args.port, args.baud, args.label, args.out,
                          args.duration, args.max_records, args.bssid)
    print_summary(summary)
    return 0 if not summary["error"] else 2


if __name__ == "__main__":
    sys.exit(main())
