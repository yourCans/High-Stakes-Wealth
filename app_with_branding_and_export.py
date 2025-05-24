
import streamlit as st
import yfinance as yf
from pycoingecko import CoinGeckoAPI
import pandas as pd
import matplotlib.pyplot as plt
import random
from datetime import datetime, timedelta
from io import StringIO

st.set_page_config(page_title="High-Stakes Wealth", layout="wide")

# Branding
st.image("https://yourcans.com.au/logo.png", width=120)  # Replace with your actual logo URL
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
high_value = investment * high_risk / 100
low_value = investment * low_risk / 100
st.write(f"- High-Risk Allocation: **${high_value:,.2f}**")
st.write(f"- Low-Risk Allocation: **${low_value:,.2f}**")

st.markdown("---")

# AI-Powered Suggestions
st.markdown("### 🧠 AI-Powered Investment Suggestions")
high_risk_picks = ["BTC", "ETH", "TSLA", "DOGE", "SOL"]
low_risk_picks = ["AAPL", "MSFT", "BND", "VTI", "GOOGL"]

high_picks = random.sample(high_risk_picks, 3)
low_picks = random.sample(low_risk_picks, 2)

st.write(f"**High-Risk Picks:** {', '.join(high_picks)}")
st.write(f"**Low-Risk Picks:** {', '.join(low_picks)}")

st.markdown("---")

# Simulated Portfolio Tracker
st.markdown("### 📉 Simulated Portfolio Performance (Last 7 Days)")
dates = [datetime.now() - timedelta(days=i) for i in range(6, -1, -1)]
dates = [d.strftime('%Y-%m-%d') for d in dates]
base = investment
performance = [round(base + random.uniform(-0.03, 0.04) * base, 2) for _ in range(7)]

perf_df = pd.DataFrame({"Date": dates, "Portfolio Value": performance})

fig, ax = plt.subplots()
ax.plot(perf_df["Date"], perf_df["Portfolio Value"], marker='o')
ax.set_title("Simulated Portfolio Value")
ax.set_ylabel("Value ($)")
ax.set_xlabel("Date")
plt.xticks(rotation=45)
st.pyplot(fig)

# Export to CSV
st.markdown("### 📤 Export Report")
csv_buffer = StringIO()
perf_df.to_csv(csv_buffer, index=False)
st.download_button(label="Download Portfolio CSV",
                   data=csv_buffer.getvalue(),
                   file_name="portfolio_report.csv",
                   mime="text/csv")

st.markdown("---")
st.markdown("🔔 *Email/text alerts and full PDF exports coming soon.*")
