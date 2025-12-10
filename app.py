import streamlit as st
import pandas as pd

st.set_page_config(page_title="NIFTY Impact Timeline", layout="wide")

st.title("📉 NIFTY 50 Impact Timeline")
st.markdown("A view of events affecting the market over 1, 7, and 30 days.")

@st.cache_data(ttl=0)
def load_data():
    try:
        return pd.read_csv("dashboard_data.csv")
    except:
        return None

df = load_data()

if df is not None:
    # Create 3 Tabs/Columns for specific timeframes
    col1, col2, col3 = st.columns(3)

    # --- STYLE HELPER ---
    def card(container, title, value, impact, sub_label):
        """Creates a clean visual card for an event"""
        color = "green" if impact in ["Positive", "Bullish"] else "red"
        if impact in ["Info", "Volatile"]: color = "gray"
        
        container.markdown(f"""
        <div style="padding: 15px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 10px;">
            <div style="color: #888; font-size: 12px;">{sub_label}</div>
            <div style="font-size: 18px; font-weight: bold;">{title}</div>
            <div style="font-size: 24px; color: {color};">{value}</div>
            <div style="font-size: 14px; font-weight: bold; color: {color};">{impact} Impact</div>
        </div>
        """, unsafe_allow_html=True)

    # --- 1 DAY COLUMN ---
    with col1:
        st.header("⚡ 1 Day (Tactical)")
        st.caption("Immediate Market Cues")
        day_events = df[df['Timeframe'] == "1-Day"]
        for _, row in day_events.iterrows():
            card(st, row['Event'], row['Value'], row['Impact'], "Global Cue")

    # --- 7 DAY COLUMN ---
    with col2:
        st.header("📅 7 Days (Weekly)")
        st.caption("Expiry & Earnings")
        week_events = df[df['Timeframe'] == "7-Day"]
        for _, row in week_events.iterrows():
            card(st, row['Event'], row['Value'], row['Impact'], "Upcoming Event")

    # --- 30 DAY COLUMN ---
    with col3:
        st.header("🌏 30 Days (Monthly)")
        st.caption("Seasonality & Macro")
        month_events = df[df['Timeframe'] == "30-Day"]
        for _, row in month_events.iterrows():
            card(st, row['Event'], row['Value'], row['Impact'], "Historical Data")

    # Footer
    st.markdown("---")
    last_update = df[df['Event'] == "Last Updated"].iloc[0]['Value']
    st.caption(f"Last Auto-Update: {last_update} IST")
    
    if st.button("🔄 Check for Updates"):
        st.rerun()

else:
    st.error("Data not initialized. Please run the GitHub Action.")
