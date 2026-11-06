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
print("portfolio risk tests passed")
