"""
Tests for python/serial_reader.py and python/data_logger.py (Yousef).
Run from the repo root:   python -m unittest tests.test_data_acquisition -v
No ESP32 needed: a fake serial port is used.
"""
import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from serial_reader import (  # noqa: E402
    NotARecord, ParseError, Reading, SerialConnectionError, SerialReader, parse_line,
)
from data_logger import CSVLogger, DataLoggerError, run_logging  # noqa: E402

SAMPLE = 'DATA,12345,"LabRouter","AA:BB:CC:DD:EE:FF",6,-57'


class FakeSerial:
    """Mimics the parts of pyserial.Serial the reader uses."""

    def __init__(self, chunks, fail_after=None):
        self.chunks = list(chunks)
        self.fail_after = fail_after
        self.is_open = True

    @property
    def in_waiting(self):
        return len(self.chunks)

    def readline(self):
        if self.fail_after is not None and self.fail_after <= 0:
            from serial import SerialException
            raise SerialException("device disconnected")
        if self.fail_after is not None:
            self.fail_after -= 1
        return self.chunks.pop(0) if self.chunks else b""  # b"" = timeout

    def reset_input_buffer(self):
        pass

    def close(self):
        self.is_open = False


class ParseTests(unittest.TestCase):
    def test_sample_record(self):
        self.assertEqual(parse_line(SAMPLE), Reading(12345, "LabRouter", "AA:BB:CC:DD:EE:FF", 6, -57))

    def test_types(self):
        r = parse_line(SAMPLE)
        self.assertIsInstance(r.esp32_millis, int)
        self.assertIsInstance(r.channel, int)
        self.assertIsInstance(r.rssi_dbm, int)

    def test_crlf_and_whitespace(self):
        self.assertEqual(parse_line(SAMPLE + "\r\n").rssi_dbm, -57)

    def test_ssid_with_comma_and_unicode(self):
        r = parse_line('DATA,1,"Home, Sweet",aa:bb:cc:dd:ee:ff,11,-80')
        self.assertEqual(r.ssid, "Home, Sweet")
        self.assertEqual(r.bssid, "AA:BB:CC:DD:EE:FF")  # normalised to upper case
        self.assertEqual(parse_line('DATA,1,"واي فاي","AA:BB:CC:DD:EE:FF",1,-70').ssid, "واي فاي")

    def test_empty_ssid_allowed(self):
        self.assertEqual(parse_line('DATA,1,"","AA:BB:CC:DD:EE:FF",1,-70').ssid, "")

    def test_ignored_lines(self):
        for line in ["", "   ", "\r\n", "ets Jun  8 2016 00:22:57", "rst:0x1 (POWERON_RESET)",
                     "Scanning...", "DATAX,1,2", "data,1,\"a\",\"AA:BB:CC:DD:EE:FF\",1,-5"]:
            with self.subTest(line=line):
                with self.assertRaises(NotARecord):
                    parse_line(line)

    def test_malformed_records(self):
        bad = [
            'DATA,12345,"LabRouter","AA:BB:CC:DD:EE:FF",6',            # missing field
            'DATA,12345,"LabRouter","AA:BB:CC:DD:EE:FF",6,-57,99',     # extra field
            'DATA,abc,"LabRouter","AA:BB:CC:DD:EE:FF",6,-57',          # bad millis
            'DATA,12345,"LabRouter","AA:BB:CC:DD:EE:FF",six,-57',      # bad channel
            'DATA,12345,"LabRouter","AA:BB:CC:DD:EE:FF",6,-5x',        # bad rssi
            'DATA,12345,"LabRouter","AA:BB:CC:DD:EE",6,-57',           # short BSSID
            'DATA,12345,"LabRouter","ZZ:BB:CC:DD:EE:FF",6,-57',        # non-hex BSSID
            'DATA,12345,"LabRouter","AA:BB:CC:DD:EE:FF",99,-57',       # channel out of range
            'DATA,12345,"LabRouter","AA:BB:CC:DD:EE:FF",6,57',         # RSSI positive
            'DATA,12345,"LabRouter","AA:BB:CC:DD:EE:FF",6,-300',       # RSSI impossible
            'DATA,-5,"LabRouter","AA:BB:CC:DD:EE:FF",6,-57',           # negative millis
            'DATA,,,,,',                                                # empty fields
        ]
        for line in bad:
            with self.subTest(line=line):
                with self.assertRaises(ParseError) as ctx:
                    parse_line(line)
                self.assertNotIsInstance(ctx.exception, NotARecord)


class ReaderTests(unittest.TestCase):
    def test_mixed_stream_never_crashes(self):
        port = FakeSerial([
            b"ets Jun  8 2016 00:22:57\r\n",
            b"\r\n",
            SAMPLE.encode() + b"\r\n",
            b'DATA,1,"x","AA:BB:CC:DD:EE:FF",6\r\n',            # malformed
            b"\xff\xfe garbage bytes\r\n",                       # undecodable
            b'DATA,13345,"LabRouter","AA:BB:CC:DD:EE:FF",6,-59\n',
        ])
        reader = SerialReader(serial_obj=port)
        got = [r for r in (reader.read_reading() for _ in range(6)) if r]
        self.assertEqual([r.rssi_dbm for r in got], [-57, -59])
        self.assertEqual((reader.stats.valid, reader.stats.malformed, reader.stats.ignored), (2, 1, 3))

    def test_timeout_returns_none(self):
        self.assertIsNone(SerialReader(serial_obj=FakeSerial([])).read_reading())

    def test_partial_line_is_buffered(self):
        port = FakeSerial([b'DATA,12345,"LabRouter","AA:BB:', b'CC:DD:EE:FF",6,-57\r\n'])
        reader = SerialReader(serial_obj=port)
        self.assertIsNone(reader.read_reading())
        self.assertEqual(reader.read_reading().rssi_dbm, -57)
        self.assertEqual(reader.stats.malformed, 0)

    def test_disconnect_raises_clear_error(self):
        reader = SerialReader("COM9", serial_obj=FakeSerial([SAMPLE.encode() + b"\n"], fail_after=1))
        self.assertIsNotNone(reader.read_reading())
        with self.assertRaises(SerialConnectionError) as ctx:
            reader.read_reading()
        self.assertIn("COM9", str(ctx.exception))

    def test_bssid_filter(self):
        line = b'DATA,1,"Other","11:22:33:44:55:66",1,-60\n'
        reader = SerialReader(serial_obj=FakeSerial([line, SAMPLE.encode() + b"\n"]),
                              target_bssid="aa:bb:cc:dd:ee:ff")
        self.assertIsNone(reader.read_reading())
        self.assertIsNotNone(reader.read_reading())
        self.assertEqual(reader.stats.filtered, 1)

    def test_read_available_is_non_blocking(self):
        port = FakeSerial([SAMPLE.encode() + b"\n", b"junk\n", SAMPLE.encode() + b"\n"])
        self.assertEqual(len(SerialReader(serial_obj=port).read_available()), 2)

    def test_bad_port_message(self):
        with self.assertRaises(SerialConnectionError) as ctx:
            SerialReader("COM99").open()
        self.assertIn("COM99", str(ctx.exception))

    def test_no_port_selected(self):
        with self.assertRaises(SerialConnectionError):
            SerialReader().open()


class LoggerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "out", "t.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def test_header_rows_and_timestamp(self):
        r = parse_line(SAMPLE)
        with CSVLogger(self.path) as lg:
            lg.log(r)
            lg.log(r)
        with open(self.path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(list(rows[0].keys()),
                         ["timestamp_utc", "esp32_millis", "ssid", "bssid", "channel", "rssi_dbm"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["rssi_dbm"], "-57")
        self.assertRegex(rows[0]["timestamp_utc"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")

    def test_excel_friendly_bom(self):
        with CSVLogger(self.path) as lg:
            lg.log(parse_line('DATA,1,"واي فاي","AA:BB:CC:DD:EE:FF",1,-70'))
        with open(self.path, "rb") as f:
            self.assertTrue(f.read().startswith(b"\xef\xbb\xbf"))

    def test_extra_columns(self):
        with CSVLogger(self.path, extra_columns=("session_label", "status")) as lg:
            lg.log(parse_line(SAMPLE), session_label="EMPTY")
        with open(self.path, newline="", encoding="utf-8-sig") as f:
            row = next(csv.DictReader(f))
        self.assertEqual((row["session_label"], row["status"]), ("EMPTY", ""))

    def test_data_flushed_before_close(self):
        lg = CSVLogger(self.path)
        lg.open()
        lg.log(parse_line(SAMPLE))
        with open(self.path, encoding="utf-8-sig") as f:   # read while still open
            self.assertEqual(len(f.read().strip().splitlines()), 2)
        lg.close()

    def test_write_failure_is_reported(self):
        lg = CSVLogger(self.path)
        lg.open()
        lg._file.close()  # simulate file becoming unwritable
        with self.assertRaises(DataLoggerError):
            lg.log(parse_line(SAMPLE))

    def test_refuses_to_overwrite(self):
        first = CSVLogger(self.path)
        first.open()
        with self.assertRaises(DataLoggerError):
            CSVLogger(self.path).open()
        first.close()

    def test_log_before_open(self):
        with self.assertRaises(DataLoggerError):
            CSVLogger(self.path).log(parse_line(SAMPLE))


class EndToEndTests(unittest.TestCase):
    def test_pipeline_with_fake_port(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "e2e.csv")
            lines = [b"boot message\r\n", SAMPLE.encode() + b"\r\n", b"DATA,bad\r\n",
                     b'DATA,13345,"LabRouter","AA:BB:CC:DD:EE:FF",6,-59\r\n']
            summary = run_logging("FAKE", label="EMPTY", out_path=path, max_records=2,
                                  reader=SerialReader(serial_obj=FakeSerial(lines)), verbose=False)
            self.assertEqual(summary["valid_records_saved"], 2)
            self.assertEqual((summary["malformed"], summary["ignored"]), (1, 1))
            self.assertEqual(summary["rssi_mean"], -58.0)

    def test_disconnect_reported_in_summary_and_data_kept(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "dc.csv")
            port = FakeSerial([SAMPLE.encode() + b"\n"], fail_after=1)
            summary = run_logging("COM9", out_path=path, duration=5,
                                  reader=SerialReader("COM9", serial_obj=port), verbose=False)
            self.assertEqual(summary["stopped_because"], "error")
            self.assertIn("COM9", summary["error"])
            self.assertEqual(summary["valid_records_saved"], 1)
            with open(path, encoding="utf-8-sig") as f:
                self.assertEqual(len(f.read().strip().splitlines()), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
