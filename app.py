
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import smtplib
from email.message import EmailMessage
import os
import re
import traceback

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
def get_spreadsheet() -> gspread.models.Spreadsheet:  # type: ignore[valid-type]
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
    return gc.open_by_url(sheet_url)


@st.cache_resource(show_spinner=False)
def get_worksheet() -> gspread.models.Worksheet:
    sh = get_spreadsheet()
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


def _append_error_log_to_file(error_context: str, error: Exception) -> None:
    """Append error details to a local log file as a fallback.

    This function must never raise.
    """
    try:
        logs_path = os.path.join("logs", "error.log")
        os.makedirs(os.path.dirname(logs_path), exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_type = type(error).__name__
        # Keep the file log single-line per entry for easier grepping
        tb = " ".join(traceback.format_exception_only(type(error), error)).strip()
        with open(logs_path, "a", encoding="utf-8") as f:
            f.write(f"{timestamp}\t{error_context}\t{error_type}\t{str(error)}\t{tb}\n")
    except Exception:
        # Final fallback: swallow to avoid surfacing logging issues to users
        pass


def _append_error_log_to_sheets(error_context: str, error: Exception) -> bool:
    """Try to append error details to an 'ErrorLog' worksheet. Returns True on success.

    This function should not raise; it returns False if anything goes wrong.
    """
    try:
        sh = get_spreadsheet()
        try:
            ws = sh.worksheet("ErrorLog")
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title="ErrorLog", rows=100, cols=6)
            ws.append_row(["Timestamp", "Context", "ErrorType", "Message", "Traceback"])

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_type = type(error).__name__
        # Traceback can be long; cap to a reasonable size for a single cell
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        if len(tb) > 25000:
            tb = tb[:25000] + "\n… (truncated)"
        ws.append_row([timestamp, error_context, error_type, str(error), tb])
        return True
    except Exception:
        return False


def log_error(error_context: str, error: Exception, *, skip_sheets: bool = False) -> None:
    """Best-effort error logging to Sheets and/or local file.

    - If skip_sheets is True, only write to file (useful when the Sheets operation failed).
    - Otherwise, attempt Sheets first, then fall back to file.
    """
    try:
        wrote_to_sheets = False
        if not skip_sheets:
            wrote_to_sheets = _append_error_log_to_sheets(error_context, error)
        if not wrote_to_sheets:
            _append_error_log_to_file(error_context, error)
    except Exception:
        # Never let logging raise
        pass

# Streamlit form
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
            except Exception as e:
                log_error("Sheets: append signup row", e, skip_sheets=True)
                st.error("We couldn't save your signup right now. Please try again shortly.")
            else:
                try:
                    send_confirmation_email(name, email)
                except Exception as e:
                    log_error("Email: send confirmation", e)
                    st.warning("You're added, but we couldn't send the confirmation email.")
                else:
                    st.success("✅ You’ve been added and a confirmation email has been sent!")
