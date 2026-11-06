"""Read-only anomaly details for rejected OHLCV price data."""
import numpy as np
import pandas as pd

def diagnose_price_anomalies(df, limit=100):
    d=df[["Open","High","Low","Close","Volume"]].copy()
    invalid=(d.High<d[["Open","Close","Low"]].max(axis=1)) | (d.Low>d[["Open","Close","High"]].min(axis=1))
    returns=d.Close.pct_change(fill_method=None)
    jumps=returns.abs()>.5
    def rows(mask):
        result=[]
        for date,row in d.loc[mask].head(limit).iterrows():
            item={"date":str(pd.Timestamp(date).date())}
            item.update({k:float(row[k]) if np.isfinite(row[k]) else None for k in d.columns})
            v=returns.loc[date]
            item["close_return_pct"]=round(float(v)*100,3) if np.isfinite(v) else None
            result.append(item)
        return result
    return {"ohlc_invalid_count":int(invalid.sum()),"large_jump_count":int(jumps.sum()),
            "ohlc_invalid":rows(invalid),"large_jumps":rows(jumps),
            "truncated":bool(invalid.sum()>limit or jumps.sum()>limit),
            "note":"Diagnostic only; no automatic price adjustment or override."}
