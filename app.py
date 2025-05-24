
import streamlit as st
import yfinance as yf
from pycoingecko import CoinGeckoAPI
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="High-Stakes Wealth", layout="wide")

st.title("💸 High-Stakes Wealth")
st.subheader("AI Investing for Bold Returns")
st.markdown("**75% High Risk | 25% Low Risk | All Strategy. No Guesswork.**")

# Sidebar input
st.sidebar.header("📊 Portfolio Setup")
investment = st.sidebar.number_input("Investment Amount ($)", min_value=100, value=1000)
high_risk = st.sidebar.slider("High-Risk Allocation (%)", 50, 100, 75)
low_risk = 100 - high_risk

# Portfolio breakdown
st.markdown("### 💰 Investment Breakdown")
st.write(f"- High-Risk Allocation: **${investment * high_risk / 100:,.2f}**")
st.write(f"- Low-Risk Allocation: **${investment * low_risk / 100:,.2f}**")

st.markdown("---")

# Live Market Data Tabs
tab1, tab2 = st.tabs(["📈 Live Prices", "📊 7-Day Charts"])

with tab1:
    st.markdown("#### 💹 Stocks")
    for ticker in ["AAPL", "TSLA", "AMZN", "MSFT"]:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")["Close"].iloc[-1]
        st.write(f"**{ticker}**: ${price:,.2f}")

    st.markdown("#### 🪙 Crypto")
    cg = CoinGeckoAPI()
    cryptos = ["bitcoin", "ethereum", "solana", "dogecoin"]
    prices = cg.get_price(ids=cryptos, vs_currencies='usd')
    for crypto in cryptos:
        name = crypto.capitalize()
        price = prices[crypto]['usd']
        st.write(f"**{name}**: ${price:,.2f}")

with tab2:
    st.markdown("#### 📈 AAPL - 7 Day Price Chart")
    aapl = yf.Ticker("AAPL")
    aapl_hist = aapl.history(period="7d")["Close"]
    fig1, ax1 = plt.subplots()
    ax1.plot(aapl_hist.index, aapl_hist.values, marker='o')
    ax1.set_title("AAPL Price (Last 7 Days)")
    ax1.set_ylabel("USD")
    st.pyplot(fig1)

    st.markdown("#### 📈 Bitcoin - 7 Day Price Chart")
    btc_hist = cg.get_coin_market_chart_by_id(id='bitcoin', vs_currency='usd', days=7)['prices']
    btc_df = pd.DataFrame(btc_hist, columns=["Timestamp", "Price"])
    btc_df["Date"] = pd.to_datetime(btc_df["Timestamp"], unit='ms')
    fig2, ax2 = plt.subplots()
    ax2.plot(btc_df["Date"], btc_df["Price"], marker='.')
    ax2.set_title("Bitcoin Price (Last 7 Days)")
    ax2.set_ylabel("USD")
    st.pyplot(fig2)

st.markdown("---")
st.markdown("📉 *More AI-driven picks, analysis, and historical performance coming soon.*")
