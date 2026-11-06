import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import pandas as pd
from portfolio_risk import portfolio_risk
dates=pd.bdate_range("2024-01-01",periods=260)
prices={k:pd.DataFrame({"Close":[100+i*.1 for i in range(260)]},index=dates) for k in ("AAA","BBB")}
def trade(start,end):
    return {"entry_date":str(dates[start].date()),"exit_date":str(dates[end].date()),"entry_price":100+start*.1,"exit_price":100+end*.1,"cost_bps_per_side":15,"slippage_bps_per_side":10}
audit={"trades":{"AAA:10":{"trades":[trade(205,245)]},"BBB:10":{"trades":[trade(205,245)]},"AAA:15":{"trades":[trade(210,225)]}}}
p=portfolio_risk(audit,prices,10)
assert p["trades_executed"]==2
assert p["max_concurrent_positions"]==2
assert p["max_exposure_pct"]<=100
assert p["stock_correlation"]["pair_count"]==1
assert portfolio_risk(audit,prices,15)["trades_executed"]==1
assert len(p["fills"])==4
assert sum(f["cash_flow"] for f in p["fills"] if f["side"]=="buy")<0
assert sum(f["cash_flow"] for f in p["fills"] if f["side"]=="sell")>0
for d in p["daily_equity"]:
    assert abs(d["equity"]-d["cash"]-d["holdings_value"])<=0.02
    assert d["cash"]>=-0.01
    assert 0<=d["exposure_pct"]<=100.00001
assert all(d["positions"]<=2 for d in p["daily_equity"])
print("portfolio risk tests passed")

# Reproducibility: identical inputs must yield identical research artifacts.
assert portfolio_risk(audit,prices,10)==p
# Every fill is traceable and cash movements reconcile to the final NAV.
assert all(f["shares"]>0 and f["price"]>0 for f in p["fills"])
assert abs(100000+sum(f["cash_flow"] for f in p["fills"])-p["daily_equity"][-1]["cash"])<0.02
assert p["daily_equity"][-1]["positions"]==0
# Invalid audit prices must fail closed rather than generate misleading risk figures.
bad_trade=trade(205,245)
bad_trade["entry_price"]=float("nan")
try:
    portfolio_risk({"trades":{"AAA:10":{"trades":[bad_trade]}}},prices,10)
    raise AssertionError("NaN entry was accepted")
except ValueError:
    pass
bad_exit=trade(205,245)
bad_exit["exit_price"]=-1
try:
    portfolio_risk({"trades":{"AAA:10":{"trades":[bad_exit]}}},prices,10)
    raise AssertionError("Negative exit was accepted")
except ValueError:
    pass
print("v2.1 accounting and deterministic replay checks passed")
