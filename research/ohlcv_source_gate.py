"""Read-only local OHLCV validation gate for research data.

This tool never downloads, rewrites, or publishes vendor data; no trading signals.
A passing structural gate is NOT proof of data licensing or corporate-action accuracy.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path

REQUIRED = ("Date", "Open", "High", "Low", "Close", "Volume")


def _as_date(value: str) -> date:
    return date.fromisoformat(value.strip()[:10])


def audit_csv(path: Path, *, source: str, license_note: str,
              adjustment: str, expected_ticker: str,
              as_of: date | None = None, jump_threshold: float = 0.50,
              max_staleness_days: int = 7) -> dict:
    """Validate one ticker's CSV; return JSON-serializable research findings.

    Warnings must be reviewed manually; the gate does not infer an adjustment.
    """
    as_of = as_of or datetime.now(timezone.utc).date()
    errors: list[dict] = []
    warnings: list[dict] = []
    count = 0
    first_date: date | None = None
    last_date: date | None = None
    prior_date: date | None = None
    prior_close: float | None = None
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or any(name not in reader.fieldnames for name in REQUIRED):
            return {"status": "BLOCKED", "ticker": expected_ticker,
                    "source": source, "license_note": license_note,
                    "adjustment": adjustment, "rows": 0,
                    "errors": [{"reason": "missing_required_columns", "required": list(REQUIRED)}],
                    "warnings": [], "note": "No data rewritten; no signals generated."}
        for line, record in enumerate(reader, start=2):
            count += 1
            try:
                dt = _as_date(record["Date"] or "")
                prices = [float(record[k] or "") for k in ("Open", "High", "Low", "Close")]
                vol = float(record["Volume"] or "")
                if any(not math.isfinite(v) for v in (*prices, vol)):
                    raise ValueError("non_finite_ohlcv")
            except (ValueError, TypeError, OverflowError) as exc:
                errors.append({"line": line, "reason": "unparseable_ohlcv_or_date", "details": str(exc)})
                continue
            op, high, low, close = prices
            if min(prices) <= 0 or vol < 0:
                errors.append({"line": line, "date": str(dt), "reason": "nonpositive_price_or_negative_volume"})
            if high < max(op, low, close) - 1e-9 or low > min(op, high, close) + 1e-9:
                errors.append({"line": line, "date": str(dt), "reason": "invalid_ohlc"})
            if dt > as_of:
                errors.append({"line": line, "date": str(dt), "reason": "future_date"})
            if dt.weekday() >= 5:
                warnings.append({"line": line, "date": str(dt), "reason": "weekend_bar_verify_calendar"})
            if first_date is None:
                first_date = dt
            if prior_date is not None:
                if dt <= prior_date:
                    errors.append({"line": line, "date": str(dt), "reason": "duplicate_or_unsorted_date"})
                elif (dt - prior_date).days > 7:
                    warnings.append({"line": line, "date": str(dt), "reason": "gap_over_7_calendar_days", "previous_date": str(prior_date)})
                if prior_close is not None and prior_close > 0 and abs(close / prior_close - 1) > jump_threshold:
                    warnings.append({"line": line, "date": str(dt), "reason": "large_close_change_unverified",
                                     "previous_close": prior_close, "close": close,
                                     "close_return_pct": round((close / prior_close - 1) * 100, 3)})
            prior_date, prior_close = dt, close
            last_date = dt
    if not count:
        errors.append({"reason": "no_rows"})
    if last_date is not None and (as_of - last_date).days > max_staleness_days:
        warnings.append({"reason": "stale_history", "last_date": str(last_date), "as_of": str(as_of)})
    if not source.strip() or not license_note.strip() or not adjustment.strip():
        errors.append({"reason": "missing_provenance_or_adjustment_disclosure"})
    # License text is a human declaration, NOT an automated license grant.
    status = "BLOCKED" if errors else "REVIEW" if warnings else "STRUCTURE_PASS"
    return {"status": status, "ticker": expected_ticker, "source": source,
            "license_note": license_note, "adjustment": adjustment,
            "as_of": str(as_of), "rows": count,
            "first_date": str(first_date) if first_date else None,
            "last_date": str(last_date) if last_date else None,
            "errors": errors, "warnings": warnings,
            "note": "Structure only: not a license, calendar, split, or vendor-provenance certification. No prices changed or signals generated."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--source", required=True, help="Vendor/provider identifier")
    parser.add_argument("--license-note", required=True, help="Documented permission or pending verification")
    parser.add_argument("--adjustment", required=True, help="e.g. raw, split-adjusted, unknown")
    parser.add_argument("--as-of", type=date.fromisoformat)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit_csv(args.csv_file, source=args.source, license_note=args.license_note,
                       adjustment=args.adjustment, expected_ticker=args.ticker, as_of=args.as_of)
    report = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
    else:
        print(report)
    return 1 if result["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
