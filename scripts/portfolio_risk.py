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
    # Only trading sessions from assets that actually participate in this horizon.
    traded_tickers={o["ticker"] for o in orders}
    dates=sorted(set().union(*(set(prices[t].loc[first:last].index.strftime("%Y-%m-%d")) for t in traded_tickers)))
    if not dates:raise ValueError("No price sessions in audit interval")
    cash=float(capital); positions={}; daily=[]; executed=[]; skipped=[]; fills=[]
    for day in dates:
        opening_equity=cash+sum(pos["shares"]*float(prices[ticker].loc[prices[ticker].index<pd.Timestamp(day),"Close"].iloc[-1]) for ticker,pos in positions.items())
        # New orders are funded from cash on hand, without assuming intraday exit proceeds.
        for order in (o for o in orders if o["entry_date"]==day):
            ticker=order["ticker"]
            if ticker in positions:
                skipped.append({"ticker":ticker,"entry_date":day,"reason":"already_held"});continue
            if day not in prices[ticker].index.strftime("%Y-%m-%d"):
                skipped.append({"ticker":ticker,"entry_date":day,"reason":"missing_entry_bar"});continue
            entry=float(order["entry_price"])
            if not np.isfinite(entry) or entry<=0:raise ValueError("Invalid entry price: "+ticker)
            friction=(order["cost_bps_per_side"]+order["slippage_bps_per_side"])/10000
            shares=int(min(.15*opening_equity, cash)/(entry*(1+friction)))
            if shares<1:
                skipped.append({"ticker":ticker,"entry_date":day,"reason":"insufficient_cash"});continue
            cash-=shares*entry*(1+friction)
            fills.append({"date":day,"ticker":ticker,"side":"buy","shares":shares,"price":entry,"cash_flow":round(-shares*entry*(1+friction),6)})
            positions[ticker]={"shares":shares,"trade":order}
            executed.append({"ticker":ticker,"entry_date":day,"exit_date":order["exit_date"],"shares":shares,"entry_price":entry})
        for ticker,pos in list(positions.items()):
            order=pos["trade"]
            if order["exit_date"]!=day:continue
            friction=(order["cost_bps_per_side"]+order["slippage_bps_per_side"])/10000
            exit_price=float(order["exit_price"])
            if not np.isfinite(exit_price) or exit_price<=0:raise ValueError("Invalid exit price: "+ticker)
            proceeds=pos["shares"]*exit_price*(1-friction)
            cash+=proceeds
            fills.append({"date":day,"ticker":ticker,"side":"sell","shares":pos["shares"],"price":float(order["exit_price"]),"cash_flow":round(proceeds,6)})
            del positions[ticker]
        value=cash
        exposure=0.0
        for ticker,pos in positions.items():
            history=prices[ticker].loc[:day,"Close"].dropna()
            if history.empty:raise ValueError("Missing holding mark: "+ticker)
            mark=float(history.iloc[-1])
            if not np.isfinite(mark) or mark<=0:raise ValueError("Invalid holding mark: "+ticker)
            value+=pos["shares"]*mark
            exposure+=pos["shares"]*mark
        if value<=0:raise ValueError("Nonpositive NAV")
        daily.append({"date":day,"equity":value,"exposure_pct":100*exposure/value,"positions":len(positions),"cash":cash,"holdings_value":exposure})
        if cash < -1e-6:raise AssertionError("Negative cash")
        if abs(value-cash-exposure)>1e-6:raise AssertionError("NAV reconciliation failed")
    if positions:raise ValueError("Open positions remain after last audit exit")
    frame=pd.DataFrame(daily)
    nav=frame.equity.to_numpy()
    returns=np.diff(nav)/nav[:-1]
    peaks=np.maximum.accumulate(np.r_[capital,nav])[1:]
    dd=(nav/peaks-1)*100
    result={"horizon_days":horizon,"status":"research_only","trades_executed":len(executed),
        "trades_skipped":len(skipped),"skipped":skipped,"fills":fills,
        "max_drawdown_pct":round(float(dd.min()),3),
        "annualized_volatility_pct":round(float(np.std(returns,ddof=1)*np.sqrt(252)*100),3) if len(returns)>1 else None,
        "mean_exposure_pct":round(float(frame.exposure_pct.mean()),3),
        "max_exposure_pct":round(float(frame.exposure_pct.max()),3),
        "max_concurrent_positions":int(frame.positions.max()),
        "daily_equity":[{"date":x["date"],"equity":round(x["equity"],2),
                         "exposure_pct":round(x["exposure_pct"],3),"positions":x["positions"],"cash":round(x["cash"],2),"holdings_value":round(x["holdings_value"],2)} for x in daily],
        "assumptions":"Independent horizon, fixed initial cash, integer shares, max 15% NAV per entry, no leverage; entry at modeled open, exit at modeled fill; adjusted daily close marks; no intraday equity path."}
    if result["max_exposure_pct"]>100.00001:raise AssertionError("Excess exposure")
    close_panel=pd.concat({ticker:price["Close"] for ticker,price in prices.items()},axis=1).sort_index()
    stock_returns=close_panel.pct_change(fill_method=None).loc[first:last]
    corr=stock_returns.corr(min_periods=30)
    pairs=[float(corr.loc[a,b]) for i,a in enumerate(corr.columns) for b in corr.columns[i+1:] if np.isfinite(corr.loc[a,b])]
    result["stock_correlation"]={"pair_count":len(pairs),"mean_pairwise_daily_return_correlation":round(float(np.mean(pairs)),4) if pairs else None,"max_pairwise_daily_return_correlation":round(float(np.max(pairs)),4) if pairs else None,"method":"Pairwise overlapping adjusted-close daily returns, minimum 30 observations; descriptive, not portfolio P&L correlation."}
    if benchmark is not None:
        spy=benchmark.sort_index().ffill()
        trend=spy>spy.shift(200)
        known=spy.shift(200).notna()
        regime=trend.reindex(pd.to_datetime(frame.date)).ffill().fillna(False).to_numpy()
        valid=known.reindex(pd.to_datetime(frame.date)).ffill().fillna(False).to_numpy()
        result["market_regime"]={"SPY_above_200d":{},"SPY_not_above_200d":{}}
        for label,mask in (("SPY_above_200d",regime & valid),("SPY_not_above_200d",~regime & valid)):
            vals=returns[mask[1:]]
            result["market_regime"][label]={"days":int(len(vals)),"mean_daily_return_pct":round(float(vals.mean()*100),4) if len(vals) else None}
    return result
