from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf


@dataclass
class BacktestMetrics:
    total_return: float
    final_value: float
    cagr: float
    annual_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_start: pd.Timestamp
    max_drawdown_end: pd.Timestamp
    num_rebalances: int


@dataclass
class BacktestResult:
    portfolio: pd.DataFrame
    metrics: BacktestMetrics


def _download_adj_close(
    ticker: str,
    start_date: str,
    end_date: Optional[str],
) -> pd.Series:
    data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)
    if data is None or (hasattr(data, "empty") and data.empty):
        raise RuntimeError(f"No data returned for {ticker} between {start_date} and {end_date}.")

    # Select adjusted close or close
    selected = None
    if isinstance(data, pd.DataFrame):
        if "Adj Close" in data.columns:
            selected = data["Adj Close"]
        elif "Close" in data.columns:
            selected = data["Close"]
        else:
            # fallback: first numeric column
            numeric_df = data.select_dtypes(include=[np.number])
            if numeric_df.shape[1] >= 1:
                selected = numeric_df.iloc[:, 0]
            else:
                raise RuntimeError(f"Unable to find price column for {ticker}.")
    else:
        # Already a Series
        selected = data

    # If still a DataFrame (e.g., MultiIndex columns or single-level with 1+ columns), reduce to a Series
    if isinstance(selected, pd.DataFrame):
        # Try to pick the column that matches the ticker
        if isinstance(selected.columns, pd.MultiIndex):
            series_candidate = None
            for col in selected.columns:
                try:
                    # col may be tuple like ("Adj Close", "BTC-USD")
                    if isinstance(col, tuple) and any(str(ticker) == str(part) for part in col):
                        series_candidate = selected[col]
                        break
                except Exception:
                    continue
            if series_candidate is None:
                # fallback to first column
                series_candidate = selected.iloc[:, 0]
            series = pd.Series(series_candidate)
        else:
            # Single-level columns
            if ticker in selected.columns:
                series = selected[ticker]
            else:
                # fallback to first column
                series = selected.iloc[:, 0]
    else:
        series = selected

    if not isinstance(series, pd.Series):
        series = pd.Series(series)

    series.name = ticker
    series = series[~pd.isna(series)]
    # Ensure DatetimeIndex
    series.index = pd.to_datetime(series.index)
    series = series.sort_index()
    return series


def _compute_metrics(portfolio_value: pd.Series, daily_returns: pd.Series, initial_capital: float, num_rebalances: int) -> BacktestMetrics:
    portfolio_value = portfolio_value.dropna()
    if portfolio_value.empty:
        raise RuntimeError("Portfolio value series is empty after cleaning.")

    start_timestamp: pd.Timestamp = portfolio_value.index[0]
    end_timestamp: pd.Timestamp = portfolio_value.index[-1]

    final_value = float(portfolio_value.iloc[-1])
    total_return = (final_value / float(initial_capital)) - 1.0

    # Time in years for CAGR using calendar days
    num_days = (end_timestamp - start_timestamp).days
    years = max(num_days / 365.25, 1e-9)
    cagr = (final_value / float(initial_capital)) ** (1.0 / years) - 1.0

    # Annualized volatility and Sharpe (rf = 0)
    trading_days_per_year = 252.0
    daily_returns = daily_returns.dropna()
    if len(daily_returns) > 1:
        annual_volatility = float(daily_returns.std(ddof=1)) * np.sqrt(trading_days_per_year)
        sharpe_ratio = (1.0 + daily_returns.mean()) ** trading_days_per_year - 1.0
        if annual_volatility > 0:
            sharpe_ratio = sharpe_ratio / annual_volatility
        else:
            sharpe_ratio = 0.0
    else:
        annual_volatility = 0.0
        sharpe_ratio = 0.0

    # Max drawdown
    running_max = portfolio_value.cummax()
    drawdown = (portfolio_value / running_max) - 1.0
    max_drawdown = float(drawdown.min())
    mdd_end = drawdown.idxmin()
    mdd_start = portfolio_value.loc[:mdd_end].idxmax()

    return BacktestMetrics(
        total_return=float(total_return),
        final_value=float(final_value),
        cagr=float(cagr),
        annual_volatility=float(annual_volatility),
        sharpe_ratio=float(sharpe_ratio),
        max_drawdown=float(max_drawdown),
        max_drawdown_start=mdd_start,
        max_drawdown_end=mdd_end,
        num_rebalances=int(num_rebalances),
    )


def backtest_75_25(
    start_date: str = "2015-01-01",
    end_date: Optional[str] = None,
    stock_ticker: str = "SPY",
    crypto_ticker: str = "BTC-USD",
    initial_capital: float = 10_000.0,
    stock_weight: float = 0.75,
    crypto_weight: float = 0.25,
    rebalance_frequency: str = "M",  # 'M' month-end, 'Q' quarter-end, etc.
    fee_bps: float = 10.0,  # transaction cost in basis points per trade leg
) -> BacktestResult:
    """
    Backtest a 75/25 portfolio between a stock (e.g., SPY) and Bitcoin (BTC-USD) with periodic rebalancing.

    Assumptions:
    - Default target weights are 75% stocks, 25% BTC. Configure via stock_weight/crypto_weight.
    - Rebalance at period end for the provided pandas frequency string (default monthly).
    - Transaction costs applied on traded notional per rebalance (fee_bps per leg).
    - Uses yfinance adjusted close where available; otherwise falls back to close.
    - Days where either asset lacks prices are excluded to align calendars.
    """
    if not np.isclose(stock_weight + crypto_weight, 1.0):
        raise ValueError("stock_weight + crypto_weight must equal 1.0")

    if end_date is None:
        end_date = date.today().isoformat()

    stock_prices = _download_adj_close(stock_ticker, start_date, end_date)
    crypto_prices = _download_adj_close(crypto_ticker, start_date, end_date)

    # Align on common dates only (both have prices)
    prices = pd.concat(
        [stock_prices.to_frame(name="stock"), crypto_prices.to_frame(name="crypto")], axis=1
    ).dropna()

    if prices.empty or len(prices) < 2:
        raise RuntimeError("Insufficient overlapping price history for the two tickers.")

    # Determine rebalance dates (period end)
    rebalance_dates = prices.resample(rebalance_frequency).last().index

    portfolio_records = []

    units_stock: float = 0.0
    units_crypto: float = 0.0
    current_portfolio_value: float = 0.0

    num_rebalances: int = 0

    for idx, (timestamp, row) in enumerate(prices.iterrows()):
        price_stock = float(row["stock"])
        price_crypto = float(row["crypto"])

        # Portfolio value before any trades for the day
        value_stock = units_stock * price_stock
        value_crypto = units_crypto * price_crypto
        current_portfolio_value = value_stock + value_crypto

        is_first_day = idx == 0
        is_rebalance_day = (timestamp in rebalance_dates) or is_first_day

        if is_rebalance_day:
            num_rebalances += 1
            # Determine investable value (initial capital on first day; otherwise current portfolio value)
            investable_value_before_fees = initial_capital if is_first_day else current_portfolio_value

            # Compute desired units before fee adjustment to estimate traded notional
            desired_value_stock = investable_value_before_fees * stock_weight
            desired_value_crypto = investable_value_before_fees * crypto_weight
            desired_units_stock = desired_value_stock / price_stock
            desired_units_crypto = desired_value_crypto / price_crypto

            trade_units_stock = desired_units_stock - units_stock
            trade_units_crypto = desired_units_crypto - units_crypto

            traded_notional = (
                abs(trade_units_stock) * price_stock + abs(trade_units_crypto) * price_crypto
            )
            transaction_cost = traded_notional * (fee_bps / 10_000.0)

            # After fees, set units to hit target weights on net value
            investable_value_after_fees = investable_value_before_fees - transaction_cost
            if investable_value_after_fees < 0:
                raise RuntimeError(
                    "Transaction costs exceeded portfolio value. Check fee_bps or data integrity."
                )

            units_stock = (investable_value_after_fees * stock_weight) / price_stock
            units_crypto = (investable_value_after_fees * crypto_weight) / price_crypto

            # Update values post-rebalance
            value_stock = units_stock * price_stock
            value_crypto = units_crypto * price_crypto
            current_portfolio_value = value_stock + value_crypto

        weight_stock_realized = value_stock / current_portfolio_value if current_portfolio_value > 0 else 0.0
        weight_crypto_realized = value_crypto / current_portfolio_value if current_portfolio_value > 0 else 0.0

        portfolio_records.append(
            {
                "date": timestamp,
                "price_stock": price_stock,
                "price_crypto": price_crypto,
                "units_stock": units_stock,
                "units_crypto": units_crypto,
                "value_stock": value_stock,
                "value_crypto": value_crypto,
                "portfolio_value": current_portfolio_value,
                "is_rebalance": bool(is_rebalance_day),
                "weight_stock": weight_stock_realized,
                "weight_crypto": weight_crypto_realized,
            }
        )

    portfolio = pd.DataFrame.from_records(portfolio_records).set_index("date").sort_index()
    daily_returns = portfolio["portfolio_value"].pct_change()

    metrics = _compute_metrics(
        portfolio_value=portfolio["portfolio_value"],
        daily_returns=daily_returns,
        initial_capital=float(initial_capital),
        num_rebalances=num_rebalances,
    )

    return BacktestResult(portfolio=portfolio, metrics=metrics)


def _format_metrics(metrics: BacktestMetrics) -> str:
    def pct(x: float) -> str:
        return f"{x*100:.2f}%"

    lines = [
        f"Final Value: ${metrics.final_value:,.2f}",
        f"Total Return: {pct(metrics.total_return)}",
        f"CAGR: {pct(metrics.cagr)}",
        f"Annual Volatility: {pct(metrics.annual_volatility)}",
        f"Sharpe (rf=0): {metrics.sharpe_ratio:.2f}",
        f"Max Drawdown: {pct(metrics.max_drawdown)}",
        f"Max DD Period: {metrics.max_drawdown_start.date()} → {metrics.max_drawdown_end.date()}",
        f"Rebalances: {metrics.num_rebalances}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest a 75/25 Stocks/BTC strategy with periodic rebalancing.")
    parser.add_argument("--start", dest="start_date", default="2015-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", dest="end_date", default=None, help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--stock", dest="stock_ticker", default="SPY", help="Stock ticker (default: SPY)")
    parser.add_argument("--crypto", dest="crypto_ticker", default="BTC-USD", help="Crypto ticker (default: BTC-USD)")
    parser.add_argument("--initial", dest="initial_capital", type=float, default=10_000.0, help="Initial capital (default: 10000)")
    parser.add_argument("--stock-weight", dest="stock_weight", type=float, default=0.75, help="Stock weight (default: 0.75)")
    parser.add_argument("--crypto-weight", dest="crypto_weight", type=float, default=0.25, help="Crypto weight (default: 0.25)")
    parser.add_argument(
        "--rebalance",
        dest="rebalance_frequency",
        default="M",
        choices=["W", "M", "Q", "A"],
        help="Rebalance frequency: W=weekly, M=monthly, Q=quarterly, A=annual",
    )
    parser.add_argument("--fee-bps", dest="fee_bps", type=float, default=10.0, help="Transaction cost in bps per trade leg (default: 10)")
    parser.add_argument("--csv", dest="csv_path", default=None, help="Optional path to save equity curve CSV")

    args = parser.parse_args()

    result = backtest_75_25(
        start_date=args.start_date,
        end_date=args.end_date,
        stock_ticker=args.stock_ticker,
        crypto_ticker=args.crypto_ticker,
        initial_capital=args.initial_capital,
        stock_weight=args.stock_weight,
        crypto_weight=args.crypto_weight,
        rebalance_frequency=args.rebalance_frequency,
        fee_bps=args.fee_bps,
    )

    print(_format_metrics(result.metrics))
    if args.csv_path:
        result.portfolio.to_csv(args.csv_path, index=True)
        print(f"Saved equity curve to {args.csv_path}")


if __name__ == "__main__":
    main()
