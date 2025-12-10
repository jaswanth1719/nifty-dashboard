import streamlit as st
import pandas as pd

st.set_page_config(page_title="NIFTY Deep Dive", layout="wide")
st.title("📉 NIFTY 50 Impact Dashboard")
st.markdown("Click on any item to see the **News & Data Sources** used for the calculation.")

@st.cache_data(ttl=0)
def load_data():
    try:
        # Read data ensuring 'Details' is read as text
        return pd.read_csv("dashboard_data.csv", dtype={'Details': str})
    except:
        return None

df = load_data()

if df is not None:
    # Custom CSS for styling
    st.markdown("""
    <style>
    .big-font { font-size:20px !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    def render_card(container, row):
        """Renders a card using direct container methods (Fixes TypeError)."""
        title = row['Event']
        value = row['Value']
        impact = row['Impact']
        details_raw = str(row['Details'])
        
        # Color Logic
        color = "black"
        if impact in ['Positive', 'Bullish']: color = "green"
        elif impact in ['Negative', 'Bearish', 'Volatile', 'High']: color = "red"
        
        # 1. Write Headline directly to the container
        container.markdown(f"### {title}")
        container.markdown(f"<span style='font-size: 26px; color: {color}'>{value}</span> ({impact})", unsafe_allow_html=True)
        
        # 2. Create Expander attached to the container
        with container.expander("🔎 View Sources & News"):
            if details_raw and details_raw != "nan":
                articles = details_raw.split("|||")
                for art in articles:
                    try:
                        parts = art.split("|")
                        if len(parts) >= 2:
                            head = parts[0]
                            link = parts[1]
                            date = parts[2] if len(parts) > 2 else ""
                            st.markdown(f"• [{head}]({link}) \n *{date}*")
                    except:
                        pass
            else:
                st.caption("No specific news found.")
        
        container.markdown("---")

    # --- RENDER COLUMNS ---
    
    # 1-DAY COLUMN
    with col1:
        st.header("⚡ 1 Day")
        # Filter data
        day_rows = df[df['Timeframe'] == "1-Day"]
        if not day_rows.empty:
            for _, row in day_rows.iterrows():
                # Pass 'col1' specifically, not 'st'
                render_card(col1, row)
        else:
            st.info("No data available")

    # 7-DAY COLUMN
    with col2:
        st.header("📅 7 Days")
        week_rows = df[df['Timeframe'] == "7-Day"]
        if not week_rows.empty:
            for _, row in week_rows.iterrows():
                render_card(col2, row)

    # 30-DAY COLUMN
    with col3:
        st.header("🌏 30 Days")
        month_rows = df[df['Timeframe'] == "30-Day"]
        if not month_rows.empty:
            for _, row in month_rows.iterrows():
                render_card(col3, row)

    # Footer
    try:
        last_update = df[df['Event'] == "Last Updated"].iloc[0]['Value']
        st.caption(f"Last Updated: {last_update} IST")
    except:
        pass
    
    if st.button("🔄 Refresh Data"):
        st.rerun()

else:
    st.error("Data loading... Please wait or run the GitHub Action.")
