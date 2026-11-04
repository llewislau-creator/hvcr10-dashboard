import json, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf
from hvcr_model import analyze_frame

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
    rows.sort(key=lambda r:(r["signal"]!="反轉觀察",-r["rv20"]))
    payload={"updated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"universe":"15 隻預選觀察股票，並非全美股","rows":rows,"errors":errors,"method":"ATR14 動態 ZigZag（max(5%,1.5×ATR/價格)），僅使用確認日；週期穩定分數≥75；Z20≤-1.5；下一交易日開盤入場；10日時間出場或1.5 ATR 停損；每邊15bps假設成本。研究回測，非已驗證實盤策略。","model_version":"HVCR-10 research v2"}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    tmp=OUT.with_suffix(".tmp");tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");tmp.replace(OUT)
if __name__=="__main__":main()
