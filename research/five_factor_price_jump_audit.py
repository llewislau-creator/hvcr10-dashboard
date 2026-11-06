"""Research-only historical price jump audit; never edits prices or live signals."""
import json
from pathlib import Path
import pandas as pd
import yfinance as yf
TICKERS=["AMD","HOOD","SOFI","ROKU","MARA","UPST","GME"]
OUT=Path("five_factor_price_jump_audit.json")
def frame(t):
 d=yf.download(t,start="2016-01-01",auto_adjust=True,progress=False,threads=False)
 if isinstance(d.columns,pd.MultiIndex):d.columns=d.columns.get_level_values(0)
 if d.empty:raise ValueError("no bars")
 return d
def audit(t):
 d=frame(t)
 jump=d.Close.pct_change(fill_method=None)
 mask=jump.abs()>.5
 events=[]
 for day in d.index[mask]:
  p=d.index.get_loc(day)
  prev=d.iloc[p-1];cur=d.iloc[p]
  events.append({"date":str(day.date()),"previous_close":float(prev.Close),"open":float(cur.Open),"high":float(cur.High),"low":float(cur.Low),"close":float(cur.Close),"volume":float(cur.Volume),"adjusted_close_jump_pct":round(float(jump.loc[day]*100),3),"classification":"unverified","requires":"independent split/corporate-action or market-event evidence"})
 return {"bars":len(d),"jump_events":events,"n_events":len(events)}
def main():
 out={"status":"audit_only","price_adjustment":"yfinance auto_adjust=True","note":"Do not waive warnings without independent event verification","stocks":{},"errors":{}}
 for t in TICKERS:
  try:
   out["stocks"][t]=audit(t)
   print(t,json.dumps(out["stocks"][t]["jump_events"],ensure_ascii=False),flush=True)
  except Exception as e:out["errors"][t]=str(e)
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 if out["errors"]:raise RuntimeError(str(out["errors"]))
if __name__=="__main__":main()
