# visualize.py
from typing import Dict, Optional
import matplotlib.pyplot as plt
import math

def _scale_to_billions(values):
    # returns (scaled_values, scale_label)
    maxv = max([v for d in values for v in d.values() if isinstance(v, (int, float)) and not math.isnan(v)] + [1.0])
    if maxv > 1e10:
        scale = 1e9
        label = "Enterprise Value (billions)"
    elif maxv > 1e7:
        scale = 1e6
        label = "Enterprise Value (millions)"
    else:
        scale = 1
        label = "Enterprise Value"
    scaled = [
        {k: (v / scale if isinstance(v, (int, float)) else v) for k, v in d.items()}
        for d in values
    ]
    return scaled, label


def plot_football_field(implied_prices: Dict[str, Dict[str, float]], *, title: str, outpath: str, spot_price: Optional[float] = None):
    methods = list(implied_prices.keys())
    lows   = [implied_prices[m]["low"]  for m in methods]
    bases  = [implied_prices[m]["base"] for m in methods]
    highs  = [implied_prices[m]["high"] for m in methods]

    fig, ax = plt.subplots(figsize=(8, 4.8))
    y = range(len(methods))
    ax.hlines(y, lows, highs, linewidth=10, alpha=0.4)
    ax.plot(bases, y, "o")  # show medians

    if spot_price is not None:
        ax.axvline(spot_price, linestyle="--", alpha=0.6)
        ax.text(spot_price, len(methods)-0.5, f" Spot {spot_price:.2f}", rotation=90, va="bottom", ha="left")

    ax.set_yticks(y)
    ax.set_yticklabels(methods)
    ax.set_xlabel("Implied price per share")
    ax.set_title(title)
    ax.grid(True, axis="x", linestyle=":", alpha=0.4)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)

def plot_football_field_ev(
    implied_ev: Dict[str, Dict[str, float]],
    *,
    title: str,
    outpath: str,
    spot_ev: Optional[float] = None
):
    methods = list(implied_ev.keys())
    # scale all EVs to billions for readability
    ev_dicts = [implied_ev[m] for m in methods]
    ev_dicts_scaled, x_label = _scale_to_billions(ev_dicts)
    scaled = {m: ev_dicts_scaled[i] for i, m in enumerate(methods)}
    spot_scaled = spot_ev / 1e9 if (spot_ev is not None) else None

    lows  = [scaled[m].get("low")  for m in methods]
    bases = [scaled[m].get("base") for m in methods]
    highs = [scaled[m].get("high") for m in methods]

    fig, ax = plt.subplots(figsize=(10, 5))
    y = range(len(methods))

    ax.hlines(y, lows, highs, linewidth=10, alpha=0.35)
    ax.plot(bases, y, "o")

    if spot_scaled is not None and not math.isnan(spot_scaled):
        ax.axvline(spot_scaled, linestyle="--", alpha=0.6)
        ax.text(spot_scaled, len(methods)-0.5, f" Spot EV {spot_scaled:.1f}B", rotation=90, va="bottom", ha="left")

    ax.set_yticks(list(y))
    ax.set_yticklabels(methods)
    ax.set_xlabel(x_label)
    ax.set_title(title)
    ax.grid(True, axis="x", linestyle=":", alpha=0.3)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)