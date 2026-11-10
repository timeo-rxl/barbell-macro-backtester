"""
Barbell Macro-Tactical Allocation Backtester
PrepaInvest Fund - CTTC 2026 (HEC Montréal)

Author: Timéo Rouxel

Backtests an asymmetric Barbell portfolio allocation on real market data
(Yahoo Finance via yfinance): a defensive Shield (VOO, LLY, LMT) combined
with high-beta offensive exposure (NVDA, DELL, WDC, GEV, CLSK).

Metrics computed from the downloaded prices (nothing is hard-coded):
annualised return (CAGR), volatility, Sharpe ratio, maximum drawdown,
CAPM Beta vs. SPY, plus the same metrics for each leg of the Barbell.

Usage:
    python barbell_backtester.py
    python barbell_backtester.py --start 2024-01-01 --end 2025-12-31
    python barbell_backtester.py --start 2023-01-01 --output equity_curve.csv

Requirements:
    pip install -r requirements.txt
"""

import argparse
import sys

import numpy as np
import pandas as pd
import yfinance as yf

# Allocation weights from the PrepaInvest CTTC 2026 strategy report.
# Shield (defensive / risk-off) = 47% -- Spear (offensive / high-beta) = 53%
DEFAULT_ALLOCATION = {
    # Shield
    "VOO": 0.25,  # S&P 500 base
    "LLY": 0.12,  # Eli Lilly (defensive growth / GLP-1)
    "LMT": 0.10,  # Lockheed Martin (geopolitical hedge)
    # Spear
    "NVDA": 0.15,  # AI hardware & compute leader
    "DELL": 0.10,  # AI infrastructure & server refresh
    "WDC": 0.10,  # Memory & data-storage cycle
    "GEV": 0.10,  # GE Vernova (grid & power for AI data centres)
    "CLSK": 0.08,  # CleanSpark (Bitcoin-mining proxy / high beta)
}

BENCHMARK_TICKER = "SPY"
RISK_FREE_RATE_ANNUAL = 0.035  # 3.5% risk-free rate estimate
TRADING_DAYS_PER_YEAR = 252

SHIELD_TICKERS = ["VOO", "LLY", "LMT"]


def fetch_prices(tickers, start, end):
    """Download adjusted daily closes for the tickers + benchmark."""
    all_tickers = sorted(set(tickers) | {BENCHMARK_TICKER})
    prices = yf.download(
        all_tickers, start=start, end=end, auto_adjust=True, progress=False
    )
    if prices.empty:
        raise RuntimeError("No price data downloaded (check dates / connection).")

    # yfinance returns a MultiIndex column frame when several tickers are
    # requested; keep only the Close prices.
    if isinstance(prices.columns, pd.MultiIndex):
        prices = prices["Close"]
    prices = prices.dropna(how="all").dropna(axis=1, how="all")

    missing = [t for t in all_tickers if t not in prices.columns]
    if missing:
        raise RuntimeError(f"No data for: {', '.join(missing)}")
    return prices


def compute_metrics(daily_returns, risk_free_annual=RISK_FREE_RATE_ANNUAL):
    """Annualised metrics for a daily-return series."""
    daily_returns = daily_returns.dropna()
    n_days = len(daily_returns)
    if n_days < 2:
        raise ValueError("Not enough data points to compute metrics.")

    equity = (1 + daily_returns).cumprod()
    total_return = equity.iloc[-1] - 1
    years = n_days / TRADING_DAYS_PER_YEAR
    cagr = (1 + total_return) ** (1 / years) - 1
    volatility = daily_returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe = (cagr - risk_free_annual) / volatility if volatility else float("nan")
    running_max = equity.cummax()
    max_drawdown = ((equity - running_max) / running_max).min()

    return {
        "days": n_days,
        "total_return": total_return,
        "cagr": cagr,
        "volatility": volatility,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "equity": equity,
    }


def compute_beta(portfolio_returns, benchmark_returns):
    """CAPM Beta of the portfolio vs. the benchmark (daily returns)."""
    aligned = pd.DataFrame(
        {"portfolio": portfolio_returns, "benchmark": benchmark_returns}
    ).dropna()
    if len(aligned) < 2 or aligned["benchmark"].var() == 0:
        return float("nan")
    return aligned["portfolio"].cov(aligned["benchmark"]) / aligned["benchmark"].var()


def print_allocation(allocation):
    shield_weight = sum(allocation[t] for t in SHIELD_TICKERS)
    spear_weight = 1 - shield_weight
    print("=" * 65)
    print("  PREPAINVEST - BARBELL MACRO-TACTICAL ALLOCATION (CTTC 2026)")
    print("=" * 65)
    print(f"\n[SHIELD - DEFENSIVE] - Total weight: {shield_weight * 100:.1f}%")
    for ticker in SHIELD_TICKERS:
        print(f"  - {ticker:<6}: {allocation[ticker] * 100:>5.1f}%")
    print(f"\n[SPEAR - OFFENSIVE] - Total weight: {spear_weight * 100:.1f}%")
    for ticker, weight in allocation.items():
        if ticker not in SHIELD_TICKERS:
            print(f"  - {ticker:<6}: {weight * 100:>5.1f}%")
    print("\n" + "-" * 65)


def print_metrics(title, metrics, beta=None):
    print(f"\n[{title}]")
    print(f"  - Trading days         : {metrics['days']}")
    print(f"  - Total return         : {metrics['total_return'] * 100:>7.2f}%")
    print(f"  - Annualised return    : {metrics['cagr'] * 100:>7.2f}% (CAGR)")
    print(f"  - Annualised vol       : {metrics['volatility'] * 100:>7.2f}%")
    print(f"  - Sharpe ratio         : {metrics['sharpe']:>7.2f} (Rf = "
          f"{RISK_FREE_RATE_ANNUAL * 100:.1f}%)")
    print(f"  - Max drawdown         : {metrics['max_drawdown'] * 100:>7.2f}%")
    if beta is not None:
        print(f"  - Beta vs {BENCHMARK_TICKER}          : {beta:>7.2f}")


def main():
    parser = argparse.ArgumentParser(
        description="Backtest the PrepaInvest Barbell allocation."
    )
    parser.add_argument("--start", default="2024-01-01",
                        help="Backtest start date (YYYY-MM-DD).")
    parser.add_argument("--end", default=None,
                        help="Backtest end date (YYYY-MM-DD, default: today).")
    parser.add_argument("--rf", type=float, default=RISK_FREE_RATE_ANNUAL,
                        help="Annual risk-free rate (default: 0.035).")
    parser.add_argument("--output", default=None,
                        help="Optional CSV path for the daily equity curve.")
    args = parser.parse_args()

    if abs(sum(DEFAULT_ALLOCATION.values()) - 1.0) > 1e-9:
        print("Error: allocation weights do not sum to 100%.", file=sys.stderr)
        return 1

    print_allocation(DEFAULT_ALLOCATION)

    try:
        prices = fetch_prices(list(DEFAULT_ALLOCATION), args.start, args.end)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    first, last = prices.index[0].date(), prices.index[-1].date()
    print(f"Data: {first} -> {last} "
          f"({len(prices)} trading days, source: Yahoo Finance)")

    daily_returns = prices.pct_change().dropna()
    weights = pd.Series(DEFAULT_ALLOCATION)
    portfolio_returns = daily_returns[weights.index] @ weights
    benchmark_returns = daily_returns[BENCHMARK_TICKER]

    portfolio_metrics = compute_metrics(portfolio_returns, args.rf)
    benchmark_metrics = compute_metrics(benchmark_returns, args.rf)
    beta = compute_beta(portfolio_returns, benchmark_returns)

    print_metrics("PORTFOLIO - BARBELL", portfolio_metrics, beta=beta)
    print_metrics(f"BENCHMARK - {BENCHMARK_TICKER}", benchmark_metrics)

    # Same metrics for each leg, weights renormalised within the leg.
    for leg_name, leg_tickers in (
        ("LEG - SHIELD (defensive)", SHIELD_TICKERS),
        ("LEG - SPEAR (offensive)",
         [t for t in DEFAULT_ALLOCATION if t not in SHIELD_TICKERS]),
    ):
        leg_weights = weights[leg_tickers] / weights[leg_tickers].sum()
        leg_returns = daily_returns[leg_tickers] @ leg_weights
        print_metrics(leg_name, compute_metrics(leg_returns, args.rf))

    print("\n" + "-" * 65)
    print("Note: past performance is not indicative of future results.")

    if args.output:
        portfolio_metrics["equity"].rename("barbell_equity").to_csv(args.output)
        print(f"Equity curve saved to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
