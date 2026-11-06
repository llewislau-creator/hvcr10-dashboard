import json, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf
from rebound_v3 import analyze_frame
from swing_v5 import swing_research
from stage2_risk import make_plan, backtest_plans
from phase1 import validate_prices, clean_price_history, market_context, earnings_event, risk_context

TICKERS = ["NVDA","AMD","TSLA","PLTR","COIN","MSTR","HOOD","SOFI","ROKU","AFRM","MARA","RIOT","UPST","SMCI","GME","APP","CRWD","IONQ","RKLB","HIMS"]
OUT = Path(__file__).resolve().parents[1] / "site" / "data" / "report.json"

def analyze(ticker, spy_close=None):
    df=yf.download(ticker,start="2016-01-01",auto_adjust=True,progress=False,threads=False)
    if df.empty: raise ValueError("no data")
    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    try:
        df,cleaning=clean_price_history(df)
        cleaning["source_attempt"]="start=2016-01-01"
    except ValueError as first_error:
        # Re-fetch an independent five-year window; never fill recent missing bars.
        retry=yf.download(ticker,period="5y",auto_adjust=True,progress=False,threads=False)
        if isinstance(retry.columns,pd.MultiIndex):
            retry.columns=retry.columns.get_level_values(0)
        try:
            df,cleaning=clean_price_history(retry)
            cleaning["source_attempt"]="5y retry"
            cleaning["primary_error"]=str(first_error)[:400]
        except Exception as second_error:
            raise ValueError(f"原始行情不合格：{first_error}；5年重新下載仍不合格：{second_error}") from second_error
    quality=validate_prices(df,ticker)
    quality["cleaning"]=cleaning
    removed=cleaning["historical_incomplete_rows_removed"]
    if removed:
        quality["issues"].append(f"已移除{removed}個較舊不完整交易日")
        if quality["status"]=="ok":quality["status"]="warning"
    if quality["status"]=="blocked":raise ValueError("行情品質檢查不通過："+", ".join(quality["issues"]))
    result=analyze_frame(df)
    result["data_quality"]=quality
    result['swing']=swing_research(df,spy_close)
    result['stage2']={'status':'research_only','plan':make_plan(df),'backtests':{str(n):backtest_plans(df,n,spy_close) for n in (10,15,20)},'ranking_influence':False}
    try:
        calendar=yf.Ticker(ticker).calendar
        earnings=earnings_event(calendar)
    except Exception as exc:
        earnings=earnings_event(None)
        earnings['note']+='；日曆查詢失敗：'+str(exc)[:120]
    result['earnings']=earnings
    result['phase1_risk']=risk_context(quality,earnings)
    if spy_close is not None:
        aligned=spy_close.reindex(df.index).ffill()
        stock_return=float(df["Close"].iloc[-1]/df["Close"].iloc[-21]-1) if len(df)>21 else None
        spy_return=float(aligned.iloc[-1]/aligned.iloc[-21]-1) if len(df)>21 and pd.notna(aligned.iloc[-21]) and aligned.iloc[-21]>0 else None
        relative=round(100*(stock_return-spy_return),2) if stock_return is not None and spy_return is not None else None
    else:
        relative=None
    result["extra_indicators"]["相對 SPY 20日強弱"]={"value":relative,"observed":relative is not None and relative>0,"unit":"百分點；正值代表跑贏 SPY"}
    result["composite_score_12"]=round(100*(sum(result["conditions"].values())+sum(bool(x["observed"]) for x in result["extra_indicators"].values()))/12,1) if relative is not None else None
    result["composite_note"]="12項等權觀察分數（非反彈機率）；SPY資料不足時不提供12項分數"
    result["ticker"]=ticker
    return result

def require_coverage(validated,expected,minimum=.90):
    if expected<=0 or validated<0 or validated>expected:raise ValueError('Invalid coverage counts')
    if validated/expected<minimum:
        raise RuntimeError(f'Insufficient validated coverage ({validated}/{expected}); previous report preserved')
    return round(validated/expected*100,1)

def main():
    rows=[];errors={}
    try:
        spy=yf.download("SPY",start="2016-01-01",auto_adjust=True,progress=False,threads=False)
        if isinstance(spy.columns,pd.MultiIndex):spy.columns=spy.columns.get_level_values(0)
        spy_close=spy["Close"] if not spy.empty else None
    except Exception as exc:
        spy_close=None
        errors["SPY benchmark"]=str(exc)
    market_data={}
    for symbol in ('SPY','QQQ','^VIX'):
        try:
            market_data[symbol]=spy if symbol=='SPY' else yf.download(symbol,period='2y',auto_adjust=True,progress=False,threads=False)
            if isinstance(market_data[symbol].columns,pd.MultiIndex):market_data[symbol].columns=market_data[symbol].columns.get_level_values(0)
        except Exception as exc:
            market_data[symbol]=None
            errors[symbol+' market']=str(exc)
    market=market_context(market_data['SPY'],market_data['QQQ'],market_data['^VIX'])
    for t in TICKERS:
        try:
            rows.append(analyze(t,spy_close));print("OK",t)
        except Exception as e:
            errors[t]=str(e);print("ERROR",t,e)
    if not rows: raise RuntimeError("No successful downloads; existing report preserved")
    # Publish verified rows only; never reuse stale prices as current observations.
    # Fail closed when coverage is too low, rather than masking a systemic outage.
    minimum_coverage=0.90
    coverage=len(rows)/len(TICKERS)
    try:
        require_coverage(len(rows),len(TICKERS),minimum_coverage)
    except RuntimeError as exc:
        raise RuntimeError(f"{exc}. Errors: {errors}") from exc
    rows.sort(key=lambda r:(not r["swing"]["eligible"],-(r["swing"]["score"] or 0),-r["swing"]["liquidity_dollar_m"],r["ticker"]))
    payload={"updated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"universe":"20 隻預選觀察股票，並非全美股","rows":rows,"errors":errors,"method":"六項技術條件至少4項符合；5/10/20交易日內觸及+8%目標；先觸及-5%停損視為失敗；20日非重疊事件；70/30時間切分；Wilson 95%信賴區間。觸價機率不等於實際淨報酬。","model_version":"HVCR-10 rebound v3","model_revision":"v5 swing research preview","investment_horizon":"2–4星期（10/15/20交易日）","ranking_basis":"5維波段投資觀察分數，非預測機率；不以高波動率作硬性篩選","phase1":{"market":market,"earnings_window_days":30,"quality_policy":"blocked股票排除於排行榜；不使用過期數據；缺少財報日期標記unknown"},"coverage":{"expected":len(TICKERS),"validated":len(rows),"pct":round(coverage*100,1),"minimum_pct":minimum_coverage*100,"excluded":[{"ticker":t,"reason":errors[t]} for t in TICKERS if t in errors]}}
    # Keep the public dashboard payload compact; publish complete dated audit separately.
    audit={"updated_utc":payload["updated_utc"],"trades":{}}
    summary={"updated_utc":payload["updated_utc"],"groups":[]}
    for row in rows:
        for horizon in (10,15,20):
            bt=row["stage2"]["backtests"][str(horizon)]
            wf=bt["walk_forward"]
            key=f'{row["ticker"]}:{horizon}'
            trades=wf.pop("trade_audit")
            audit["trades"][key]={"folds":wf["folds"],"trades":trades}
            mb=bt["moving_block_bootstrap"]
            iid=bt["mean_net_bootstrap_ci95_pct"]
            ci=mb["ci95_pct"]
            summary["groups"].append({
                "ticker":row["ticker"],"horizon_days":horizon,"n":bt["n"],
                "iid_ci95_pct":iid,"block_ci95_pct":ci,
                "iid_positive":iid is not None and iid[0]>0,
                "block_positive":{k:(v is not None and v[0]>0) for k,v in ci.items()},
                "weakens_vs_iid":iid is not None and iid[0]>0 and any(
                    v is None or v[0]<=0 for v in ci.values()),
                "audit_key":key})
            wf["audit_file"]="trade_audit.json"
            wf["audit_key"]=key
    payload["bootstrap_summary_file"]="bootstrap_summary.json"
    payload["trade_audit_file"]="trade_audit.json"
    OUT.parent.mkdir(parents=True,exist_ok=True)
    for name,doc in (("trade_audit.json",audit),("bootstrap_summary.json",summary)):
        path=OUT.parent/name
        temp=path.with_suffix(".tmp")
        temp.write_text(json.dumps(doc,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
        temp.replace(path)
    tmp=OUT.with_suffix(".tmp");tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");tmp.replace(OUT)
if __name__=="__main__":main()
