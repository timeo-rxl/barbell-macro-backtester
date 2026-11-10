# barbell-macro-backtester

Backtester for the **PrepaInvest Barbell macro-tactical allocation** (CTTC 2026, HEC Montréal).

The strategy combines a defensive **Shield (47%)** with an offensive, high-beta **Spear (53%)**:

| Leg | Weight | Holdings |
| --- | --- | --- |
| 🛡️ Shield (defensive) | 47% | `VOO` 25%, `LLY` 12%, `LMT` 10% |
| ⚔️ Spear (offensive) | 53% | `NVDA` 15%, `DELL` 10%, `WDC` 10%, `GEV` 10%, `CLSK` 8% |

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

```
[PORTFOLIO - BARBELL]
  - Annualised return    :   XX.XX% (CAGR)
  - Annualised vol       :   XX.XX%
  - Sharpe ratio         :    X.XX (Rf = 3.5%)
  - Max drawdown         :  -XX.XX%
  - Beta vs SPY          :    X.XX
```

## Disclaimer

Educational project from a student fund simulation. Past performance is not indicative of future results. This is not investment advice.
