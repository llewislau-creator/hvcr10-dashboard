import sys,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import pandas as pd,numpy as np
from phase1 import validate_prices,market_context,earnings_event,risk_context
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
