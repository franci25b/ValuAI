# comps_select.py
from typing import List
import textwrap
import yfinance as yf
from google.genai import types
from gemini_client import ask_json

# Schema: list of tickers only
TickerListSchema = types.Schema(
    type=types.Type.ARRAY,
    items=types.Schema(type=types.Type.STRING),
    description="List of stock tickers (e.g., AAPL, MSFT). No explanations."
)

def _validate_tickers(cands: List[str], n: int) -> List[str]:
    seen = set()
    valid = []
    for t in cands:
        t = t.upper().strip()
        if t in seen:
            continue
        seen.add(t)
        try:
            data = yf.download(t, period="5d", interval="1d", progress=False, auto_adjust=False)
            if not data.empty:
                valid.append(t)
        except Exception:
            continue
        if len(valid) >= n:
            break
    return valid

def suggest_comp_tickers(company_or_ticker: str, n: int = 15) -> List[str]:
    prompt = textwrap.dedent(f"""
    You are an equity analyst. Return ONLY a JSON array of {n} liquid, listed
    peer tickers that are the closest business comparables for: "{company_or_ticker}".
    Prefer same sub-industry, similar business model and revenue scale. Avoid ETFs,
    indices, preferreds, warrants, duplicates, or non-listed symbols. Output ONLY JSON.
    """)
    try:
        raw_list = ask_json(prompt, schema=TickerListSchema)  # Call Gemini with a strict schema.
        validated = _validate_tickers(raw_list, n)            # Filter to real, tradeable, deduped tickers.
        # Require at least a “handful” so the percentiles you compute later have some meaning.
        if len(validated) >= max(5, n // 2):
            return validated                                  # Success path: usable set of comps.
    except Exception as e:
        # Model overload, network flake, schema mismatch, etc. -> don’t crash the pipeline.
        print(f"[warn] AI comps selection failed: {e}")
    return []