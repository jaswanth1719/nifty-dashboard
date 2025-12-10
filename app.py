import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import pytz

# Page Config
st.set_page_config(page_title="Enhanced NIFTY Dashboard", layout="wide", page_icon="📊")

# Dark Mode Toggle
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

st.sidebar.button("Toggle Light/Dark Mode", on_click=toggle_theme)

# Apply Theme
theme_css = """
<style>
    .card { padding: 18px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 16px; }
</style>
"""
if st.session_state.theme == "dark":
    theme_css += "<style>.stApp { background-color: #0e1117; color: #fafafa; } .card { background: #1a1f2e; border-left: 6px solid #00d4ff; }</style>"
else:
    theme_css += "<style>.card { background: #f8f9fa; border-left: 6px solid #1e88e5; }</style>"
st.markdown(theme_css, unsafe_allow_html=True)

st.title("Enhanced NIFTY 50 Impact Dashboard")
st.markdown("**Real-time impacts on NIFTY: Daily, Weekly, Monthly • Expanded Events • Live Chart & Flows**")

# Tabs for Navigation
tab1, tab2, tab3 = st.tabs(["📈 Live Chart & Flows", "⚡ Impacts", "📥 Export"])

with tab1:
    # Live Chart (unchanged)
    st.subheader("Live NIFTY 50 Chart")
    try:
        nifty = yf.Ticker("^NSEI")
        now_ist = datetime.now(pytz.timezone('Asia/Kolkata'))
        interval = "5m" if 9 <= now_ist.hour < 16 else "1d"
        data = nifty.history(period="5d", interval=interval)
        if not data.empty:
            data.index = data.index.tz_convert('Asia/Kolkata')
            st.line_chart(data['Close'], height=400)
            current = data['Close'].iloc[-1]
            prev = nifty.info.get('regularMarketPreviousClose', current)
            change = (current - prev) / prev * 100
            st.markdown(f"**Current:** {current:,.2f} ({change:+.2f}%)")
    except:
        st.warning("Chart unavailable")

    # FII/DII (unchanged)
    st.subheader("FII/DII Net Flows (₹ Cr)")
    @st.cache_data(ttl=3600)
    def get_fii_dii():
        try:
            url = "https://archives.nseindia.com/content/equities/FIIDII.csv"
            df = pd.read_csv(url, skiprows=1)
            row = df.iloc[0]
            date = row['Date']
            fii = float(str(row['FII Net (Cr.)']).replace(',', ''))
            dii = float(str(row['DII Net (Cr.)']).replace(',', ''))
            return date, fii, dii
        except:
            return "Latest", 0, 0
    date, fii, dii = get_fii_dii()
    col1, col2 = st.columns(2)
    col1.metric("FII Net", f"₹{fii:,.0f}", "Selling" if fii < 0 else "Buying")
    col2.metric("DII Net", f"₹{dii:,.0f}", "Buying" if dii > 0 else "Selling")

with tab2:
    # Load Data
    @st.cache_data(ttl=180)
    def load_data():
        try:
            return pd.read_csv("dashboard_data.csv", dtype={'Details': str}).fillna("")
        except:
            return pd.DataFrame()
    df = load_data()

    # Render Card (with tooltips)
    def render_card(col, row):
        title = row['Event']
        value = row['Value']
        impact = row['Impact']
        details = row['Details']
        color = "#00C853" if "Positive" in impact or "Bullish" in impact or "Low" in impact else "#D50000" if "Negative" in impact or "Bearish" in impact or "High" in impact else "#FF9800"
        with col:
            st.markdown(f'<div class="card"><h4>{title}</h4><div style="font-size:32px; color:{color}">{value}</div><div style="color:{color}">Impact: {impact}</div></div>', unsafe_allow_html=True)
            with st.expander("News & Details"):
                if details:
                    for art in details.split("|||"):
                        parts = art.split("|", 2)
                        if len(parts) >= 2:
                            st.markdown(f"• [{parts[0]}]({parts[1]}) ({parts[2] if len(parts)>2 else ''})")
                else:
                    st.caption("No details")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("1-Day Impacts")
        for _, r in df[df['Timeframe'] == "1-Day"].iterrows():
            render_card(col1, r)
    with col2:
        st.subheader("7-Day Impacts")
        for _, r in df[df['Timeframe'] == "7-Day"].iterrows():
            render_card(col2, r)
    with col3:
        st.subheader("30-Day Impacts")
        for _, r in df[df['Timeframe'] == "30-Day"].iterrows():
            render_card(col3, r)

with tab3:
    st.subheader("Export Data")
    st.download_button("Download CSV", df.to_csv(index=False), "nifty_impacts.csv")

# Footer
try:
    updated = df[df['Timeframe'] == 'Meta']['Value'].iloc[0]
    st.caption(f"Updated: {updated} IST")
except:
    pass
if st.sidebar.button("Refresh"):
    st.cache_data.clear()
    st.rerun()
