"""Research-only daily marked-to-market portfolios. No live execution."""
import numpy as np
import pandas as pd

def portfolio_risk(audit, prices, horizon, benchmark=None, capital=100000.0):
    """One independent horizon, cash-funded, at most 15% NAV per entry."""
    orders=[]
    for key, record in audit["trades"].items():
        ticker, period=key.rsplit(":",1)
        if int(period)!=horizon:continue
        for t in record["trades"]:
            orders.append(dict(t,ticker=ticker))
    orders.sort(key=lambda t:(t["entry_date"],t["ticker"],t["exit_date"]))
    if not orders:
        return {"horizon_days":horizon,"status":"no_trades","trades_executed":0}
    for t in orders:
        if t["ticker"] not in prices:raise ValueError("Missing prices: "+t["ticker"])
    first=min(t["entry_date"] for t in orders)
    last=max(t["exit_date"] for t in orders)
    dates=sorted(set().union(*(set(p.loc[first:last].index.strftime("%Y-%m-%d")) for p in prices.values())))
    cash=float(capital); positions={}; daily=[]; executed=[]; skipped=[]
    for day in dates:
        opening_equity=cash+sum(pos["shares"]*float(prices[ticker].loc[:day,"Close"].iloc[-1]) for ticker,pos in positions.items())
        # New orders are funded from cash on hand, without assuming intraday exit proceeds.
        for order in (o for o in orders if o["entry_date"]==day):
            ticker=order["ticker"]
            if ticker in positions:
                skipped.append({"ticker":ticker,"entry_date":day,"reason":"already_held"});continue
            if day not in prices[ticker].index.strftime("%Y-%m-%d"):
                skipped.append({"ticker":ticker,"entry_date":day,"reason":"missing_entry_bar"});continue
            entry=float(order["entry_price"])
            friction=(order["cost_bps_per_side"]+order["slippage_bps_per_side"])/10000
            shares=int(min(.15*opening_equity, cash)/(entry*(1+friction)))
            if shares<1:
                skipped.append({"ticker":ticker,"entry_date":day,"reason":"insufficient_cash"});continue
            cash-=shares*entry*(1+friction)
            positions[ticker]={"shares":shares,"trade":order}
            executed.append({"ticker":ticker,"entry_date":day,"exit_date":order["exit_date"],"shares":shares,"entry_price":entry})
        for ticker,pos in list(positions.items()):
            order=pos["trade"]
            if order["exit_date"]!=day:continue
            friction=(order["cost_bps_per_side"]+order["slippage_bps_per_side"])/10000
            cash+=pos["shares"]*float(order["exit_price"])*(1-friction)
            del positions[ticker]
        value=cash
        exposure=0.0
        for ticker,pos in positions.items():
            history=prices[ticker].loc[:day,"Close"]
            if history.empty:raise ValueError("Missing holding mark: "+ticker)
            mark=float(history.iloc[-1])
            value+=pos["shares"]*mark
            exposure+=pos["shares"]*mark
        if value<=0:raise ValueError("Nonpositive NAV")
        daily.append({"date":day,"equity":value,"exposure_pct":100*exposure/value,"positions":len(positions)})
        if cash < -1e-6:raise AssertionError("Negative cash")
    frame=pd.DataFrame(daily)
    nav=frame.equity.to_numpy()
    returns=np.diff(nav)/nav[:-1]
    peaks=np.maximum.accumulate(np.r_[capital,nav])[1:]
    dd=(nav/peaks-1)*100
    result={"horizon_days":horizon,"status":"research_only","trades_executed":len(executed),
        "trades_skipped":len(skipped),"skipped":skipped,
        "max_drawdown_pct":round(float(dd.min()),3),
        "annualized_volatility_pct":round(float(np.std(returns,ddof=1)*np.sqrt(252)*100),3) if len(returns)>1 else None,
        "mean_exposure_pct":round(float(frame.exposure_pct.mean()),3),
        "max_exposure_pct":round(float(frame.exposure_pct.max()),3),
        "max_concurrent_positions":int(frame.positions.max()),
        "daily_equity":[{"date":x["date"],"equity":round(x["equity"],2),
                         "exposure_pct":round(x["exposure_pct"],3),"positions":x["positions"]} for x in daily],
        "assumptions":"Independent horizon, fixed initial cash, integer shares, max 15% NAV per entry, no leverage; entry at modeled open, exit at modeled fill; adjusted daily close marks; no intraday equity path."}
    if result["max_exposure_pct"]>100.00001:raise AssertionError("Excess exposure")
    if benchmark is not None:
        b=benchmark.reindex(pd.to_datetime(frame.date)).ffill()
        regime=(b>b.shift(200)).to_numpy()
        result["market_regime"]={"SPY_above_200d":{},"SPY_not_above_200d":{}}
        for label,mask in (("SPY_above_200d",regime),("SPY_not_above_200d",~regime)):
            vals=returns[mask[1:]]
            result["market_regime"][label]={"days":int(len(vals)),"mean_daily_return_pct":round(float(vals.mean()*100),4) if len(vals) else None}
    return result
