import json, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf
from rebound_v3 import analyze_frame

TICKERS = ["NVDA","AMD","TSLA","PLTR","COIN","MSTR","HOOD","SOFI","ROKU","AFRM","MARA","RIOT","UPST","SMCI","GME"]
OUT = Path(__file__).resolve().parents[1] / "site" / "data" / "report.json"

def analyze(ticker):
    df=yf.download(ticker,start="2016-01-01",auto_adjust=True,progress=False,threads=False)
    if df.empty: raise ValueError("no data")
    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    result=analyze_frame(df)
    result["ticker"]=ticker
    return result

def main():
    rows=[];errors={}
    for t in TICKERS:
        try:
            rows.append(analyze(t));print("OK",t)
        except Exception as e:
            errors[t]=str(e);print("ERROR",t,e)
    if not rows: raise RuntimeError("No successful downloads; existing report preserved")
    rows.sort(key=lambda r:(r["signal"]!="反彈觀察", -(r["probability"] if r["probability"] is not None else -1),-r["matched"]))
    payload={"updated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"universe":"15 隻預選觀察股票，並非全美股","rows":rows,"errors":errors,"method":"六項技術條件至少4項符合；5/10/20交易日內觸及+8%目標；先觸及-5%停損視為失敗；20日非重疊事件；70/30時間切分；Wilson 95%信賴區間。觸價機率不等於實際淨報酬。","model_version":"HVCR-10 rebound v3"}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    tmp=OUT.with_suffix(".tmp");tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");tmp.replace(OUT)
if __name__=="__main__":main()
