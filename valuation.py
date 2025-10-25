# valuation.py
from typing import Dict, Tuple
import pandas as pd
import numpy as np

Percentiles = Tuple[float, float, float]  # p25, p50, p75

def pctiles(s: pd.Series) -> Percentiles:
    s = s.replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty: 
        return (np.nan, np.nan, np.nan)
    return tuple(np.percentile(s, [25, 50, 75]))  # type: ignore[return-value]

def implied_price_from_multiple(
    target_row: pd.Series, multiple_name: str, driver_name: str
) -> Dict[str, float]:
    """
    For a given peer multiple (e.g., EV/EBITDA) and target driver (e.g., EBITDA),
    compute implied enterprise value, equity value, and price per share.
    Returns dict with low/base/high (p25/p50/p75 multiple).
    """
    driver = target_row[driver_name]
    shares = target_row["shares_out"]
    cash = target_row["cash"]
    debt = target_row["debt"]

    if pd.isna(driver) or pd.isna(shares) or shares == 0:
        return {"low": np.nan, "base": np.nan, "high": np.nan}

    p25, p50, p75 = target_row[f"{multiple_name}_p25"], target_row[f"{multiple_name}_p50"], target_row[f"{multiple_name}_p75"]
    out = {}
    for label, mult in [("low", p25), ("base", p50), ("high", p75)]:
        if pd.isna(mult): 
            out[label] = np.nan
            continue
        ev = mult * driver
        eq = ev - (debt or 0) + (cash or 0)
        price = eq / shares
        out[label] = float(price)
    return out
