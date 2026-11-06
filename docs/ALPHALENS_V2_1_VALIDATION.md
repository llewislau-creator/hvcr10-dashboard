# AlphaLens v2.1 — Research integrity and release gates

## Scope and status
This is a research-only system. No historical backtest or portfolio metric is represented as live execution, independently audited performance, or a calibrated probability. Code changes are committed; live CI, deployment, and independent data-provider reconciliation are not yet verified.

## Data lineage
- `scripts/update.py` generates `site/data/report.json`, `trade_audit.json`, `bootstrap_summary.json`, `price_diagnostics.json`, and `portfolio_risk.json`.
- `tests/test_report_artifacts.py` checks common generation timestamps, ticker/horizon audit keys, trade counts, walk-forward date ordering, and bootstrap metadata.
- A report row references the audit by `ticker:horizon`; generated reports should never be treated as independently verified market data.
- Coverage, excluded securities, and reasons for exclusion must remain visible.

## Reproducible backtest
- Each ticker/horizon trade record includes signal, entry and exit dates, modeled prices, modeled per-side cost/slippage, and fold.
- Assert signal date < entry date <= exit date, fold containment, non-overlapping per-ticker trades, and reported mean net return versus audit trade ledger.
- Reproducibility tests compare repeated runs with identical inputs; this does not establish out-of-sample predictive power.
- Still required: independent price vendor reconciliation, corporate-action audit, benchmark and simple-rule strategy comparison, and live forward paper-trading.

## Reconciled portfolio risk
- Cash-funded, independent 10/15/20-day horizons; integer shares, maximum 15% NAV per new position, no leverage.
- Existing positions are valued at the last available **previous** close when computing entry sizing; current-day closes are not used for pre-open sizing.
- Invalid/non-finite entry, exit, and holding marks fail closed.
- Per-day `NAV = cash + holdings_value`, `exposure = holdings_value / NAV`; each sell/buy creates a cash-flow ledger event.
- Maximum drawdown is computed from daily close NAV with initial capital as the initial peak. This is **not** intraday drawdown.
- `tests/test_portfolio_risk.py` checks deterministic replay, ledger reconciliation, price validation.
- `tests/test_report_artifacts.py` recomputes NAV, cash, exposure, and max drawdown from generated data.

## Release acceptance
1. Run `python tests/test_workspace_ui.py` and all offline tests in `.github/workflows/daily.yml`.
2. Regenerate daily artifacts, then run `python tests/test_report_artifacts.py`.
3. Independently verify a sample of entry/exit prices against the licensed source and verify SPY/QQQ benchmark treatment.
4. Check Cloudflare production deployment, all six pages, ticker navigation, portfolio horizons, browser console, and mobile viewport.
5. Only after steps 1–4 pass may the release be called **production accepted**.

## Known limitations
- Price and execution assumptions may differ from real fills.
- Historical tests can be overfit and are not proof of future performance.
- Daily close NAV omits intraday excursions.
- The current 20-stock research universe is not a broad market scanner.
- Risk metrics should remain labeled **pending independent verification** until release acceptance is complete.
