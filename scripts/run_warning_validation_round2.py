"""Execute second-round AlphaLens warning evaluation for the fixed 20 tickers."""
import json
from datetime import datetime,timezone
from pathlib import Path
from run_warning_validation_v22 import SYMBOLS, prices
from warning_validation_round2 import evaluate_second_round

OUT=Path(__file__).resolve().parents[1]/"site/data/warning_validation_round2.json"

def main():
    spy=prices("SPY")["Close"]
    results={}
    errors={}
    for symbol in SYMBOLS:
        try:
            result=evaluate_second_round(prices(symbol),spy)
            if result["status"]!="preliminary_research":
                errors[symbol]=result["status"]
            else:
                results[symbol]=result
        except Exception as exc:
            errors[symbol]=str(exc)[:250]
        print(symbol,results.get(symbol,{}).get("events","error"))
    if len(results)<18:
        raise RuntimeError("Below 90% ticker coverage; refuse to publish")
    data={"generated_utc":datetime.now(timezone.utc).isoformat(),
          "status":"preliminary_research","tickers":SYMBOLS,
          "completed":len(results),"errors":errors,"results":results,
          "note":"Different event definition from round 1. Do not compare headline recall percentages directly."}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    temp=OUT.with_suffix(".tmp")
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    temp.replace(OUT)
    print("Saved",OUT)
if __name__=="__main__":
    main()
