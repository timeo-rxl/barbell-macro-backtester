"""Barbell Macro-Tactical Backtester — interactive Streamlit app.

PrepaInvest Fund — CTTC 2026 (HEC Montréal).

The same engine as ``barbell_backtester.py`` (real Yahoo Finance data,
nothing hard-coded), with the allocation, the dates and the risk-free
rate as controls: change a weight, the whole backtest recomputes —
equity curve, Sharpe, beta, drawdown, and the Shield / Spear legs.

Run:
    streamlit run app.py
"""

import datetime as dt

import pandas as pd
import streamlit as st

from barbell_backtester import (
    BENCHMARK_TICKER,
    DEFAULT_ALLOCATION,
    RISK_FREE_RATE_ANNUAL,
    SHIELD_TICKERS,
    compute_beta,
    compute_metrics,
    fetch_prices,
)

TICKERS = list(DEFAULT_ALLOCATION)
LEG = {t: ("🛡️ Shield" if t in SHIELD_TICKERS else "⚔️ Spear") for t in TICKERS}
LEG_EMOJI = {"🛡️ Shield": "🛡️", "⚔️ Spear": "⚔️"}

st.set_page_config(
    page_title="Barbell Backtester — PrepaInvest",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️⚔️ Barbell Macro-Tactical Backtester")
st.caption(
    "PrepaInvest Fund — CTTC 2026 · HEC Montréal. A defensive Shield (VOO, LLY, LMT) "
    "plus high-beta offensive exposure (NVDA, DELL, WDC, GEV, CLSK). "
    "Real market data from Yahoo Finance — change any weight and the backtest recomputes."
)


@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(tickers: tuple[str, ...], start: str, end: str) -> pd.DataFrame:
    return fetch_prices(list(tickers), start, end)


def pct(x: float) -> str:
    return f"{x * 100:.2f}%"


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Backtest settings")

    start_date = st.date_input(
        "Start date", value=dt.date(2024, 1, 1), min_value=dt.date(2015, 1, 1)
    )
    end_date = st.date_input("End date", value=dt.date.today())
    risk_free = (
        st.slider("Risk-free rate (%)", 0.0, 8.0, RISK_FREE_RATE_ANNUAL * 100, 0.5)
        / 100
    )

    st.subheader("Allocation (%)")
    if st.button("↺ Reset to CTTC 2026 allocation"):
        for t, w in DEFAULT_ALLOCATION.items():
            st.session_state[f"w_{t}"] = int(round(w * 100))
    raw_weights: dict[str, float] = {}
    for leg_name, leg_tickers in (
        ("🛡️ Shield — defensive", SHIELD_TICKERS),
        ("⚔️ Spear — offensive", [t for t in TICKERS if t not in SHIELD_TICKERS]),
    ):
        st.markdown(f"**{leg_name}**")
        for t in leg_tickers:
            raw_weights[t] = st.slider(
                t,
                min_value=0,
                max_value=40,
                value=int(round(DEFAULT_ALLOCATION[t] * 100)),
                key=f"w_{t}",
            )

total_raw = sum(raw_weights.values())
if total_raw <= 0:
    st.error("All weights are 0% — give at least one holding a weight.")
    st.stop()
weights = {t: w / total_raw for t, w in raw_weights.items()}
shield_w = sum(weights[t] for t in SHIELD_TICKERS)
st.sidebar.markdown(
    f"**Effective split:** 🛡️ Shield {shield_w * 100:.1f}% · "
    f"⚔️ Spear {(1 - shield_w) * 100:.1f}%"
)

# ---------------------------------------------------------------- run
if start_date >= end_date:
    st.error("The start date must be before the end date.")
    st.stop()

with st.spinner("Downloading prices from Yahoo Finance…"):
    try:
        prices = load_prices(tuple(TICKERS), str(start_date), str(end_date))
    except RuntimeError as exc:
        st.error(f"Could not download prices: {exc}")
        st.stop()

first, last = prices.index[0].date(), prices.index[-1].date()
daily_returns = prices.pct_change().dropna()
w = pd.Series(weights)
portfolio_returns = daily_returns[w.index] @ w
benchmark_returns = daily_returns[BENCHMARK_TICKER]

portfolio = compute_metrics(portfolio_returns, risk_free)
benchmark = compute_metrics(benchmark_returns, risk_free)
beta = compute_beta(portfolio_returns, benchmark_returns)

st.caption(
    f"Data: {first} → {last} · {len(prices)} trading days · source: Yahoo Finance · "
    f"benchmark: {BENCHMARK_TICKER} · risk-free rate: {risk_free * 100:.1f}%"
)

# ---------------------------------------------------------------- KPIs
st.subheader("Portfolio vs. benchmark")
cols = st.columns(6)
kpis = [
    ("Total return", portfolio["total_return"], benchmark["total_return"]),
    ("CAGR", portfolio["cagr"], benchmark["cagr"]),
    ("Volatility", portfolio["volatility"], benchmark["volatility"]),
    ("Sharpe ratio", portfolio["sharpe"], benchmark["sharpe"]),
    ("Max drawdown", portfolio["max_drawdown"], benchmark["max_drawdown"]),
    ("Beta vs SPY", beta, 1.0),
]
for col, (label, p_val, b_val) in zip(cols, kpis):
    with col:
        st.metric(
            label,
            pct(p_val) if "ratio" not in label and "Beta" not in label else f"{p_val:.2f}",
            delta=(
                f"{(p_val - b_val) * 100:+.1f} pts vs SPY"
                if "ratio" not in label and "Beta" not in label
                else f"{p_val - b_val:+.2f} vs SPY"
            ),
        )

# ---------------------------------------------------------------- equity curve
st.subheader("Equity curve — $100 invested")
equity = pd.DataFrame(
    {
        "Barbell": portfolio["equity"] * 100,
        BENCHMARK_TICKER: benchmark["equity"] * 100,
    }
)
st.line_chart(equity)

st.subheader("Drawdown — how far the Barbell fell from its peak")
running_max = portfolio["equity"].cummax()
drawdown = ((portfolio["equity"] - running_max) / running_max * 100).rename("Barbell drawdown %")
st.area_chart(drawdown)

# ---------------------------------------------------------------- legs
st.subheader("Shield vs. Spear — same period, weights renormalised within each leg")
leg_rows = []
for leg_name, leg_tickers in (
    ("🛡️ Shield (defensive)", SHIELD_TICKERS),
    ("⚔️ Spear (offensive)", [t for t in TICKERS if t not in SHIELD_TICKERS]),
):
    leg_w = w[leg_tickers] / w[leg_tickers].sum()
    leg_m = compute_metrics(daily_returns[leg_tickers] @ leg_w, risk_free)
    leg_rows.append(
        {
            "Leg": leg_name,
            "Weight": f"{w[leg_tickers].sum() * 100:.1f}%",
            "Total return": pct(leg_m["total_return"]),
            "CAGR": pct(leg_m["cagr"]),
            "Volatility": pct(leg_m["volatility"]),
            "Sharpe": f"{leg_m['sharpe']:.2f}",
            "Max drawdown": pct(leg_m["max_drawdown"]),
        }
    )
leg_rows.append(
    {
        "Leg": "Barbell (portfolio)",
        "Weight": "100%",
        "Total return": pct(portfolio["total_return"]),
        "CAGR": pct(portfolio["cagr"]),
        "Volatility": pct(portfolio["volatility"]),
        "Sharpe": f"{portfolio['sharpe']:.2f}",
        "Max drawdown": pct(portfolio["max_drawdown"]),
    }
)
leg_rows.append(
    {
        "Leg": f"Benchmark ({BENCHMARK_TICKER})",
        "Weight": "—",
        "Total return": pct(benchmark["total_return"]),
        "CAGR": pct(benchmark["cagr"]),
        "Volatility": pct(benchmark["volatility"]),
        "Sharpe": f"{benchmark['sharpe']:.2f}",
        "Max drawdown": pct(benchmark["max_drawdown"]),
    }
)
st.dataframe(pd.DataFrame(leg_rows), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- holdings
st.subheader("Holdings")
holding_rows = []
for t in TICKERS:
    # GEV only started trading in April 2024, so its first price in a window
    # starting earlier is NaN — use its first valid price instead.
    first_price = prices[t].dropna().iloc[0]
    last_price = prices[t].iloc[-1]
    total_ret = last_price / first_price - 1
    holding_rows.append(
        {
            "Ticker": t,
            "Leg": LEG[t],
            "Weight": pct(weights[t]),
            "Price first → last": f"${first_price:.2f} → ${last_price:.2f}",
            "Total return": pct(total_ret),
        }
    )
st.dataframe(pd.DataFrame(holding_rows), use_container_width=True, hide_index=True)

st.subheader("Allocation")
alloc_df = pd.DataFrame(
    {"Weight %": [weights[t] * 100 for t in TICKERS]}, index=TICKERS
)
st.bar_chart(alloc_df)

st.divider()
st.caption(
    "Method: daily returns on adjusted closes, rebalanced to the target weights every day. "
    "Sharpe = (CAGR − risk-free rate) / annualised volatility. "
    "Past performance is not indicative of future results — this is a student project, not investment advice."
)
