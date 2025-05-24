
import streamlit as st

st.set_page_config(page_title="High-Stakes Wealth", layout="wide")

st.title("💸 High-Stakes Wealth")
st.subheader("AI Investing for Bold Returns")
st.markdown("**75% High Risk | 25% Low Risk | All Strategy. No Guesswork.**")

st.markdown("---")

# Sidebar for user input
st.sidebar.header("📊 Portfolio Setup")
investment = st.sidebar.number_input("Investment Amount ($)", min_value=100, value=1000)
high_risk = st.sidebar.slider("High-Risk Allocation (%)", 50, 100, 75)
low_risk = 100 - high_risk

# Portfolio breakdown
st.write(f"### 💰 Investment Breakdown")
st.write(f"- High-Risk Allocation: **${investment * high_risk / 100:,.2f}**")
st.write(f"- Low-Risk Allocation: **${investment * low_risk / 100:,.2f}**")

st.markdown("---")
st.markdown("📈 *Live market data, AI picks, and performance tracking coming soon.*")
