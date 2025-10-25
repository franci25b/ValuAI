# visualize.py
from typing import Dict
import matplotlib.pyplot as plt

def plot_football_field(implied_prices: Dict[str, Dict[str, float]], *, title: str, outpath: str):
    methods = list(implied_prices.keys())
    lows   = [implied_prices[m]["low"]  for m in methods]
    bases  = [implied_prices[m]["base"] for m in methods]
    highs  = [implied_prices[m]["high"] for m in methods]

    fig, ax = plt.subplots(figsize=(8, 4.8))
    y = range(len(methods))
    ax.hlines(y, lows, highs, linewidth=10, alpha=0.4)
    ax.plot(bases, y, "o")  # show medians
    ax.set_yticks(y)
    ax.set_yticklabels(methods)
    ax.set_xlabel("Implied price per share")
    ax.set_title(title)
    ax.grid(True, axis="x", linestyle=":", alpha=0.4)
    fig.tight_layout()
    fig.savefig(outpath, dpi=160)
    plt.close(fig)
