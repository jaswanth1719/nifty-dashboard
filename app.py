import streamlit as st
import pandas as pd

st.set_page_config(page_title="NIFTY Deep Dive", layout="wide")
st.title("📉 NIFTY 50 Impact Dashboard")
st.markdown("Click on any item to see the **News & Data Sources** used for the calculation.")

@st.cache_data(ttl=0)
def load_data():
    try:
        # Ensure we treat 'Details' as string even if empty
        return pd.read_csv("dashboard_data.csv", dtype={'Details': str})
    except:
        return None

df = load_data()

if df is not None:
    # Styles
    st.markdown("""
    <style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .impact-pos { color: #28a745; }
    .impact-neg { color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    def render_card(container, row):
        """Renders a card with an expander for sources."""
        title = row['Event']
        value = row['Value']
        impact = row['Impact']
        details_raw = str(row['Details']) # Raw string of links
        
        # Color logic
        color = "black"
        if impact in ['Positive', 'Bullish']: color = "green"
        elif impact in ['Negative', 'Bearish', 'Volatile', 'High']: color = "red"
        
        with container:
            st.markdown(f"### {title}")
            st.markdown(f"<span style='font-size: 26px; color: {color}'>{value}</span> ({impact})", unsafe_allow_html=True)
            
            # THE CLICKABLE DROPDOWN
            with st.expander("🔎 View Sources & News"):
                if details_raw and details_raw != "nan":
                    # Split the string '|||' into individual articles
                    articles = details_raw.split("|||")
                    for art in articles:
                        try:
                            # Format: Title|Link|Date
                            parts = art.split("|")
                            if len(parts) >= 2:
                                head = parts[0]
                                link = parts[1]
                                date = parts[2] if len(parts) > 2 else ""
                                st.markdown(f"• [{head}]({link}) \n *{date}*")
                        except:
                            pass
                else:
                    st.caption("No specific news found for this timeframe.")
            st.markdown("---")

    # --- RENDER COLUMNS ---
    
    with col1:
        st.header("⚡ 1 Day")
        for _, row in df[df['Timeframe'] == "1-Day"].iterrows():
            render_card(st, row)

    with col2:
        st.header("📅 7 Days")
        for _, row in df[df['Timeframe'] == "7-Day"].iterrows():
            render_card(st, row)
            
    with col3:
        st.header("🌏 30 Days")
        for _, row in df[df['Timeframe'] == "30-Day"].iterrows():
            render_card(st, row)

    # Footer
    last_update = df[df['Event'] == "Last Updated"].iloc[0]['Value']
    st.caption(f"Last Updated: {last_update} IST")
    
    if st.button("🔄 Refresh Data"):
        st.rerun()

else:
    st.error("Data loading... Please wait or run the GitHub Action.")
