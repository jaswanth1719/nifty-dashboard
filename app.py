import streamlit as st
import pandas as pd
import os
from update_data import build_data

st.set_page_config(page_title="NIFTY Impact Dashboard", layout="wide", page_icon="Chart Increasing")

# Auto-refresh every 8 minutes
st.markdown("<meta http-equiv='refresh' content='480'>", unsafe_allow_html=True)

st.title("NIFTY 50 Real-Time Impact Dashboard")
st.markdown("**Live drivers • Events • News • Expiry • RBI • FOMC**")

@st.cache_data(ttl=300)
def load_data():
    if not os.path.exists("dashboard_data.csv"):
        df = build_data()
    else:
        df = pd.read_csv("dashboard_data.csv")
        df['Details'] = df['Details'].fillna("")  # Fix NaN to empty string
    return df

if st.sidebar.button("Force Refresh Now"):
    with st.spinner("Updating..."):
        build_data()
    st.success("Refreshed!")
    st.rerun()

df = load_data()

# Display in columns
col1, col2, col3 = st.columns(3)

for _, row in df.iterrows():
    timeframe = row["Timeframe"]
    if timeframe == "1-Day":
        col = col1
    elif timeframe in ["7-Day", "Upcoming", "Ongoing"]:
        col = col2
    else:
        col = col3

    with col:
        impact = row["Impact"]
        color = {"Bullish":"🟢","Bearish":"🔴","Neutral":"⚪","High Volatility":"🟠","Very High":"🔴","Calm":"🟢"}.get(impact, "⚪")
        st.markdown(f"#### {color} {row['Event']}")
        st.markdown(f"**{row['Value']}**")
        st.caption(f"Impact: {impact}")
        details = row["Details"]
        if details and "unavailable" not in details:
            with st.expander("News"):
                for art in details.split("|||")[:3]:
                    if "|" in art:
                        parts = art.split("|")
                        title = parts[0]
                        link = parts[1] if len(parts) > 1 else ""
                        st.markdown(f"• [{title}]({link})")

st.caption("Auto-refreshes every 8 min • Data: Yahoo Finance + Google News")
