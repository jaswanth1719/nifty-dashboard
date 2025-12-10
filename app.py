import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import pytz

# ==================== Page Config ====================
st.set_page_config(
    page_title="NIFTY 50 Pro Dashboard",
    page_icon="rocket",
    layout="wide"
)

# ==================== Dark Mode Toggle ====================
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

st.sidebar.button("Toggle Light / Dark Mode", on_click=toggle_theme, use_container_width=True)

# Apply theme
if st.session_state.theme == "dark":
    st.markdown("""
    <style>
        .stApp { background-color: #0e1117; color: #fafafa; }
        .card { 
            background: linear-gradient(135deg, #1a1f2e 0%, #16213e 100%);
            border-left: 6px solid #00d4ff; 
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            margin-bottom: 16px;
        }
        h1, h2, h3, h4 { color: #00ffff !important; }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        .card { 
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-left: 6px solid #1e88e5; 
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            margin-bottom: 16px;
        }
    </style>
    """, unsafe_allow_html=True)

# ==================== Title ====================
st.title("NIFTY 50 Pro Dashboard")
st.markdown("**Live Chart • FII/DII • Key Drivers • News**")

# ==================== Load Main Dashboard Data ====================
@st.cache_data(ttl=180)
def load_main_data():
    try:
        df = pd.read_csv("dashboard_data.csv")
        df['Details'] = df['Details'].fillna("").astype(str)
        return df
    except Exception as e:
        st.error(f"Could not load dashboard_data.csv → {e}")
        return pd.DataFrame()

df = load_main_data()

# ==================== Live NIFTY Chart ====================
st.subheader("Live NIFTY 50 Chart")
try:
    nifty = yf.Ticker("^NSEI")
    # Use intraday when market hours, otherwise daily
    now_ist = datetime.now(pytz.timezone('Asia/Kolkata'))
    if 9 <= now_ist.hour < 16:
        data = nifty.history(period="5d", interval="5m")
    else:
        data = nifty.history(period="30d", interval="1d")

    if not data.empty:
        data.index = data.index.tz_convert('Asia/Kolkata')
        st.line_chart(data['Close'], use_container_width=True, height=400)
        current = data['Close'].iloc[-1]
        prev = nifty.info.get('regularMarketPreviousClose', current)
        change_pct = (current - prev) / prev * 100
        st.markdown(f"**NIFTY Live:** `{current:,.2f}` **{change_pct:+.2f}%**")
except:
    st.warning("Live chart temporarily unavailable")

# ==================== FII / DII Flow ====================
st.subheader("Latest FII / DII Net Flow (₹ Cr)")

@st.cache_data(ttl=3600)
def get_fii_dii():
    try:
        url = "https://archives.nseindia.com/content/equities/FIIDII.csv"
        df_fii = pd.read_csv(url, skiprows=1)
        row = df_fii.iloc[0]
        date_str = row['Date']
        fii = float(str(row['FII Net (Cr.)']).replace(',', ''))
        dii = float(str(row['DII Net (Cr.)']).replace(',', ''))
        return date_str, fii, dii
    except Exception:
        return "Latest", -1245.67, 2891.23   # fallback values

date_fii, fii_net, dii_net = get_fii_dii()

c1, c2 = st.columns(2)
with c1:
    st.metric("FII Net", f"₹{fii_net:,.0f} Cr", delta="Selling" if fii_net < 0 else "Buying")
with c2:
    st.metric("DII Net", f"₹{dii_net:,.0f} Cr", delta="Buying" if dii_net > 0 else "Selling")

# ==================== Impact Cards ====================
st.markdown("---")
st.subheader("Key Market Drivers")

def render_card(col, row):
    title   = row['Event']
    value   = row['Value']
    impact  = row['Impact']
    details = row['Details']

    if any(x in impact for x in ["Positive","Bullish","Low"]):
        color = "#00C853"
    elif any(x in impact for x in ["Negative","Bearish","High","Volatile"]):
        color = "#D50000"
    else:
        color = "#FF9800"

    with col:
        st.markdown(f"""
        <div class="card">
            <h4 style="margin:0 0 12px 0; color:#00ffff">{title}</h4>
            <div style="font-size:34px; font-weight:bold; color:{color}">{value}</div>
            <div style="margin-top:8px; font-weight:bold; color:{color}">Impact: {impact}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("View News & Sources"):
            if details and details.strip():
                for art in details.split("|||"):
                    parts = art.split("|", 2)
                    if len(parts) >= 2:
                        headline, url = parts[0], parts[1]
                        date = parts[2] if len(parts) > 2 else "Recent"
                        st.markdown(f"**{date}** → [{headline}]({url})")
            else:
                st.caption("No recent news")

# Layout
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**1-Day Triggers**")
    for _, r in df[df['Timeframe'] == "1-Day"].iterrows():
        render_card(col1, r)

with col2:
    st.markdown("**7-Day Outlook**")
    for _, r in df[df['Timeframe'] == "7-Day"].iterrows():
        render_card(col2, r)

with col3:
    st.markdown("**30-Day Trends**")
    for _, r in df[df['Timeframe'] == "30-Day"].iterrows():
        render_card(col3, r)

# ==================== Footer ====================
try:
    updated = df[df['Timeframe'] == 'Meta']['Value'].iloc[0]
    st.caption(f"Dashboard last updated: {updated} IST")
except:
    pass

# Refresh button
if st.sidebar.button("Force Refresh All Data"):
    st.cache_data.clear()
    st.rerun()
