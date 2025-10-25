# run_mvp.py
import sys
import pandas as pd
from comps_select import suggest_comp_tickers
from data_fetch import get_snapshots
from valuation import pctiles, implied_price_from_multiple
from visualize import plot_football_field
#import yfinance as yf

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_mvp.py <TARGET_TICKER_OR_NAME>")
        sys.exit(1)

    target = sys.argv[1]
    print(f"Target: {target}")

    comps = suggest_comp_tickers(target, n=8)
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

    # compute peer multiple percentiles
    for col in ["ev_rev", "ev_ebitda"]:
        p25, p50, p75 = pctiles(peers[col])
        df.loc[df["ticker"] == target_row["ticker"], f"{col}_p25"] = p25
        df.loc[df["ticker"] == target_row["ticker"], f"{col}_p50"] = p50
        df.loc[df["ticker"] == target_row["ticker"], f"{col}_p75"] = p75

    target_row = df[df["ticker"] == target_row["ticker"]].iloc[0]

    # implied price ranges
    implied = {
        "EV/Revenue": implied_price_from_multiple(target_row, "ev_rev", "revenue_ttm"),
        "EV/EBITDA":  implied_price_from_multiple(target_row, "ev_ebitda", "ebitda_ttm"),
    }
    print("Implied price ranges (USD unless data says otherwise):")
    print(pd.DataFrame(implied))

    spot = target_row.get("price")
    if pd.notna(spot):
        print(f"\nSpot price: {target_row['ticker']} = {spot:.2f}")

    # plot football field
    outpng = f"football_field_{target_row['ticker']}.png"
    plot_football_field(implied, title=f"{target_row['ticker']} – Football Field", outpath=outpng)
    print(f"Saved chart -> {outpng}")

if __name__ == "__main__":
    main()
