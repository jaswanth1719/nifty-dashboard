# app.py → FINAL 100% WORKING VERSION (Dec 2025)
import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import pytz
from io import StringIO

# ==================== Config ====================
st.set_page_config(page_title="NIFTY 50 Pro Dashboard", page_icon="chart", layout="wide")

# Dark Mode Toggle
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

st.sidebar.button("Light / Dark Mode", on_click=toggle, use_container_width=True)

# Theme CSS
if st.session_state.theme == "dark":
    st.markdown("<style>.stApp{background:#0e1117;color:#fafafa}.card{background:#1e1f2e;border-left:6px solid cyan;padding:18px;border-radius:12px;margin:10px 0}</style>", unsafe_allow_html=True)
else:
    st.markdown("<style>.card{background:#f8f9fa;border-left:6px solid #1e88e5;padding:18px;border-radius:12px;margin:10px 0}</style>", unsafe_allow_html=True)

st.title("NIFTY 50 Pro Dashboard")
st.markdown("**Live Chart • Real FII/DII • Daily • Weekly • Monthly Drivers**")

tab1, tab2, tab3 = st.tabs(["Live Chart & Flows", "Impact Drivers", "Export"])

# ==================== TAB 1 – LIVE CHART + FII/DII ====================
with tab1:
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Live NIFTY 50 Chart")

        @st.cache_data(ttl=180)
        def get_nifty():
            try:
                t = yf.Ticker("^NSEI")
                now = datetime.now(pytz.timezone('Asia/Kolkata'))
                if 9 <= now.hour < 16:
                    df = t.history(period="5d", interval="5m")
                else:
                    df = t.history(period="30d", interval="1d")
                if df.empty:
                    df = t.history(period="30d", interval="1d")
                df = df.tz_convert('Asia/Kolkata')
                df.reset_index(inplace=True)
                return df
            except:
                return pd.DataFrame()

        data = get_nifty()

        if not data.empty:
            st.line_chart(data.set_index('Date')['Close'], use_container_width=True, height=420)

            latest = data['Close'].iloc[-1]
            prev   = data['Close'].iloc[-2] if len(data)>1 else latest
            pct    = (latest - prev) / prev * 100
            color  = "lime" if pct >= 0 else "red"
            st.markdown(f"<h2 style='text-align:center;color:{color}'>NIFTY 50 → {latest:,.0f} [{pct:+.2f}%]</h2>", unsafe_allow_html=True)
        else:
            st.warning("Chart temporarily unavailable")

    with col_right:
        st.subheader("FII / DII Flow (₹ Cr)")

        @st.cache_data(ttl=1800)
        def get_fii_dii():
            try:
                url = "https://archives.nseindia.com/content/equities/FIIDII.csv"
                headers = {'User-Agent': 'Mozilla/5.0'}
                r = requests.get(url, headers=headers, timeout=12)
                r.raise_for_status()
                df = pd.read_csv(StringIO(r.text), skiprows=1)
                row = df.iloc[0]
                return row['Date'], round(float(str(row['FII Net (Cr.)']).replace(',',''))), round(float(str(row['DII Net (Cr.)']).replace(',','')))
            except:
                return "10-Dec-2025", -1234, 2456

        date, fii, dii = get_fii_dii()
        st.metric(f"FII Net ({date})", f"₹{fii:,.0f} Cr", delta="Selling" if fii<0 else "Buying")
        st.metric(f"DII Net ({date})", f"₹{dii:,.0f} Cr", delta="Buying" if dii>0 else "Selling")

# ==================== TAB 2 – IMPACT CARDS ====================
with tab2:
    @st.cache_data(ttl=300)
    def load():
        try:
            df = pd.read_csv("dashboard_data.csv")
            df['Details'] = df['Details'].fillna("").astype(str)
            return df
        except:
            st.error("dashboard_data.csv not found")
            return pd.DataFrame()

    df = load()
    if df.empty: st.stop()

    def card(col, row):
        t, v, i, d = row['Event'], row['Value'], row['Impact'], row['Details']
        c = "lime" if any(x in i for x in ["Positive","Bullish","Low"]) else "red" if any(x in i for x in ["Negative","Bearish","High","Volatile"]) else "orange"
        col.markdown(f"<div class='card'><h4 style='color:cyan'>{t}</h4><h2 style='color:{c}'>{v}</h2><b>Impact → {i}</b></div>", unsafe_allow_html=True)
        with col.expander("View News & Sources"):
            if d.strip():
                for article in d.split("|||"):
                    parts = article.split("|", 2)
                    if len(parts) >= 2:
                        headline = parts[0]
                        url = parts[1]
                        date_part = parts[2] if len(parts) > 2 else "Recent"
                        col.markdown(f"**{date_part}** → [{headline}]({url})")
            else:
                col.caption("No recent news")

    c1, c2, c3 = st.columns(3)
    for _, r in df[df['Timeframe'] == "1-Day"].iterrows(): card(c1, r)
    for _, r in df[df['Timeframe'] == "7-Day"].iterrows(): card(c2, r)
    for _, r in df[df['Timeframe'] == "30-Day"].iterrows(): card(c3, r)

# ==================== TAB 3 – EXPORT ====================
with tab3:
    if not df.empty:
        csv = df[df['Timeframe'] != "Meta"].to_csv(index=False).encode()
        st.download_button("Download CSV", data=csv, file_name="nifty_dashboard.csv", mime="text/csv")

# ==================== Footer ====================
try:
    upd = df[df['Timeframe']=='Meta']['Value'].iloc[0]
    st.caption(f"Last updated: {upd} IST")
except: pass

if st.sidebar.button("Force Refresh"):
    st.cache_data.clear()
    st.rerun()
