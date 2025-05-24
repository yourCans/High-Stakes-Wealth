
import streamlit as st
import yfinance as yf
from pycoingecko import CoinGeckoAPI
import pandas as pd
import matplotlib.pyplot as plt
import random
from datetime import datetime, timedelta
from io import StringIO, BytesIO

from fpdf import FPDF

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

# Email input
st.sidebar.markdown("📧 **Optional Email for Alerts**")
user_email = st.sidebar.text_input("Enter your email (simulated only)")

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

# CSV Export
st.markdown("### 📤 Export Options")
csv_buffer = StringIO()
perf_df.to_csv(csv_buffer, index=False)
st.download_button(label="Download CSV Report",
                   data=csv_buffer.getvalue(),
                   file_name="portfolio_report.csv",
                   mime="text/csv")

# PDF Export (Simulated)
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'High-Stakes Wealth - Portfolio Summary', ln=1, align='C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

pdf = PDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.cell(200, 10, txt=f"Investment Amount: ${investment}", ln=1)
pdf.cell(200, 10, txt=f"High-Risk Allocation: {high_risk}%", ln=1)
pdf.cell(200, 10, txt=f"Low-Risk Allocation: {low_risk}%", ln=1)
pdf.cell(200, 10, txt=" ", ln=1)
pdf.cell(200, 10, txt="AI Investment Picks:", ln=1)
pdf.cell(200, 10, txt=f"High-Risk: {', '.join(high_picks)}", ln=1)
pdf.cell(200, 10, txt=f"Low-Risk: {', '.join(low_picks)}", ln=1)

pdf.cell(200, 10, txt=" ", ln=1)
pdf.cell(200, 10, txt="Portfolio Value (7 Days):", ln=1)
for date, value in zip(dates, performance):
    pdf.cell(200, 10, txt=f"{date}: ${value}", ln=1)

pdf_output = BytesIO()
pdf.output(pdf_output)
st.download_button(label="Download PDF Summary",
                   data=pdf_output.getvalue(),
                   file_name="portfolio_summary.pdf",
                   mime="application/pdf")

st.markdown("---")
st.markdown("✅ *Email alerts saved (simulated), export options now live. More features coming soon.*")
