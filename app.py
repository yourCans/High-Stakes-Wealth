
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import smtplib
from email.message import EmailMessage
import os
import re
import matplotlib.pyplot as plt

# Google Sheets setup
# Restrict OAuth scope to spreadsheets only to follow least-privilege.
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets"
]

import json
import base64

# Lazily initialize clients and worksheet with caching to avoid re-auth on every rerun.
@st.cache_resource(show_spinner=False)
def get_gspread_client() -> gspread.client.Client:
    encoded_key = None
    try:
        encoded_key = st.secrets["gcp"]["encoded_key"]
    except Exception:
        # Fallback to environment variable to improve local dev experience
        encoded_key = os.environ.get("GCP_ENCODED_KEY")
    if not encoded_key:
        raise RuntimeError("Missing GCP service account key. Set 'gcp.encoded_key' in secrets or GCP_ENCODED_KEY env var.")

    decoded = base64.b64decode(encoded_key).decode("utf-8")
    service_account_info = json.loads(decoded)
    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def get_worksheet() -> gspread.models.Worksheet:
    sheet_url = None
    try:
        sheet_url = st.secrets.get("gcp", {}).get("sheet_url")  # type: ignore[attr-defined]
    except Exception:
        sheet_url = None
    if not sheet_url:
        sheet_url = os.environ.get("SHEET_URL")
    if not sheet_url:
        raise RuntimeError("Missing Google Sheet URL. Set 'gcp.sheet_url' in secrets or SHEET_URL env var.")

    gc = get_gspread_client()
    sh = gc.open_by_url(sheet_url)
    return sh.worksheet("Sheet1")

def get_email_credentials() -> tuple[str, str]:
    username = None
    password = None
    try:
        username = st.secrets["email"]["username"]
        password = st.secrets["email"]["password"]
    except Exception:
        username = os.environ.get("EMAIL_USERNAME")
        password = os.environ.get("EMAIL_PASSWORD")
    if not username or not password:
        raise RuntimeError("Missing email credentials. Set email.username/password in secrets or EMAIL_USERNAME/EMAIL_PASSWORD env vars.")
    return username, password


def is_valid_email(address: str) -> bool:
    if not isinstance(address, str):
        return False
    address = address.strip()
    if "\n" in address or "\r" in address:
        return False
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return re.match(pattern, address) is not None


def send_confirmation_email(name: str, recipient_email: str):
    sender_email, sender_password = get_email_credentials()
    msg = EmailMessage()
    msg["Subject"] = "✅ You're in: High-Stakes Wealth Alerts"
    msg["From"] = sender_email
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
        smtp.login(sender_email, sender_password)
        smtp.send_message(msg)

def render_signup_view() -> None:
    st.title("📬 Sign Up for High-Stakes Wealth Alerts")
    st.write("Join our insider list to get:")
    st.markdown("""• 📊 Weekly portfolio summaries  
    • 🔔 Price movement alerts  
    • 🧠 New AI investment picks""")

    with st.form("signup_form", clear_on_submit=True):
        input_name = st.text_input("Your Name")
        input_email = st.text_input("Your Email")
        submitted = st.form_submit_button("Sign Me Up")

        if submitted:
            name = (input_name or "").strip()
            email = (input_email or "").strip()

            if not name or not email:
                st.error("Please fill in both name and email.")
            elif not is_valid_email(email):
                st.error("Please enter a valid email address.")
            else:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    worksheet = get_worksheet()
                    worksheet.append_row([name, email, now])
                except Exception:
                    st.error("We couldn't save your signup right now. Please try again shortly.")
                else:
                    try:
                        send_confirmation_email(name, email)
                    except Exception:
                        st.warning("You're added, but we couldn't send the confirmation email.")
                    else:
                        st.success("✅ You’ve been added and a confirmation email has been sent!")


def render_dashboard_view() -> None:
    st.title("📊 Portfolio Dashboard")
    st.caption("Current breakdown of your portfolio risk allocation")

    labels = ["High-Risk", "Low-Risk"]
    values = [75, 25]
    colors = ["#ff6b6b", "#4dabf7"]

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("High-Risk", "75%")
    metric_col2.metric("Low-Risk", "25%")
    metric_col3.metric("Total", "100%")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Allocation – Donut")
        fig1, ax1 = plt.subplots(figsize=(4, 4))
        ax1.pie(
            values,
            labels=labels,
            colors=colors,
            autopct="%1.0f%%",
            startangle=90,
            wedgeprops=dict(width=0.5),
        )
        ax1.axis("equal")
        st.pyplot(fig1, clear_figure=True)

    with chart_col2:
        st.subheader("Allocation – Bar")
        fig2, ax2 = plt.subplots(figsize=(5, 3))
        ax2.barh(labels, values, color=colors)
        ax2.set_xlim(0, 100)
        ax2.set_xlabel("Percent of Portfolio")
        for index, value in enumerate(values):
            ax2.text(value + 1, index, f"{value}%", va="center")
        st.pyplot(fig2, clear_figure=True)


def main() -> None:
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("View", ("Dashboard", "Sign Up"))

    if page == "Dashboard":
        render_dashboard_view()
    else:
        render_signup_view()


main()
