"""Run historical warning evaluation for the existing 20-symbol universe."""
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import yfinance as yf
from warning_validation_v22 import evaluate_warning_history

SYMBOLS = "NVDA AMD TSLA PLTR COIN MSTR HOOD SOFI ROKU AFRM MARA RIOT UPST SMCI GME APP CRWD IONQ RKLB HIMS".split()
OUTPUT = Path(__file__).resolve().parents[1] / "site/data/warning_validation_v22.json"

def prices(symbol):
    data = yf.download(symbol, start="2016-01-01", auto_adjust=True, progress=False, threads=False)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    if data.empty:
        raise ValueError("empty price history")
    return data

def main():
    spy = prices("SPY")["Close"]
    results, errors = {}, {}
    for symbol in SYMBOLS:
        try:
            results[symbol] = evaluate_warning_history(prices(symbol), spy)
        except Exception as exc:
            errors[symbol] = str(exc)[:250]
    if len(results) < 18:
        raise RuntimeError("Evaluation coverage below 90%; report not published")
    output = {
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "preliminary_research",
        "symbols": SYMBOLS,
        "results": results,
        "errors": errors,
        "limitations": "Overlapping forward windows and correlated stocks; not independently validated."
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Evaluated", len(results), "stocks; errors", len(errors))

if __name__ == "__main__":
    main()
