import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import pytz
from io import StringIO

# ==================== 1. CONFIGURATION ====================
st.set_page_config(
    page_title="NIFTY 50 Pro Dashboard", 
    page_icon="📈", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Persistent Dark Mode Logic ---
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

st.sidebar.button(
    f"Toggle {'Light' if st.session_state.theme == 'dark' else 'Dark'} Mode", 
    on_click=toggle_theme, 
    use_container_width=True
)

# --- CSS Styling ---
if st.session_state.theme == "dark":
    st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .card {
        background-color: #1a1c24;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #00d4ff;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .metric-val { font-size: 24px; font-weight: bold; color: #ffffff; }
    .sub-text { font-size: 14px; color: #a0a0a0; }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #000000; }
    .card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2962ff;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-val { font-size: 24px; font-weight: bold; color: #000000; }
    .sub-text { font-size: 14px; color: #666666; }
    </style>
    """, unsafe_allow_html=True)

st.title("🇮🇳 NIFTY 50 Pro Dashboard")
st.markdown("Live Market Data • FII/DII Flows • Automated Impact Analysis")

# ==================== 2. DATA FUNCTIONS ====================

@st.cache_data(ttl=180)
def get_nifty_chart_data():
    """Fetches 5-min data if market is open, else Daily data."""
    try:
        ticker = yf.Ticker("^NSEI")
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        
        # Fetch Intraday if market hours, else Daily
        if 9 <= now.hour < 16:
            df = ticker.history(period="1d", interval="5m")
        else:
            df = ticker.history(period="1mo", interval="1d")
            
        if df.empty:
            df = ticker.history(period="1mo", interval="1d")

        # Clean Data
        df = df[['Close']].reset_index()
        
        # Standardize Date Column Name
        cols = [c.lower() for c in df.columns]
        if 'datetime' in cols:
            df.rename(columns={'Datetime': 'Date'}, inplace=True)
        elif 'date' in cols:
            df.rename(columns={'Date': 'Date'}, inplace=True)
            
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def get_fii_dii_status():
    try:
        url = "https://archives.nseindia.com/content/equities/FIIDII.csv"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        df = pd.read_csv(StringIO(response.text), skiprows=1)
        latest = df.iloc[0]
        
        date = latest['Date']
        fii = float(str(latest['FII Net (Cr.)']).replace(',', ''))
        dii = float(str(latest['DII Net (Cr.)']).replace(',', ''))
        
        return date, fii, dii
    except:
        return "Offline", 0, 0

@st.cache_data(ttl=300)
def load_impact_data():
    try:
        df = pd.read_csv("dashboard_data.csv")
        df['Details'] = df['Details'].fillna("").astype(str)
        return df
    except:
        return pd.DataFrame()

# ==================== 3. LAYOUT & RENDERING ====================

tab1, tab2, tab3 = st.tabs(["📊 Live Market", "⚡ Impact Drivers", "📥 Export"])

# --- TAB 1: CHART + FII/DII ---
with tab1:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Live NIFTY 50 Performance")
        chart_df = get_nifty_chart_data()
        
        if not chart_df.empty and 'Close' in chart_df.columns:
            # Live Change Calculation
            current_price = chart_df['Close'].iloc[-1]
            prev_price = chart_df['Close'].iloc[0]
            change_pct = ((current_price - prev_price) / prev_price) * 100
            
            color = "green" if change_pct >= 0 else "red"
            st.markdown(f"<h2 style='color: {color}'>{current_price:,.2f} ({change_pct:+.2f}%)</h2>", unsafe_allow_html=True)
            
            # --- CRITICAL FIX IS HERE ---
            # 1. Set Date as Index
            # 2. Select 'Close' column with DOUBLE BRACKETS [['Close']]
            #    This forces pandas to keep it as a DataFrame, not a Series.
            plot_data = chart_df.set_index('Date')[['Close']]
            
            st.line_chart(plot_data, use_container_width=True, height=400)
        else:
            st.warning("Chart data currently unavailable.")

    with col2:
        st.subheader("Institutional Flow")
        fii_date, fii_val, dii_val = get_fii_dii_status()
        
        st.markdown(f"**Date:** {fii_date}")
        st.metric("FII Net", f"₹ {fii_val:,.0f} Cr", delta="Buying" if fii_val > 0 else "Selling")
        st.metric("DII Net", f"₹ {dii_val:,.0f} Cr", delta="Buying" if dii_val > 0 else "Selling")
        st.caption("*Source: NSE Archives*")

# --- TAB 2: IMPACT CARDS ---
with tab2:
    impact_df = load_impact_data()
    
    if not impact_df.empty:
        def render_card(col, row):
            title = row['Event']
            value = row['Value']
            impact = row['Impact']
            news_raw = row['Details']
            
            text_color = "#ffa726" # Orange
            if any(x in impact for x in ['Positive', 'Bullish', 'Low']): text_color = "#66bb6a" # Green
            if any(x in impact for x in ['Negative', 'Bearish', 'High', 'Volatile']): text_color = "#ef5350" # Red
            
            col.markdown(f"""
            <div class="card">
                <div class="sub-text">{title}</div>
                <div class="metric-val" style="color: {text_color};">{value}</div>
                <div style="font-weight: bold; margin-top: 5px;">Impact: {impact}</div>
            </div>
            """, unsafe_allow_html=True)
            
            with col.expander("📰 Read News"):
                if news_raw and len(news_raw) > 5:
                    articles = news_raw.split("|||")
                    for art in articles:
                        parts = art.split("|")
                        if len(parts) >= 2:
                            headline = parts[0]
                            link = parts[1]
                            date = parts[2] if len(parts) > 2 else ""
                            st.markdown(f"• [{headline}]({link})\n  *{date}*")
                else:
                    st.caption("No specific news found.")

        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("### ⚡ 1-Day (Tactical)")
            for _, row in impact_df[impact_df['Timeframe'] == '1-Day'].iterrows():
                render_card(c1, row)
                
        with c2:
            st.markdown("### 📅 7-Day (Weekly)")
            for _, row in impact_df[impact_df['Timeframe'] == '7-Day'].iterrows():
                render_card(c2, row)
                
        with c3:
            st.markdown("### 🌏 30-Day (Macro)")
            for _, row in impact_df[impact_df['Timeframe'] == '30-Day'].iterrows():
                render_card(c3, row)

    else:
        st.info("No impact data found. Please run the backend script.")

# --- TAB 3: EXPORT ---
with tab3:
    if not impact_df.empty:
        csv = impact_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", data=csv, file_name="nifty_impact.csv", mime="text/csv")

# ==================== FOOTER ====================
st.markdown("---")
col_f1, col_f2 = st.columns([4, 1])

with col_f1:
    try:
        last_upd = impact_df[impact_df['Timeframe'] == 'Meta']['Value'].iloc[0]
        st.caption(f"Backend Last Updated: {last_upd} IST")
    except:
        pass

with col_f2:
    if st.button("🔄 Force Refresh"):
        st.cache_data.clear()
        st.rerun()
