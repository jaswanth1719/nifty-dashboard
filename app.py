import streamlit as st
import pandas as pd
import os
from datetime import datetime
import pytz

# --- Import the data generator ---
try:
    from update_data import build_data
except ImportError:
    st.error("`update_data.py` not found in the same folder!")
    st.stop()

# ==================== Page Config ====================
st.set_page_config(
    page_title="NIFTY 50 Impact Dashboard",
    page_icon="Chart Increasing",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== Auto-Refresh Every 8 Minutes ====================
st.markdown("""
<script>
    const interval = 8 * 60 * 1000;  // 8 minutes
    setTimeout(() => location.reload(), interval);
</script>
""", unsafe_allow_html=True)

# ==================== Custom CSS – Dark & Light Mode ====================
def load_css():
    if st.session_state.get("theme", "dark") == "dark":
        st.markdown("""
        <style>
            .stApp { background: #0e1117; color: #fafafa; }
            .big-font { font-size: 48px !important; font-weight: bold; }
            .impact-badge {
                padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 14px;
            }
            .bullish   { background: #1b5e20; color: #b9f6ca; }
            .bearish   { background: #7f0000; color: #ff8a80; }
            .neutral   { background: #3d5afe; color: #c5cae9; }
            .volatile  { background: #e65100; color: #ffcc80; }
            .card {
                background: linear-gradient(135deg, #16213e, #1a1f2e);
                border-left: 6px solid #00d4ff;
                border-radius: 16px;
                padding: 20px;
                box-shadow: 0 8px 20px rgba(0,0,0,0.5);
                margin: 12px 0;
                transition: transform 0.2s;
            }
            .card:hover { transform: translateY(-4px); }
            .news-link { color: #80deea !important; }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            .stApp { background: #f8f9fa; }
            .card {
                background: white;
                border-left: 6px solid #1976d2;
                border-radius: 16px;
                padding: 20px;
                box-shadow: 0 6px 16px rgba(0,0,0,0.1);
                margin: 12px 0;
            }
            .impact-badge {
                padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 14px;
            }
            .bullish   { background: #e8f5e8; color: #2e7d32; }
            .bearish   { background: #ffebee; color: #c62828; }
            .neutral   { background: #e3f2fd; color: #1565c0; }
            .volatile  { background: #fff3e0; color: #ef6c00; }
        </style>
        """, unsafe_allow_html=True)

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# Sidebar Theme Toggle
with st.sidebar:
    st.markdown("### Settings")
    if st.button("Light / Dark Mode", use_container_width=True):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()

load_css()

# ==================== Data Management ====================
@st.cache_data(ttl=300)  # Cache 5 mins
def get_data():
    if not os.path.exists("dashboard_data.csv"):
        return build_and_save()
    try:
        df = pd.read_csv("dashboard_data.csv")
        # Parse last update time
        meta_row = df[df['Timeframe'] == 'Meta']
        if not meta_row.empty:
            last_update = meta_row['Value'].iloc[0]
        else:
            last_update = "Unknown"
        return df, last_update
    except:
        return build_and_save()

def build_and_save():
    with st.spinner("Fetching latest market data & news..."):
        new_df = build_data()
    return new_df, datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%b %d, %H:%M IST')

# Force Refresh Button
if st.sidebar.button("Force Refresh Now", type="primary", use_container_width=True):
    df, last_update = build_and_save()
    st.cache_data.clear()
    st.success("Data refreshed!")
    st.rerun()
else:
    df, last_update = get_data()

# ==================== Header ====================
col_title, col_update = st.columns([3,1])
with col_title:
    st.markdown("# NIFTY 50 Impact Dashboard")
    st.markdown("**Real-time drivers • News • Seasonality • Expiry**")
with col_update:
    st.markdown(f"**Last Update**  \n{last_update}")

st.markdown("---")

# ==================== Render Impact Cards ====================
def get_badge_class(impact):
    impact = str(impact).lower()
    if any(x in impact for x in ["bullish", "positive", "calm", "low"]):
        return "bullish"
    elif any(x in impact for x in ["bearish", "negative", "fear"]):
        return "bearish"
    elif any(x in impact for x in ["volatile", "high volatility"]):
        return "volatile"
    else:
        return "neutral"

def render_card(row):
    event = row['Event']
    value = row['Value']
    impact = row['Impact']
    details = row['Details']

    badge = get_badge_class(impact)

    st.markdown(f"""
    <div class="card">
        <h3 style="margin:0 0 8px0; color:#00ffff;">{event}</h3>
        <div class="big-font" style="margin:10px 0; color:{'#00ff9d' if 'bull' in badge else '#ff5252' if 'bear' in badge else '#ff9800'}">
            {value}
        </div>
        <span class="impact-badge {badge}">{impact}</span>
    </div>
    """, unsafe_allow_html=True)

    if details and details.strip() and details != "No recent news":
        with st.expander("Latest News & Analysis", expanded=False):
            for article in details.split("|||"):
                if "|" not in article:
                    continue
                title, link, date = article.split("|", 2)
                st.markdown(f"**{date}** • [{title}]({link})", unsafe_allow_html=True)
    else:
        with st.expander("Latest News & Analysis"):
            st.caption("No recent news available.")

# ==================== Layout: 3 Columns ====================
if not df.empty:
    col1, col2, col3 = st.columns([1,1,1])

    # 1-Day Triggers
    with col1:
        st.subheader("1-Day Triggers")
        for _, row in df[df['Timeframe'] == '1-Day'].iterrows():
            render_card(row)

    # 7-Day Outlook
    with col2:
        st.subheader("7-Day Outlook")
        for _, row in df[df['Timeframe'] == '7-Day'].iterrows():
            render_card(row)
        # Also show Upcoming Events
        upcoming = df[df['Timeframe'] == 'Upcoming']
        if not upcoming.empty:
            st.markdown("#### Upcoming Events")
            for _, row in upcoming.iterrows():
                render_card(row)

    # 30-Day Trends
    with col3:
        st.subheader("30-Day Trends")
        for _, row in df[df['Timeframe'].isin(['30-Day', 'Upcoming'])].iterrows():
            render_card(row)

    # Footer
    st.markdown("---")
    st.caption("Data from Yahoo Finance • Google News • NSE | Auto-refreshes every 8 minutes | Made with Streamlit")

else:
    st.error("No data available. Please click 'Force Refresh Now' in the sidebar.")
