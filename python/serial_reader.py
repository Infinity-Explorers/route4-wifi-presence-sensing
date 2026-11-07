from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
from dataclasses import asdict, dataclass
from typing import Iterator, List, Optional, Tuple

try:
    import serial
    from serial import SerialException
    from serial.tools import list_ports
except ImportError:  # pyserial missing: give a clear message later, in open()
    serial = None
    list_ports = None

    class SerialException(Exception):  # type: ignore[no-redef]
        pass


log = logging.getLogger("route4.serial_reader")

# ---------------------------------------------------------------------------
# Agreed data contract (change ONLY after agreement with Members 1, 3 and 4)
# ---------------------------------------------------------------------------
DEFAULT_BAUD = 115200
RECORD_PREFIX = "DATA"
EXPECTED_FIELDS = 6  # DATA, millis, ssid, bssid, channel, rssi
BSSID_RE = re.compile(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")
CHANNEL_RANGE = (1, 14)    # 2.4 GHz Wi-Fi channels
RSSI_RANGE = (-127, 0)     # dBm; anything outside is certainly corrupt


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class ParseError(ValueError):
    """A line looked like a DATA record but is invalid (malformed)."""


class NotARecord(ParseError):
    """A line is not a DATA record at all (blank, boot message, debug text)."""


class SerialConnectionError(RuntimeError):
    """Port could not be opened, or the connection was lost."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Reading:
    esp32_millis: int
    ssid: str
    bssid: str
    channel: int
    rssi_dbm: int

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReaderStats:
    valid: int = 0
    malformed: int = 0
    ignored: int = 0     # blank lines, boot messages, other non-DATA text
    filtered: int = 0    # valid records from a different BSSID than target
    last_error: str = ""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def parse_line(line: str) -> Reading:
    """Parse one serial line into a Reading.

    Raises NotARecord for lines that are not DATA records (safe to ignore) and
    ParseError for DATA records that are malformed (should be reported).
    """
    text = line.strip().lstrip("\ufeff")
    if not text:
        raise NotARecord("blank line")
    if not text.startswith(RECORD_PREFIX + ","):
        raise NotARecord(f"not a DATA record: {text[:60]!r}")

    # csv handles the quoted SSID correctly, even if it contains commas.
    try:
        fields = next(csv.reader([text]))
    except (csv.Error, StopIteration) as exc:
        raise ParseError(f"cannot split record ({exc}): {text[:80]!r}") from exc

    if len(fields) != EXPECTED_FIELDS:
        raise ParseError(
            f"expected {EXPECTED_FIELDS} fields, got {len(fields)}: {text[:80]!r}"
        )

    _, millis_s, ssid, bssid, channel_s, rssi_s = fields

    try:
        millis = int(millis_s)
        channel = int(channel_s)
        rssi = int(rssi_s)
    except ValueError as exc:
        raise ParseError(f"non-numeric millis/channel/rssi: {text[:80]!r}") from exc

    if millis < 0:
        raise ParseError(f"negative esp32_millis ({millis})")
    if not BSSID_RE.match(bssid):
        raise ParseError(f"invalid BSSID {bssid!r}")
    if not CHANNEL_RANGE[0] <= channel <= CHANNEL_RANGE[1]:
        raise ParseError(f"channel {channel} outside {CHANNEL_RANGE}")
    if not RSSI_RANGE[0] <= rssi <= RSSI_RANGE[1]:
        raise ParseError(f"RSSI {rssi} dBm outside {RSSI_RANGE}")

    return Reading(millis, ssid, bssid.upper(), channel, rssi)


# ---------------------------------------------------------------------------
# Port helpers
# ---------------------------------------------------------------------------
def available_ports() -> List[Tuple[str, str]]:
    """Return [(device, description)] for every serial port Windows sees."""
    if list_ports is None:
        return []
    return [(p.device, p.description) for p in list_ports.comports()]


def _ports_hint() -> str:
    ports = available_ports()
    if not ports:
        return "No serial ports detected (is the ESP32 plugged in? USB driver installed?)."
    return "Available ports: " + "; ".join(f"{d} ({desc})" for d, desc in ports)


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------
class SerialReader:
    """Reads and parses DATA records from a COM port.

    `serial_obj` lets tests inject a fake port; normal use passes `port`.
    `target_bssid` (optional) drops valid records from other access points.
    """

    def __init__(
        self,
        port: Optional[str] = None,
        baud: int = DEFAULT_BAUD,
        timeout: float = 1.0,
        target_bssid: Optional[str] = None,
        serial_obj=None,
    ):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.target_bssid = target_bssid.upper() if target_bssid else None
        self.stats = ReaderStats()
        self._ser = serial_obj
        self._buf = b""

    # -- connection ---------------------------------------------------------
    def open(self) -> None:
        if self._ser is not None:
            return
        if serial is None:
            raise SerialConnectionError("pyserial is not installed. Run: pip install pyserial")
        if not self.port:
            raise SerialConnectionError(f"No COM port selected. Use --port COM5. {_ports_hint()}")
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        except (SerialException, OSError, ValueError) as exc:
            raise SerialConnectionError(self._open_error_message(exc)) from exc
        try:
            self._ser.reset_input_buffer()
        except (SerialException, OSError):
            pass
        log.info("Opened %s at %d baud", self.port, self.baud)

    def _open_error_message(self, exc: Exception) -> str:
        text = str(exc)
        low = text.lower()
        if "access is denied" in low or "permission" in low or "busy" in low:
            why = ("The port is busy. Close the Arduino Serial Monitor / PlatformIO "
                   "monitor / any other program using it, then try again.")
        elif "could not open port" in low or "filenotfound" in low or "cannot find" in low:
            why = "That COM port does not exist. Check Device Manager -> Ports (COM & LPT)."
        else:
            why = "Check the USB cable and that the ESP32 driver is installed."
        return f"Cannot open {self.port} at {self.baud} baud: {text}. {why} {_ports_hint()}"

    def close(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            except (SerialException, OSError):
                pass
            self._ser = None

    def __enter__(self) -> "SerialReader":
        self.open()
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # -- reading ------------------------------------------------------------
    def read_line(self) -> Optional[str]:
        """Return one complete decoded line, or None on timeout / partial line."""
        if self._ser is None:
            raise SerialConnectionError("Port is not open. Call open() first.")
        try:
            raw = self._ser.readline()
        except (SerialException, OSError) as exc:
            raise SerialConnectionError(
                f"Lost connection to {self.port}: {exc}. "
                "Was the ESP32 unplugged or reset? Reconnect it and restart."
            ) from exc
        if not raw:
            return None  # timeout: no data within `timeout` seconds
        if not raw.endswith(b"\n"):
            # Timeout hit mid-line: keep the fragment and wait for the rest.
            self._buf += raw
            return None
        line, self._buf = self._buf + raw, b""
        return line.decode("utf-8", errors="replace")  # never crash on bad bytes

    def read_reading(self) -> Optional[Reading]:
        """Read one line; return a Reading, or None if nothing usable arrived."""
        line = self.read_line()
        if line is None:
            return None
        try:
            reading = parse_line(line)
        except NotARecord as exc:
            self.stats.ignored += 1
            log.debug("Ignored: %s", exc)
            return None
        except ParseError as exc:
            self.stats.malformed += 1
            self.stats.last_error = str(exc)
            log.warning("Skipping malformed record: %s", exc)
            return None
        if self.target_bssid and reading.bssid != self.target_bssid:
            self.stats.filtered += 1
            return None
        self.stats.valid += 1
        return reading

    def readings(self) -> Iterator[Reading]:
        """Blocking generator of valid readings (stop it with `break`/Ctrl+C)."""
        while True:
            reading = self.read_reading()
            if reading is not None:
                yield reading

    def read_available(self) -> List[Reading]:
        """Non-blocking: return all readings already waiting in the port buffer.

        Designed for GUI loops (matplotlib FuncAnimation) that must not block.
        """
        out: List[Reading] = []
        try:
            waiting = getattr(self._ser, "in_waiting", 0)
        except (SerialException, OSError) as exc:
            raise SerialConnectionError(f"Lost connection to {self.port}: {exc}") from exc
        while waiting > 0:
            reading = self.read_reading()
            if reading is not None:
                out.append(reading)
            try:
                waiting = self._ser.in_waiting
            except (SerialException, OSError) as exc:
                raise SerialConnectionError(f"Lost connection to {self.port}: {exc}") from exc
        return out


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles + non-ASCII SSIDs
        sys.stdout.reconfigure(errors="replace")

    ap = argparse.ArgumentParser(description="Read and print Route 4 RSSI records.")
    ap.add_argument("--port", help="COM port, e.g. COM5")
    ap.add_argument("--baud", type=int, default=DEFAULT_BAUD, help="default 115200")
    ap.add_argument("--bssid", help="only keep this router BSSID")
    ap.add_argument("--count", type=int, default=0, help="stop after N valid readings (0 = run until Ctrl+C)")
    ap.add_argument("--list", action="store_true", help="list COM ports and exit")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.list:
        ports = available_ports()
        print("\n".join(f"{d}  {desc}" for d, desc in ports) if ports else "No serial ports found.")
        return 0

    reader = SerialReader(args.port, args.baud, target_bssid=args.bssid)
    try:
        with reader:
            for n, r in enumerate(reader.readings(), start=1):
                print(f"[{n}] t={r.esp32_millis} ms  {r.ssid}  {r.bssid}  ch{r.channel}  {r.rssi_dbm} dBm")
                if args.count and n >= args.count:
                    break
    except SerialConnectionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nStopped by user.")
    s = reader.stats
    print(f"valid={s.valid} malformed={s.malformed} ignored={s.ignored} filtered={s.filtered}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
