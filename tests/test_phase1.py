import sys,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import pandas as pd,numpy as np
from phase1 import validate_prices,clean_price_history,market_context,earnings_event,risk_context
idx=pd.bdate_range("2025-01-01",periods=300)
close=np.linspace(100,130,300)
d=pd.DataFrame({"Open":close,"High":close+1,"Low":close-1,"Close":close,"Volume":np.full(300,1000000)},index=idx)
q=validate_prices(d,"TEST",today=idx[-1].date())
assert q["status"]=="ok"
bad=d.copy();bad.iloc[-1,bad.columns.get_loc("High")]=1
assert validate_prices(bad,today=idx[-1].date())["status"]=="blocked"
assert validate_prices(d,today=idx[-1].date()+dt.timedelta(days=9))["status"]=="blocked"
m=market_context(d,d,d)
assert m["regime"]=="趨勢偏強"
assert earnings_event(None,today=dt.date(2026,11,4))["status"]=="unknown"
e=earnings_event({"Earnings Date":[dt.date(2026,11,12)]},today=dt.date(2026,11,4))
assert e["days_until"]==8
assert risk_context(q,e)=="持有期內可能有財報"
print("phase1 tests passed")

# Missing historical bar is removed and audited; recent missing bar is blocked.
idx2=pd.bdate_range("2024-01-01",periods=400)
price=np.linspace(100,140,400)
hist=pd.DataFrame({"Open":price,"High":price+1,"Low":price-1,"Close":price,"Volume":np.full(400,1000000)},index=idx2)
hist.iloc[50,hist.columns.get_loc("Volume")]=np.nan
clean,audit=clean_price_history(hist)
assert len(clean)==399 and audit["historical_incomplete_rows_removed"]==1
assert validate_prices(clean,today=idx2[-1].date())["status"]=="ok"
recent=hist.copy();recent.iloc[-1,recent.columns.get_loc("Close")]=np.nan
try:clean_price_history(recent)
except ValueError as exc:assert "最近5個交易日" in str(exc)
else:raise AssertionError("Recent missing price must be rejected")
print("historical cleanup tests passed")
