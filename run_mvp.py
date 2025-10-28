# run_mvp.py
import sys
import pandas as pd
import numpy as np
from comps_select import suggest_comp_tickers
from data_fetch import get_snapshots
from valuation import pctiles, implied_ev_from_multiple
from visualize import plot_football_field_ev
from dcf import infer_inputs_from_row, dcf_ev

def clean_peers(peers: pd.DataFrame) -> pd.DataFrame:
    """Basic hygiene: require positive drivers, drop NaNs/infs, winsorize 5–95%."""
    peers = peers.copy()

    # keep only rows with usable drivers
    keep = (
        peers["revenue_ttm"].replace([np.inf, -np.inf], np.nan).gt(0)
        & peers["ebitda_ttm"].replace([np.inf, -np.inf], np.nan).gt(0)
        & peers["enterprise_value"].replace([np.inf, -np.inf], np.nan).gt(0)
    )
    peers = peers[keep]

    # compute multiples if missing (defensive)
    with np.errstate(divide="ignore", invalid="ignore"):
        if "ev_rev" not in peers:
            peers["ev_rev"] = peers["enterprise_value"] / peers["revenue_ttm"]
        if "ev_ebitda" not in peers:
            peers["ev_ebitda"] = peers["enterprise_value"] / peers["ebitda_ttm"]

    # drop NaNs/infs
    for col in ["ev_rev", "ev_ebitda"]:
        peers[col] = peers[col].replace([np.inf, -np.inf], np.nan)

    peers = peers.dropna(subset=["ev_rev", "ev_ebitda"])

    # winsorize to reduce outlier impact (5th–95th percentile clipping)
    for col in ["ev_rev", "ev_ebitda"]:
        if not peers[col].empty:
            lo, hi = peers[col].quantile([0.05, 0.95])
            peers[col] = peers[col].clip(lower=lo, upper=hi)

    return peers

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_mvp.py <TARGET_TICKER_OR_NAME>")
        sys.exit(1)

    target = sys.argv[1]
    print(f"Target: {target}")

    comps = suggest_comp_tickers(target, n=15)
    print("Proposed comps:", comps)

    # fetch data for comps + target
    tickers = [target] + comps
    df = get_snapshots(tickers)

    upper = df["ticker"].str.upper()
    if target.upper() not in set(upper):
        raise RuntimeError(f"Could not fetch data for target {target}. Got: {sorted(set(upper))}")

    # split target vs peers
    target_row = df[df["ticker"].str.upper() == target.upper()].iloc[0]
    peers = df[df["ticker"].str.upper() != target.upper()]

    raw_count = len(peers)
    peers = clean_peers(peers)
    print(f"Peers used for multiples: {len(peers)}/{raw_count} after filters (winsorized 5–95%).")

    print("\nPeer multiples snapshot:")
    print(peers[["ticker", "ev_rev", "ev_ebitda"]].head(n=15).to_string(index=False))

    # compute peer multiple percentiles
    for col in ["ev_rev", "ev_ebitda"]:
        p25, p50, p75 = pctiles(peers[col])
        df.loc[df["ticker"] == target_row["ticker"], f"{col}_p25"] = p25
        df.loc[df["ticker"] == target_row["ticker"], f"{col}_p50"] = p50
        df.loc[df["ticker"] == target_row["ticker"], f"{col}_p75"] = p75

    target_row = df[df["ticker"] == target_row["ticker"]].iloc[0]

    # ---- DCF module ----
    dcf_inputs = infer_inputs_from_row(target_row)
    dcf_ranges = dcf_ev(dcf_inputs)

    implied_ev = {
        "EV/Revenue": implied_ev_from_multiple(target_row, "ev_rev", "revenue_ttm"),
        "EV/EBITDA":  implied_ev_from_multiple(target_row, "ev_ebitda", "ebitda_ttm"),
        "DCF (FCFF)": dcf_ranges,
    }

    print("\nDCF inputs (key):")
    print(
        f"Rev_TTM={dcf_inputs.revenue_ttm/1e9:.0f} B, EBIT%={dcf_inputs.ebit_margin:.2%}, "
        f"Tax={dcf_inputs.tax_rate:.0%}, WACC={dcf_inputs.wacc:.0%}, Years={dcf_inputs.years}\n"
        f"D&A%={dcf_inputs.d_and_a_pct:.0%}, CAPEX%={dcf_inputs.capex_pct:.0%}, NWC%={dcf_inputs.nwc_pct:.0%}\n"
        f"Growth low/base/high={dcf_inputs.growth_low:.0%}/{dcf_inputs.growth_base:.0%}/{dcf_inputs.growth_high:.0%}, "
        f"g low/base/high={dcf_inputs.g_low:.0%}/{dcf_inputs.g_base:.0%}/{dcf_inputs.g_high:.0%}\n"
    )

    for k, v in dcf_ranges.items():
        print(f"DCF {k} EV: {v/1e9:.1f} B")

    spot_ev = target_row.get("enterprise_value")

    print("\nImplied enterprise value ranges (same currency as data, values expressed in Billions):")
    df_print = pd.DataFrame.from_dict(implied_ev, orient="index") / 1e9
    print(df_print.round(3))
    if pd.notna(spot_ev):
        print(f"Spot EV: {spot_ev/1e9:.1f} B")

    outpng = f"football_field_ev_{target_row['ticker']}.png"
    plot_football_field_ev(
        implied_ev, 
        title=f"{target_row['ticker']} – Football Field (Enterprise Value)",
        outpath=outpng,
        spot_ev=spot_ev if pd.notna(spot_ev) else None
    )
    print(f"Saved chart -> {outpng}")

if __name__ == "__main__":
    main()
