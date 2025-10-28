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

    # Try quarterly metrics
    qm = {}
    try:
        qm = get_quarterly_metrics(ticker)
    except Exception:
        qm = {}
    
    # Revenue TTM: prefer quarterly sum, else latest annual figure
    ttm_rev = _safe(qm.get("revenue_ttm_q"))

    if pd.isna(ttm_rev):
        try:
            fin_a = getattr(tk, "financials", None)  # annual table
            if isinstance(fin_a, pd.DataFrame) and not fin_a.empty:
                for row_name in ["Total Revenue", "TotalRevenue", "Revenue"]:
                    if row_name in fin_a.index:
                        # use most recent annual (single column), NOT a 4-year sum
                        ttm_rev = float(pd.to_numeric(fin_a.loc[row_name].iloc[0], errors="coerce"))
                        break
        except Exception:
            pass

    # EBITDA proxy from info (MVP), D&A and CAPEX from quarterly if available
    ebitda_ttm = _safe(info.get("ebitda"))
    danda_ttm  = _safe(qm.get("danda_ttm_q"))
    capex_ttm  = _safe(qm.get("capex_ttm_q"))
    op_nwc     = _safe(qm.get("op_nwc"))
    op_income_ttm = _safe(qm.get("op_income_ttm"))

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
        "danda_ttm": danda_ttm,
        "capex_ttm": capex_ttm,
        "op_nwc": op_nwc,
        "op_income_ttm": op_income_ttm,
    }

def get_snapshots(tickers: List[str]) -> pd.DataFrame:
    rows = [get_basic_snapshot(t) for t in tickers]
    df = pd.DataFrame(rows)

    # Basic multiples (avoid divide-by-zero)
    with np.errstate(divide="ignore", invalid="ignore"):
        df["ev_rev"] = df["enterprise_value"] / df["revenue_ttm"]
        df["ev_ebitda"] = df["enterprise_value"] / df["ebitda_ttm"]

    return df

def _row_sum_ttm(df: pd.DataFrame, row_names):
    """Sum last 4 quarters for the first matching row name."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return np.nan
    for name in row_names:
        if name in df.index:
            # quarterly frames usually have most-recent column first
            return float(pd.to_numeric(df.loc[name].iloc[:4], errors="coerce").sum())
    return np.nan

def _grab_first(df: pd.DataFrame, row_names):
    if not isinstance(df, pd.DataFrame) or df.empty:
        return np.nan
    for name in row_names:
        if name in df.index:
            return float(pd.to_numeric(df.loc[name].iloc[0], errors="coerce"))
    return np.nan

def get_quarterly_metrics(ticker: str) -> dict:
    """
    Compute TTM D&A, TTM CAPEX from quarterly cash flow; TTM revenue from quarterly financials;
    and a simple Operating NWC and NWC% from quarterly balance sheet.
    """
    tk = yf.Ticker(ticker)

    # --- Quarterly cash flow (for D&A and CAPEX) ---
    cf_q = getattr(tk, "quarterly_cashflow", None)
    # Common row labels seen in yfinance:
    da_names = ["Depreciation", "Depreciation And Amortization", "Depreciation & amortization"]
    capex_names = ["Capital Expenditures", "CapitalExpenditures", "Capex"]
    ttm_da = _row_sum_ttm(cf_q, da_names)
    ttm_capex = _row_sum_ttm(cf_q, capex_names)
    # use absolute values for cash-flow items (Yahoo often reports negatives)
    if pd.notna(ttm_da):    
        ttm_da    = abs(ttm_da)
    if pd.notna(ttm_capex): 
        ttm_capex = abs(ttm_capex)

    # --- Quarterly income/financials (for revenue TTM) ---
    is_q = getattr(tk, "quarterly_financials", None)
    rev_names = ["Total Revenue", "TotalRevenue", "Revenue"]
    opinc_names = ["Operating Income", "OperatingIncome", "EBIT"]
    ttm_rev_q = _row_sum_ttm(is_q, rev_names)
    op_income_ttm = _row_sum_ttm(is_q, opinc_names)

    # --- Quarterly balance sheet (for Operating NWC proxy) ---
    bs_q = getattr(tk, "quarterly_balance_sheet", None)
    # We use a simple operating NWC proxy:
    # OpNWC = (Current Assets - Cash & STI) - (Current Liabilities - Short-term debt)
    # This avoids treating cash and short-term financing as "operating".
    ca_names  = ["Total Current Assets", "Current Assets", "TotalCurrentAssets"]
    cla_names = ["Total Current Liabilities", "Current Liabilities", "TotalCurrentLiabilities"]
    cash_names = ["Cash And Cash Equivalents", "CashAndCashEquivalents", "Cash"]
    sti_names  = ["Short Term Investments", "ShortTermInvestments"]
    std_names  = ["Short Long Term Debt", "Short/Current Long Term Debt", "Current Debt", "ShortTermDebt"]

    ca  = _grab_first(bs_q, ca_names)
    cla = _grab_first(bs_q, cla_names)
    cash = _grab_first(bs_q, cash_names)
    sti  = _grab_first(bs_q, sti_names)
    std  = _grab_first(bs_q, std_names)

    if np.isnan(cash): 
        cash = 0.0
    if np.isnan(sti):  
        sti  = 0.0
    if np.isnan(std):  
        std  = 0.0

    op_nwc = np.nan
    if pd.notna(ca) and pd.notna(cla):
        op_ca  = ca  - cash - sti
        op_cla = cla - std
        op_nwc = float(op_ca - op_cla)

    # Result dict
    return {
        "revenue_ttm_q": ttm_rev_q,     # TTM revenue from quarterly
        "danda_ttm_q": ttm_da,          # TTM D&A from quarterly
        "capex_ttm_q": ttm_capex,       # TTM CAPEX from quarterly
        "op_nwc": op_nwc,               # Operating NWC level (latest quarter)
        "op_income_ttm": op_income_ttm, # TTM operating income from quarterly
    }
