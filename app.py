
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import smtplib
from email.message import EmailMessage

# Google Sheets setup
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPE
)

gc = gspread.authorize(creds)
sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1y-3oAxZAqtIbfDhyJyfAPwg9VafBUjY3SPs_HVFjcDI/edit")
worksheet = sh.worksheet("Sheet1")

# Email setup
EMAIL_ADDRESS = st.secrets["email"]["username"]
EMAIL_PASSWORD = st.secrets["email"]["password"]

def send_confirmation_email(name, recipient_email):
    msg = EmailMessage()
    msg["Subject"] = "✅ You're in: High-Stakes Wealth Alerts"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient_email
    msg.set_content(f"""Hi {name},

Thanks for signing up for High-Stakes Wealth alerts!

You’ll now receive:
- 📊 Weekly portfolio summaries
- 🔔 Big price movement alerts (e.g. BTC drops 10%)
- 🧠 New AI investment picks

Stay bold,
The High-Stakes Wealth Team
""")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

# Streamlit form
st.title("📬 Sign Up for High-Stakes Wealth Alerts")
st.write("Join our insider list to get:")
st.markdown("""• 📊 Weekly portfolio summaries  
• 🔔 Price movement alerts  
• 🧠 New AI investment picks""")

with st.form("signup_form", clear_on_submit=True):
    name = st.text_input("Your Name")
    email = st.text_input("Your Email")
    submitted = st.form_submit_button("Sign Me Up")

    if submitted:
        if name and email:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            worksheet.append_row([name, email, now])
            send_confirmation_email(name, email)
            st.success("✅ You’ve been added and a confirmation email has been sent!")
        else:
            st.error("Please fill in both name and email.")
