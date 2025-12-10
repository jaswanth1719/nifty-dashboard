import streamlit as st
import pandas as pd

# 1. Configuration
st.set_page_config(
    page_title="NIFTY Impact Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 NIFTY 50 Impact Dashboard")
st.markdown("---")

# 2. Load Data Function (With Cache Control)
# We use ttl=0 to ensure it reloads the CSV every time someone refreshes the app
@st.cache_data(ttl=0)
def load_data():
    # REPLACE WITH YOUR RAW URL
    # Format: https://raw.githubusercontent.com/[YOUR_USERNAME]/[REPO_NAME]/main/dashboard_data.csv
    # But since the file is local to the repo when deployed on Streamlit, we can just read it locally!
    try:
        return pd.read_csv("dashboard_data.csv")
    except FileNotFoundError:
        return None

df = load_data()

if df is not None:
    # 3. Layout
    col1, col2, col3, col4 = st.columns(4)

    # Helper to extract values safely
    def get_stat(metric_name):
        row = df[df['Metric'] == metric_name]
        if not row.empty:
            return row.iloc[0]['Value'], row.iloc[0]['Status']
        return "N/A", "N/A"

    # Display Metrics
    with col1:
        val, status = get_stat("US Markets (S&P 500)")
        st.metric("🇺🇸 US Markets", val, delta=None, help="S&P 500 Overnight Change")
        if status == "Bullish": st.success("Positive Cue")
        else: st.error("Negative Cue")

    with col2:
        val, status = get_stat("Crude Oil")
        st.metric("🛢️ Crude Oil", val, delta=None)
        # Oil logic is inverse: Rising oil is bad (Bearish) for India
        if status == "Bearish": st.error("Negative Impact") # Oil UP = Bad
        else: st.success("Positive Impact") # Oil DOWN = Good

    with col3:
        val, status = get_stat("Global VIX")
        st.metric("📉 Global VIX", val)
        if status == "Volatile": st.warning("High Volatility")
        else: st.info("Stable")

    with col4:
        val, status = get_stat("Last Updated (IST)")
        st.metric("🕒 Updated At", val.split(" ")[1]) # Show time only
        st.caption(val.split(" ")[0]) # Show date below

    # 4. Refresh Button
    if st.button("🔄 Refresh Data"):
        st.rerun()

else:
    st.warning("⚠️ Data file not found. Please ensure the GitHub Action has run successfully.")
