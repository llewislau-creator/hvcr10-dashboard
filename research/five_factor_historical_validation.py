"""Isolated five-factor historical comparison. Never writes website data."""
import json
from pathlib import Path
import sys
import yfinance as yf
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from phase1 import clean_price_history, validate_prices
from five_factor_comparison import simulate,metrics

TICKERS=["NVDA","AMD","TSLA","PLTR","COIN","MSTR","HOOD","SOFI","ROKU","AFRM","MARA","RIOT","UPST","SMCI","GME","APP","CRWD","IONQ","RKLB","HIMS"]
OUT=Path("five_factor_validation.json")
def download(ticker):
    x=yf.download(ticker,start="2016-01-01",auto_adjust=True,progress=False,threads=False)
    if isinstance(x.columns,pd.MultiIndex):x.columns=x.columns.get_level_values(0)
    if x.empty:raise ValueError("empty download")
    x,clean=clean_price_history(x)
    q=validate_prices(x,ticker)
    if q["status"]!="ok":raise ValueError("quality status "+q["status"]+": "+str(q.get("issues",[])))
    return x,clean
def main():
    spy,_=download("SPY")
    output={"status":"research_only","benchmark":"SPY","period":"2016-01-01 to run date","per_stock":{},"errors":{},"comparison":{},"limitations":["single-stock sequential trade drawdown, not portfolio NAV drawdown","unadjusted SPY relative return against net-of-cost stock trades","fixed and signal trades have different exits and potentially different future entry dates","universe selected today; survivorship and selection bias","not deployed; no live orders"]}
    for ticker in TICKERS:
        try:
            df,clean=download(ticker)
            if len(df)<330:raise ValueError("insufficient rows")
            by={}
            for h in (10,15,20):
                by[str(h)]={}
                for mode in ("legacy_fixed","fixed","signal"):
                    trades=simulate(df,spy.Close,h,mode)
                    by[str(h)][mode]={"metrics":metrics(trades),"trades":trades}
            output["per_stock"][ticker]={"rows":len(df),"quality":"ok","comparison":by}
            print("OK",ticker,flush=True)
        except Exception as e:
            output["errors"][ticker]=str(e)[:400]
            print("SKIP",ticker,str(e)[:200],flush=True)
    for h in (10,15,20):
        output["comparison"][str(h)]={}
        for mode in ("legacy_fixed","fixed","signal"):
            trades=[t for item in output["per_stock"].values() for t in item["comparison"][str(h)][mode]["trades"]]
            output["comparison"][str(h)][mode]=metrics(trades)
    output["validated_tickers"]=len(output["per_stock"])
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print("RESULT",json.dumps({"validated":output["validated_tickers"],"errors":output["errors"],"comparison":output["comparison"]},ensure_ascii=False),flush=True)
    if output["validated_tickers"]<18:raise RuntimeError("coverage <90%; results research-only and not approved")
if __name__=="__main__":main()
