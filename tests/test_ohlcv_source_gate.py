"""Offline validation; no external market data downloaded."""
import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "research" / "ohlcv_source_gate.py"
spec = importlib.util.spec_from_file_location("ohlcv_source_gate", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OhlcvSourceGateTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "sample.csv"

    def audit(self, content):
        self.path.write_text(content, encoding="utf-8")
        return module.audit_csv(self.path, source="local-test", license_note="testing only",
                                adjustment="raw", expected_ticker="TEST",
                                as_of=date(2026, 11, 24))

    def test_valid_series(self):
        x = self.audit("Date,Open,High,Low,Close,Volume\n2026-11-19,10,12,9,11,100\n2026-11-20,11,12,10,11.5,110\n")
        self.assertEqual(x["status"], "STRUCTURE_PASS")
        self.assertEqual(x["rows"], 2)

    def test_invalid_ohlc_blocks(self):
        x = self.audit("Date,Open,High,Low,Close,Volume\n2026-11-20,11,10,9,11.5,110\n")
        self.assertEqual(x["status"], "BLOCKED")

    def test_duplicate_blocks(self):
        x = self.audit("Date,Open,High,Low,Close,Volume\n2026-11-19,10,10,9,10,100\n2026-11-19,10,10,9,10,100\n")
        self.assertIn("duplicate_or_unsorted_date", [e["reason"] for e in x["errors"]])

    def test_large_move_review_not_automatic_rewrite(self):
        x = self.audit("Date,Open,High,Low,Close,Volume\n2026-11-19,10,10,9,10,100\n2026-11-20,21,22,20,21,100\n")
        self.assertEqual(x["status"], "REVIEW")
        self.assertEqual(x["warnings"][0]["reason"], "large_close_change_unverified")

    def test_missing_provenance_blocks(self):
        self.path.write_text("Date,Open,High,Low,Close,Volume\n2026-11-20,10,11,9,10,100\n", encoding="utf-8")
        x = module.audit_csv(self.path, source="", license_note="", adjustment="",
                             expected_ticker="TEST", as_of=date(2026, 11, 24))
        self.assertEqual(x["status"], "BLOCKED")

    def test_stale_is_review(self):
        x = self.audit("Date,Open,High,Low,Close,Volume\n2026-09-01,10,11,9,10,100\n")
        self.assertEqual(x["status"], "REVIEW")

    def test_weekend_warning(self):
        x = self.audit("Date,Open,High,Low,Close,Volume\n2026-11-21,10,11,9,10,100\n")
        self.assertEqual(x["status"], "REVIEW")

    def test_missing_column_blocks(self):
        x = self.audit("Date,Open,High,Low,Close\n2026-11-20,10,11,9,10\n")
        self.assertEqual(x["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
