# dcf.py
from dataclasses import dataclass
from typing import Dict
import numpy as np
import pandas as pd

@dataclass
class DCFInputs:
    # Level & operating structure
    revenue_ttm: float            # starting revenue level
    ebit_margin: float            # EBIT as % of revenue (0.00–0.50 commonly)
    tax_rate: float               # effective cash tax rate (e.g., 0.22)
    # Cash-flow structure
    capex_pct: float              # CAPEX as % of revenue (e.g., 0.06)
    d_and_a_pct: float            # D&A as % of revenue (e.g., 0.05)
    nwc_pct: float                # Operating NWC as % of revenue (e.g., 0.10)
    # Discounting & horizon
    wacc: float                   # discount rate (e.g., 0.09)
    years: int = 5                # explicit forecast years
    # Scenario params
    growth_low: float = 0.03      # per-year revenue growth in forecast (pessimistic)
    growth_base: float = 0.06     # base
    growth_high: float = 0.09     # optimistic
    g_low: float = 0.01           # terminal growth (low)
    g_base: float = 0.02          # terminal growth (base)
    g_high: float = 0.03          # terminal growth (high)

def infer_inputs_from_row(row: pd.Series) -> DCFInputs:
    rev = float(row.get("revenue_ttm") or np.nan)

    # Prefer TTM D&A and CAPEX from quarterly
    danda_ttm = row.get("danda_ttm")
    capex_ttm = row.get("capex_ttm")
    ebitda    = row.get("ebitda_ttm")
    op_income_ttm = row.get("op_income_ttm")

    # D&A% and CAPEX% from quarterly data if available; otherwise fall back.
    d_and_a_pct = 0.05
    if pd.notna(danda_ttm) and pd.notna(rev) and rev > 0:
        d_and_a_pct = max(0.0, float(danda_ttm) / rev)

    capex_pct = 0.06
    if pd.notna(capex_ttm) and pd.notna(rev) and rev > 0:
        capex_pct = max(0.0, float(capex_ttm) / rev)

    # EBIT margin = EBITDA% - D&A% (bounded); prefer TTM operating income if available
    if pd.notna(op_income_ttm) and pd.notna(rev) and rev > 0:
        ebit_margin = max(0.0, min(0.50, float(op_income_ttm) / rev))
    elif pd.notna(ebitda) and pd.notna(rev) and rev > 0:
        ebit_margin = max(0.0, min(0.50, float(ebitda) / rev - d_and_a_pct))
    else:
        ebit_margin = 0.15

    # Operating NWC% from level if available (allow negatives; common in retail)
    nwc_pct = 0.10
    op_nwc = row.get("op_nwc")
    if pd.notna(op_nwc) and pd.notna(rev) and rev > 0:
        try:
            nwc_pct = float(op_nwc) / float(rev)
        except Exception:
            nwc_pct = np.nan

    # Only fall back if invalid; otherwise bound to a sane range that allows negatives
    if not pd.notna(nwc_pct) or not np.isfinite(nwc_pct):
        nwc_pct = 0.10
    else:
        nwc_pct = float(np.clip(nwc_pct, -0.30, 0.50))
    return DCFInputs(
        revenue_ttm=rev,
        ebit_margin=ebit_margin,
        tax_rate=0.22,
        wacc=0.09,
        capex_pct=capex_pct,
        d_and_a_pct=d_and_a_pct,
        nwc_pct=nwc_pct,
        years=5,
        growth_low=0.03,  growth_base=0.06,  growth_high=0.09,
        g_low=0.01,       g_base=0.02,       g_high=0.03,
    )

def dcf_ev(inputs: DCFInputs) -> Dict[str, float]:
    """Return EV for low/base/high scenarios (FCFF model with Gordon terminal)."""

    def _run(yearly_growth: float, g_term: float) -> float:
        rev = inputs.revenue_ttm
        ev = 0.0
        # starting NWC level (as % of revenue)
        nwc = inputs.nwc_pct * rev

        for t in range(1, inputs.years + 1):
            rev_next = rev * (1.0 + yearly_growth)
            ebit = rev_next * inputs.ebit_margin
            nopat = ebit * (1.0 - inputs.tax_rate)
            d_and_a = inputs.d_and_a_pct * rev_next

            # Taper CAPEX% linearly toward D&A% by year N (maintenance capex at horizon)
            capex_pct_t = inputs.capex_pct - (inputs.capex_pct - inputs.d_and_a_pct) * (t / inputs.years)
            capex = capex_pct_t * rev_next

            nwc_next = inputs.nwc_pct * rev_next
            delta_nwc = nwc_next - nwc

            fcff = nopat + d_and_a - capex - delta_nwc
            ev += fcff / ((1.0 + inputs.wacc) ** t)

            rev = rev_next
            nwc = nwc_next

        # Terminal value using FCFF_(n+1) / (WACC - g)
        rev_T1 = rev * (1.0 + g_term)
        ebit_T1 = rev_T1 * inputs.ebit_margin
        nopat_T1 = ebit_T1 * (1.0 - inputs.tax_rate)
        d_and_a_T1 = inputs.d_and_a_pct * rev_T1
        capex_T1 = inputs.d_and_a_pct * rev_T1  # maintenance capex at terminal
        nwc_T1 = inputs.nwc_pct * rev_T1
        delta_nwc_T1 = nwc_T1 - nwc

        fcff_T1 = nopat_T1 + d_and_a_T1 - capex_T1 - delta_nwc_T1
        # --- Diagnostic guard ---
        if fcff_T1 <= 0 or np.isnan(fcff_T1):
            # print(f"[warn] DCF invalid: terminal FCFF is non-positive ({fcff_T1/1e9:.2f} B). "
            #     "Enterprise Value not meaningful under current assumptions.")
            return np.nan  # return a float placeholder
        
        tv = np.nan
        if inputs.wacc > g_term:  # guardrail against div-by-zero / negative denom
            tv = fcff_T1 / (inputs.wacc - g_term)
            ev += tv / ((1.0 + inputs.wacc) ** inputs.years)

        return float(ev)
    
    values = {
        "low":  _run(inputs.growth_low,  inputs.g_low),
        "base": _run(inputs.growth_base, inputs.g_base),
        "high": _run(inputs.growth_high, inputs.g_high),
    }
    if all(np.isnan(list(values.values()))):
        print("[warn] All DCF scenarios invalid (non-positive terminal FCFFs).")
    
    return values