"""Offline diagnostics regression tests."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import pandas as pd
from data_diagnostics import diagnose_price_anomalies
d=pd.DataFrame({"Open":[10.,10.,10.],"High":[11.,9.,20.],"Low":[9.,9.,9.],"Close":[10.,10.,20.],"Volume":[100.,100.,100.]},index=pd.bdate_range("2024-01-01",periods=3))
a=diagnose_price_anomalies(d)
assert a["ohlc_invalid_count"]==1
assert a["large_jump_count"]==1
assert a["ohlc_invalid"][0]["date"]==str(d.index[1].date())
assert a["large_jumps"][0]["date"]==str(d.index[2].date())
assert a["large_jumps"][0]["close_return_pct"]==100
assert d.High.iloc[1]==9
print("price diagnostic tests passed")
