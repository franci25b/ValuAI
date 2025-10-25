# data_fetch.py
from typing import Dict, Any, List
import pandas as pd
import numpy as np
import yfinance as yf

def _safe(v, default=np.nan):
    return default if v in (None, "", "None") else v

def _notna(x) -> bool:
    return pd.notna(x) and x is not None

def get_basic_snapshot(ticker: str) -> Dict[str, Any]:
    tk = yf.Ticker(ticker)

    # --- info dict (robust to missing fields)
    try:
        info = tk.get_info() or {}
    except Exception:
        info = {}

    shares = _safe(info.get("sharesOutstanding"))
    price  = _safe(info.get("currentPrice"))
    mcap   = _safe(info.get("marketCap"))
    cash   = _safe(info.get("totalCash"))
    debt   = _safe(info.get("totalDebt"))

    # --- financials (avoid boolean context on DataFrame)
    try:
        fin = tk.get_financials()
    except Exception:
        fin = None

    if fin is None or (isinstance(fin, pd.DataFrame) and fin.empty):
        fin = pd.DataFrame()

    # Try to estimate TTM revenue by summing last four quarters if available
    ttm_rev = np.nan
    try:
        # yfinance sometimes labels income statement rows; handle a few common ones
        row_candidates = ["Total Revenue", "TotalRevenue", "Revenue"]
        for row_name in row_candidates:
            if row_name in fin.index:
                ttm_rev = float(fin.loc[row_name].head(4).sum())
                break
    except Exception:
        pass

    # EBITDA (yfinance often exposes in info; not guaranteed TTM but OK for MVP)
    ebitda_ttm = _safe(info.get("ebitda"))

    # Enterprise value
    ev = np.nan
    if _notna(mcap) or _notna(debt) or _notna(cash):
        ev = (mcap if _notna(mcap) else 0) + (debt if _notna(debt) else 0) - (cash if _notna(cash) else 0)

    return {
        "ticker": ticker.upper(),
        "price": price,
        "shares_out": shares,
        "market_cap": mcap,
        "cash": cash,
        "debt": debt,
        "enterprise_value": ev,
        "revenue_ttm": ttm_rev,
        "ebitda_ttm": ebitda_ttm,
    }

def get_snapshots(tickers: List[str]) -> pd.DataFrame:
    rows = [get_basic_snapshot(t) for t in tickers]
    df = pd.DataFrame(rows)

    # Basic multiples (avoid divide-by-zero)
    with np.errstate(divide="ignore", invalid="ignore"):
        df["ev_rev"] = df["enterprise_value"] / df["revenue_ttm"]
        df["ev_ebitda"] = df["enterprise_value"] / df["ebitda_ttm"]

    return df

