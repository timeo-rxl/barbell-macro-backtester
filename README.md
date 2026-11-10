# barbell-macro-backtester

Backtester for the **PrepaInvest Barbell macro-tactical allocation** (CTTC 2026, HEC Montréal).

The strategy combines a defensive **Shield (47%)** with an offensive, high-beta **Spear (53%)**:

| Leg | Weight | Holdings |
| --- | --- | --- |
| 🛡️ Shield (defensive) | 47% | `VOO` 25%, `LLY` 12%, `LMT` 10% |
| ⚔️ Spear (offensive) | 53% | `NVDA` 15%, `DELL` 10%, `WDC` 10%, `GEV` 10%, `CLSK` 8% |

**Live demo:** https://rk3bdkp5mpgddrd25qgnsr.streamlit.app/ — change any weight, date or risk-free rate and the backtest recomputes.

## What it computes

From real market data (Yahoo Finance via `yfinance`) — nothing is hard-coded:

- Annualised return (CAGR), volatility, Sharpe ratio, maximum drawdown
- CAPM Beta vs. `SPY`
- The same metrics for each leg of the Barbell, so you can see what the Shield and the Spear each contribute

## Quick start

```bash
pip install -r requirements.txt
python barbell_backtester.py
```

```bash
# Custom window
python barbell_backtester.py --start 2023-01-01 --end 2025-06-30

# Export the daily equity curve
python barbell_backtester.py --start 2024-01-01 --output equity_curve.csv
```

## Example output

Verified run, H1 2025 (2025-01-01 → 2025-06-30, 120 trading days):

```
[PORTFOLIO - BARBELL]
  - Total return         :   17.00%
  - Annualised return    :   39.06% (CAGR)
  - Annualised vol       :   36.21%
  - Sharpe ratio         :    0.98 (Rf = 3.5%)
  - Max drawdown         :  -25.44%
  - Beta vs SPY          :    1.27
```

## Disclaimer

Educational project from a student fund simulation. Past performance is not indicative of future results. This is not investment advice.
