# ValuAI — Automated Company Valuation using DCF and Market Multiples

## Quick Start
```bash
# Clone, install dependencies, and run your first valuation
git clone https://github.com/yourusername/ValuAI.git
cd ValuAI
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_mvp.py JNJ
```

## Overview
ValuAI is a Python-based financial analysis tool that estimates a company’s intrinsic value using
Discounted Cash Flow (DCF) analysis and comparable company (market) multiples.  

The current version of ValuAI uses **Google Gemini** as its only AI model. Gemini assists the system by selecting comparable companies based on sector, geography, and business model.
It will also be used to support a stock's risk evaluation in future releases.

The objective is to merge rigorous quantitative modeling with AI-driven contextual understanding to produce realistic, transparent, and reproducible valuation estimates.

---

## Core Features
- Automated data fetching for key financial variables (Revenue, EBIT, CapEx, NWC, etc.)
- AI-assisted comparable company selection powered by Gemini
- DCF engine with customizable assumptions (WACC, growth, margins, NWC%, CapEx tapering)
- Fallbacks for missing or unreliable financial data
- Modular code structure separating data, modeling, and output generation
- Extendable architecture to include additional AI models or valuation methods

---

## Project Structure
| File | Description |
|------|--------------|
| `data_fetch.py` | Fetches and processes company fundamentals (TTM, balance sheet, etc.) |
| `dcf.py` | Core DCF model and helper functions for projecting free cash flow and enterprise value |
| `run_mvp.py` | Main execution script running the valuation pipeline for a given ticker |
| `comps_select.py` | Handles comparable company selection with Gemini integration |
| `gemini_client.py` | Handles communication with Google Gemini API |
| `valuation.py` | Coordinates comparables-based valuation outputs |
| `visualize.py` | Generates formatted output and charts (if visualization is enabled) |
| `requirements.txt` | Python dependencies |
| `.env` | Contains your Gemini API key and environment variables |
| `.gitignore` | Ensures sensitive and virtual environment files are ignored by Git |
| `README.md` | This documentation file |

---

## Example Usage
```bash
# Activate your virtual environment
source .venv/bin/activate

# Run a valuation for a company
python run_mvp.py JNJ

# Output includes:
# - Peer multiples and implied valuations
# - DCF-based enterprise and equity values
# - Key model assumptions (growth, margins, NWC%, WACC)
```

---

## Setup Instructions
```bash
# Clone the repository
git clone https://github.com/yourusername/ValuAI.git
cd ValuAI

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add your Gemini API key to a .env file:
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

Then you can test it quickly:
```bash
python run_mvp.py JNJ
```

---

## Key Model Assumptions
- Net Working Capital (NWC%) defaults to 10% only when missing. Negative ratios (common in retail and consumer sectors) are allowed.
- Terminal-year CapEx equals D&A%, representing maintenance-level reinvestment.
- WACC and growth rates can be adjusted in the code for sensitivity testing.

---

## Future Improvements
- Sector-aware default parameters for NWC%, CapEx%, and WACC.
- Additional data sources for more reliable fundamentals.
- Further (AI-driven) data refinement
- Support for alternative terminal value models (perpetual growth, exit multiple, or fade models).
- Interactive front-end visualization dashboard.
- **AI-driven risk assessment module** evaluating:
  - Business model durability  
  - Competitive intensity  
  - Macroeconomic sensitivity  
  - Governance and innovation exposure

---

## Author and License
Author: Francesco Barberis  
Year: 2025  
License: MIT — open-source; use freely with attribution.
