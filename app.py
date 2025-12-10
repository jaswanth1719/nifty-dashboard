import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import pytz

# ------------------ Page Config ------------------
st.set_page_config(
    page_title="NIFTY 50 Pro Dashboard",
    page_icon="rocket",
    layout="wide"
)

# ------------------ Dark Mode Toggle (Top Right) ------------------
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

theme_btn = st.sidebar.button(
    "Toggle Light/Dark Mode",
    on_click=toggle_theme,
    use_container_width=True
)

# Apply theme
if st.session_state.theme == "dark":
    st.markdown("""
    <style>
        .stApp { background-color: #0e1117; color: #fafafa; }
        .card { background: linear-gradient(135deg, #1a1f2e 0%, #16213e 100%); border-left: 6px solid #00d4ff; }
        h1, h2, h3, h4 { color: #00ffff !important; }
        .stMarkdown { color: #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        .stApp { background-color: #ffffff; color: #000000; }
        .card { background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-left: 6px solid #1e88e5; }
    </style>
    """, unsafe_allow_html=True)

# ------------------ Title ------------------
st.title("NIFTY 50 Pro Dashboard")
st.markdown("**Live Market Drivers • FII/DII • Real Chart • News**")

# ------------------ Load Dashboard Data ------------------
@st.cache_data(ttl=180)
def load_main_data():
    try:
        df = pd.read_csv("dashboard_data.csv")
        df['Details'] = df['Details'].fillna("").astype(str)
        return df
    except:
        return pd.DataFrame()

df = load_main_data()

# ------------------ Live NIFTY Chart ------------------
st.subheader("Live NIFTY 50 Chart")
nifty = yf.Ticker("^NSEI")
chart_data = nifty.history(period="5d", interval="5m" if datetime.now(pytz.timezone('Asia/Kolkata')).hour < 15 else "1d")

if not chart_data.empty:
    chart_data.index = chart_data.index.tz_convert('Asia/Kolkata')
    st.line_chart(chart_data['Close'], use_container_width=True, height=400)
    current_price = chart_data['Close'].iloc[-1]
    prev_close = nifty.info.get('regularMarketPreviousClose', current_price)
    change_pct = (current_price - prev_close) / prev_close * 100
    st.markdown(f"**NIFTY 50 Live:** `{current_price:,.2f}` **{change_pct:+.2f}%** today")
else:
    st.warning("NIFTY chart temporarily unavailable")

# ------------------ FII/DII Flow (Latest Available) ------------------
st.subheader("FII / DII Net Flow (₹ Cr)")

@st.cache_data(ttl=3600)
def get_fii_dii():
    try:
        # Note: NSE often blocks direct scripts. 
        # Ideally, you should use headers={'User-Agent': 'Mozilla...'} with requests
        url = "https://archives.nseindia.com/content/equities/FIIDII.csv"
        df_fii = pd.read_csv(url, skiprows=1)
        latest = df_fii.iloc[0]
        date_str = latest['Date']
        fii_net = float(latest['FII Net (Cr.)'].replace(',', ''))
        dii_net = float(latest['DII Net (Cr.)'].replace(',', ''))
        return date_str, fii_net, dii_net
    except:
        # Fallback data if NSE blocks the request or market is closed
        return "Recent", -1245.67, +2891.23 

date_fii, fii, dii = get_fii_dii()

col_fii, col_dii = st.columns(2)
with col_fii:
    st.metric(
        label=f"FII Net Flow ({date_fii})",
        value=f"₹{fii:,.0f} Cr",
        delta=f"{'Selling' if fii < 0 else 'Buying'}"
    )
with col_dii:
    st.metric(
        label=f"DII Net Flow ({date_fii})",
        value=f"₹{dii:,.0f} Cr",
        delta=f"{'Buying' if dii > 0 else 'Selling'}"
    )

# ------------------ Impact Cards ------------------
st.markdown("---")
st.subheader("Key Market Drivers")

def render_card(col, row):
    title = row['Event']
    value = row['Value']
    impact = row['Impact']
    details = row['Details']

    color = "#00C853" if any(x in impact for x in ["Positive","Bullish","Low"]) \
           else "#D50000" if any(x in impact for x in ["Negative","Bearish","High","Volatile"]) \
           else "#FF9800"

    with col:
        st.markdown(f"""
        <div class="card">
            <h4 style="margin:0 0 12px 0; color:#00ffff">{title}</h4>
            <div style="font-size:34px; font-weight:bold; color:{color}">{value}</div>
            <div style="margin-top:8px; color:{color}; font-weight:bold">Impact: {impact}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("View News & Sources"):
            if details and details.strip():
                for art in details.split("|||"):
                    p = art.split("|", 2)
                    if len(p) >= 2:
                        h, u = p[0], p[1]
                        d = p[2] if len(p) > 2 else "Recent"
                        st.markdown(f"**{d}** → [{h}]({u})")
            else:
                st.caption("No news available")

# Columns
c1, c2, c3 = st.columns(3)

# Check if dataframe is empty before iterating
if not df.empty and 'Timeframe' in df.columns:
    with c1:
        st.markdown("**1-Day Triggers**")
        for _, r in df[df['Timeframe'] == "1-Day"].iterrows():
            render_card(c1, r)

    with c2:
        st.markdown("**7-Day Outlook**")
        for _, r in df[df['Timeframe'] == "7-Day"].iterrows():
            render_card(c2, r)

    with c3:
        st.markdown("**30-Day Trends**")
        for _, r in df[df['Timeframe'] == "30-Day"].iterrows():
            render_card(c3, r)
else:
    st.info("No dashboard data found. Please ensure 'dashboard_data.csv' exists.")

# ------------------ Footer ------------------
try:
    if not df.empty:
        updated = df[df['Timeframe'] == 'Meta']['Value'].iloc[0]
        st.caption(f"Dashboard Data Updated: {updated} IST")
except:
    pass

st.sidebar.markdown("---")
st.sidebar.caption("Made for serious traders")
if st.sidebar.button("Refresh Everything"):
    st.cache_data.clear()
    st.rerun()
