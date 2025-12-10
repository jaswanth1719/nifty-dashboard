import streamlit as st
import pandas as pd

st.set_page_config(page_title="NIFTY Impact Dashboard", layout="wide")
st.title("📊 NIFTY 50 Impact Dashboard")
st.markdown("---")

@st.cache_data(ttl=0)
def load_data():
    try:
        # Read local CSV (Streamlit Cloud clones the repo, so file is local)
        return pd.read_csv("dashboard_data.csv")
    except:
        return None

df = load_data()

if df is not None:
    # --- SECTION 1: MARKET METRICS ---
    st.subheader("⚡ Market Drivers (1-Day View)")
    col1, col2, col3, col4 = st.columns(4)

    # Filter for non-news items
    metrics = df[~df['Metric'].isin(['News', 'Last Updated'])]
    
    def show_metric(label, col):
        row = metrics[metrics['Metric'] == label]
        if not row.empty:
            val = row.iloc[0]['Value']
            status = row.iloc[0]['Status']
            col.metric(label, val, status)

    show_metric("US Markets (S&P 500)", col1)
    show_metric("Crude Oil", col2)
    show_metric("Global VIX", col3)
    show_metric("📅 Next Weekly Expiry", col4)

    st.markdown("---")

    # --- SECTION 2: NEWS & EVENTS ---
    st.subheader("📰 Latest News & Triggers")
    
    # Filter for News items
    news_items = df[df['Metric'] == 'News']
    
    if not news_items.empty:
        for index, row in news_items.iterrows():
            # Display as a clean card
            st.info(f"**{row['Status']}** | {row['Value']}")
    else:
        st.write("No major headlines fetched.")

    # Footer
    last_update = df[df['Metric'] == 'Last Updated'].iloc[0]['Value']
    st.caption(f"Last Updated: {last_update} IST")
    
    if st.button("🔄 Refresh"):
        st.rerun()

else:
    st.warning("⚠️ Data file not found. Please run the GitHub Action.")
