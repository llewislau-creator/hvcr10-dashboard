# Independent OHLCV validation gate (no TradingView)

This is a **read-only research tool**, not a new price feed, strategy, or investment signal. It has **no runtime connection** to the website or scheduled update pipeline. The production five-factor engine and weights remain unchanged.

## Usage

Supply one locally obtained CSV per symbol with headers `Date,Open,High,Low,Close,Volume` (ascending ISO dates). Do not commit proprietary data or API keys.

```bash
python research/ohlcv_source_gate.py local_prices.csv \
  --ticker TSLA \
  --source "provider-name" \
  --license-note "rights for this use still need independent verification" \
  --adjustment "unknown" \
  --as-of 2026-11-24 \
  --output /tmp/tsla-ohlcv-audit.json
python -m unittest discover -s tests -p "test_ohlcv_source_gate.py" -v
```

Three possible statuses:

- `BLOCKED`: structural errors, invalid dates or candles, missing/invalid fields, or empty provenance declarations.
- `REVIEW`: major price changes, calendar-date gaps, weekend bars, or stale data requiring human verification.
- `STRUCTURE_PASS`: only the implemented basic structural checks passed, **not** proof of completeness, licensed use, corporate-action correctness, or trading readiness.

## Mandatory verification outside this script

1. **Data rights:** Provider license and account tier must permit the exact retrieval frequency, private storage, website display and any derived metrics. Recording a `--license-note` does not establish legal permission.
2. **Instrument identity:** Validate exchange, share class, delistings and ticker changes against independent authoritative records.
3. **Market calendar:** Compare against a verified exchange calendar, including holidays and suspensions; seven-day gap warnings are only a rough indicator.
4. **Corporate actions:** Independently validate splits, dividends and adjusted OHLCV using a trusted source. Large changes are never silently rewritten.
5. **Freshness:** Confirm exchange-local trading date, timezone, final versus provisional bars, and provider publication latency.
6. **Backtest integrity:** Only use validated historical vintages, realistic next-bar execution and costs, out-of-sample evaluation, and SPY benchmarks.

## Scope and safeguards

- The tool only reads local CSV and emits JSON to stdout or a requested path.
- The optional JSON report includes no API key.
- It does not fetch Yahoo Finance, FMP, or TradingView data.
- It does not change `scripts/update.py`, `scripts/hvcr_model.py`, scoring, stock selection, trade signals, deployments, or workflow schedules.
- Production integration must be separately reviewed after actual source-license and data-quality evidence is available.

For current market-data source research: the free FMP tier has published request limits and tier-specific endpoint access; `yfinance` expressly directs users to review Yahoo's terms and states its API use is intended for personal use. Neither is, on its own, blanket permission to distribute price data on a website.
