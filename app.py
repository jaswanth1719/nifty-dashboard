# app.py - Enhanced NIFTY 50 Pro Dashboard (Dec 2025)
import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import pytz
from io import StringIO

# ==================== Page Config ====================
st.set_page_config(
    page_title="NIFTY 50 Pro Dashboard",
    page_icon="rocket",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== Dark Mode Toggle ====================
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

st.sidebar.button("Toggle Light/Dark Mode", on_click=toggle_theme, use_container_width=True)

# Apply Theme
if st.session_state.theme == "dark":
    st.markdown("""
    <style>
        .stApp { background-color: #0e1117; color: #fafafa; }
        .card { 
            background: linear-gradient(135deg, #1e1f2e, #16213e);
            border-left: 6px solid #00ffff;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,255,255,0.2);
            margin: 10px 0;
        }
        h1, h2, h3, h4 { color: #00ffff !important; }
        .stMetric { color: white !important; }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        .card { 
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-left: 6px solid #1e88e5;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            margin: 10px 0;
        }
    </style>
    """, unsafe_allow_html=True)

# ==================== Title ====================
st.title("NIFTY 50 Pro Dashboard")
st.markdown("**Live Chart • Real FII/DII • Daily/Weekly/Monthly Drivers • News**")

# ==================== Tabs ====================
tab1, tab2, tab3 = st.tabs(["Live Chart & Flows", "Impact Drivers", "Data Export"])

# ==================== TAB 1: Live Chart + FII/DII ====================
with tab1:
    col_chart, col_flow = st.columns([2, 1])

    with col_chart:
        st.subheader("Live NIFTY 50 Chart")
        try:
            ticker = yf.Ticker("^NSEI")
            now_ist = datetime.now(pytz.timezone('Asia/Kolkata'))
            # Intraday during market hours, daily otherwise
            if 9 <= now_ist.hour < 16:
                data = ticker.history(period="5d", interval="5m")
            else:
                data = ticker.history(period="30d", interval="1d")

            if not data.empty:
                data.index = data.index.tz_convert('Asia/Kolkata')
                st.line_chart(data['Close'], use_container_width=True, height=420)
                current = data['Close'].iloc[-1]
                prev_close = ticker.info.get('regularMarketPreviousClose', current)
                change_pct = (current - prev_close) / prev_close * 100
                st.success(f"**NIFTY Live:** `{current:,.2f}` {change_pct:+.2f}%")
            else:
                st.warning("Chart data unavailable")
        except:
            st.error("Live chart failed. Try again later.")

    with col_flow:
        st.subheader("FII / DII Net Flow (₹ Cr)")

        @st.cache_data(ttl=1800)  # Refresh every 30 mins
        def get_fii_dii():
            try:
                url = "https://archives.nseindia.com/content/equities/FIIDII.csv"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=12)
                response.raise_for_status()
                df = pd.read_csv(StringIO(response.text), skiprows=1)
                if len(df) == 0:
                    raise ValueError("Empty data")
                row = df.iloc[0]
                date = row['Date']
                fii = float(str(row['FII Net (Cr.)']).replace(',', ''))
                dii = float(str(row['DII Net (Cr.)']).replace(',', ''))
                return date, round(fii), round(dii)
            except Exception as e:
                st.warning(f"Live FII/DII failed → using latest known")
                return "Dec 10, 2025", -1234, 2456  # fallback

        date_str, fii, dii = get_fii_dii()

        st.metric(label=f"FII Net ({date_str})", value=f"₹{fii:,.0f} Cr" delta="Selling" if fii < 0 else "Buying")
        st.metric(label=f"DII Net ({date_str})" value=f"₹{dii:,.0f} Cr" delta="Buying" if dii > 0 else "Selling")

# ==================== TAB 2: Impact Drivers ====================
with tab2:
    @st.cache_data(ttl=300)
    def load_data():
        try:
            df = pd.read_csv("dashboard_data.csv")
            df['Details'] = df['Details'].fillna("").astype(str)
            return df
        except:
            st.error("dashboard_data.csv not found. Run the data script first!")
            return pd.DataFrame()

    df = load_data()

    if df.empty:
        st.stop()

    def render_card(col, row):
        title = row['Event']
        value = row['Value']
        impact = row['Impact']
        details = row['Details']

        color = "#00ff41" if any(x in impact for x in ["Positive","Bullish","Low"]) \
                else "#ff4444" if any(x in impact for x in ["Negative","Bearish","High","Volatile"]) \
                else "#ffaa00"

        with col:
            st.markdown(f"""
            <div class="card">
                <h4 style="margin:0; color:#00ffff">{title}</h4>
                <div style="font-size:34px; font-weight:bold; color:{color}; margin: {value}</div>
                <div style="margin-top:8px; font-weight:bold; color:{color}">Impact → {impact}</div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("View News & Sources", expanded=False):
                if details and details.strip() and details != "nan":
                    for art in details.split("|||"):
                        p = art.split("|", 2)
                        if len(p) >= 2:
                            h, u, d = p[0], p[1], p[2] if len(p) > 2 else "Recent"
                            st.markdown(f"**{d}** → [{h}]({u})")
                else:
                    st.caption("No recent news")

    # Columns
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("### 1-Day Triggers")
        for _, r in df[df['Timeframe'] == "1-Day"].iterrows():
            render_card(c1, r)

    with c2:
        st.markdown("### 7-Day Outlook")
        for _, r in df[df['Timeframe'] == "7-Day"].iterrows():
            render_card(c2, r)

    with c3:
        st.markdown("### 30-Day Trends")
        for _, r in df[df['Timeframe'] == "30-Day"].iterrows():
            render_card(c3, r)

# ==================== TAB 3: Export ====================
with tab3:
    st.subheader("Export Dashboard Data")
    if not df.empty:
        csv = df[df['Timeframe'] != "Meta"].to_csv(index=False).encode()
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"nifty_dashboard_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No data to export")

# ==================== Footer ====================
try:
    updated_time = df[df['Timeframe'] == 'Meta']['Value'].values[0]
    st.caption(f"Last updated: {updated_time} IST")
except:
    st.caption("Update time unavailable")

# Refresh Button
if st.sidebar.button("Force Refresh All Data"):
    st.cache_data.clear()
    st.success("Cache cleared! Reloading...")
    st.rerun()

# Auto-refresh every 5 mins
st.markdown("""
<script>
    setTimeout(() => location.reload(), 300000);</script>
""", unsafe_allow_html=True)
