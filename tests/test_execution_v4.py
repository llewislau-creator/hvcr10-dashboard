"""Deterministic tests of execution assumptions; no market data download."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from execution_v4 import simulate_ohlc_trade,summarize

def run(o,h,l,c,**kw):
    return simulate_ohlc_trade(o,h,l,c,0,**kw)

a=run([100,100],[101,109],[99,99],[100,108])
assert a["reason"]=="target" and a["net_pct"]<8
b=run([100,100],[101,109],[99,94],[100,108])
assert b["reason"]=="ambiguous_stop" and b["net_pct"]<0
c=run([100,93],[101,94],[99,91],[100,92])
assert c["reason"]=="gap_stop" and c["exit"]==93
d=run([100,100],[101,102],[99,98],[100,101])
assert d["reason"]=="time_exit" and d["net_pct"]<1
s=summarize([a,b,c,d])
assert s["n"]==4 and s["max_drawdown_pct"]>=0
assert summarize([])["n"]==0
print("v4 execution tests passed")
