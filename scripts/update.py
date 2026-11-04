import json, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

TICKERS = ["NVDA","AMD","TSLA","PLTR","COIN","MSTR","HOOD","SOFI","ROKU","AFRM","MARA","RIOT","UPST","SMCI","GME"]
OUT = Path(__file__).resolve().parents[1] / "site" / "data" / "report.json"

def pivots(close, threshold=0.05):
    direction=0; anchor=float(close.iloc[0]); anchor_i=0; extreme=anchor; extreme_i=0; events=[]
    for i in range(1,len(close)):
        p=float(close.iloc[i])
        if direction==0:
            if p>=anchor*(1+threshold):
                events.append(("low",anchor_i,i,anchor)); direction=1; extreme=p; extreme_i=i
            elif p<=anchor*(1-threshold):
                events.append(("high",anchor_i,i,anchor)); direction=-1; extreme=p; extreme_i=i
        elif direction==1:
            if p>extreme: extreme=p; extreme_i=i
            elif p<=extreme*(1-threshold):
                events.append(("high",extreme_i,i,extreme)); direction=-1; extreme=p; extreme_i=i
        else:
            if p<extreme: extreme=p; extreme_i=i
            elif p>=extreme*(1+threshold):
                events.append(("low",extreme_i,i,extreme)); direction=1; extreme=p; extreme_i=i
    return events

def analyze(ticker):
    df=yf.download(ticker,start="2016-01-01",auto_adjust=True,progress=False,threads=False)
    if df.empty: raise ValueError("no data")
    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    df=df[["Close","Volume"]].dropna()
    if len(df)<252: raise ValueError("insufficient history")
    c=df["Close"]; rv=np.log(c/c.shift(1)).rolling(20).std()*np.sqrt(252)
    z=(c-c.rolling(20).mean())/c.rolling(20).std().replace(0,np.nan)
    dollars=(c*df["Volume"]).rolling(20).mean()
    events=pivots(c)
    lows=[x for x in events if x[0]=="low"]
    durations=[b[1]-a[1] for a,b in zip(lows,lows[1:])]
    eligible=bool(c.iloc[-1]>=5 and rv.iloc[-1]>=0.5 and dollars.iloc[-1]>=20e6)
    signal=bool(eligible and pd.notna(z.iloc[-1]) and z.iloc[-1]<=-1.5 and len(durations)>=6)
    cond=(c>=5)&(rv>=0.5)&(dollars>=20e6)&(z<=-1.5)
    stats=[]
    for h in (1,3,5,10):
        vals=((c.shift(-h)/c-1)*100)[cond].dropna()
        stats.append({"days":h,"count":int(len(vals)),"mean_pct":round(float(vals.mean()),2) if len(vals) else None,"win_pct":round(float((vals>0).mean()*100),1) if len(vals) else None})
    return {"ticker":ticker,"close":round(float(c.iloc[-1]),2),"rv20":round(float(rv.iloc[-1])*100,1),"z20":round(float(z.iloc[-1]),2) if pd.notna(z.iloc[-1]) else None,"dollar_m":round(float(dollars.iloc[-1])/1e6,1),"cycle_days":round(float(np.median(durations)),1) if durations else None,"cycle_cv":round(float(np.std(durations,ddof=1)/np.mean(durations)),2) if len(durations)>1 and np.mean(durations)>0 else None,"cycles":len(durations),"signal":"反轉觀察" if signal else "無訊號","last_price_date":str(c.index[-1].date()),"conditional":stats,"last_confirmation":str(c.index[events[-1][2]].date()) if events else None}

def main():
    rows=[];errors={}
    for t in TICKERS:
        try:
            rows.append(analyze(t));print("OK",t)
        except Exception as e:
            errors[t]=str(e);print("ERROR",t,e)
    if not rows: raise RuntimeError("No successful downloads; existing report preserved")
    rows.sort(key=lambda r:(r["signal"]!="反轉觀察",-r["rv20"]))
    payload={"updated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"universe":"15 隻預選觀察股票，並非全美股","rows":rows,"errors":errors,"method":"收盤價確認 ZigZag 5%；RV20 年化；Z20；歷史收盤至未來收盤條件報酬（非交易回測）"}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    tmp=OUT.with_suffix(".tmp");tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");tmp.replace(OUT)
if __name__=="__main__":main()
