import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import os

# --- IMPORT YOUR DATA GENERATOR ---
# UPDATED: Now importing from 'update_data.py'
try:
    from update_data import build_data
except ImportError:
    st.error("Could not find 'update_data.py'. Make sure it is in the same folder as this app.")

# ==================== Page Config ====================
st.set_page_config(page_title="NIFTY 50 Pro Dashboard", page_icon="rocket", layout="wide")

# ==================== Theme Setup ====================
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

st.sidebar.button("Toggle Light / Dark Mode", on_click=toggle_theme, use_container_width=True)

if st.session_state.theme == "dark":
    st.markdown("""
    <style>
        .stApp { background-color: #0e1117; color: #fafafa; }
        .card { 
            background: linear-gradient(135deg, #1a1f2e 0%, #16213e 100%);
            border-left: 6px solid #00d4ff; 
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            margin-bottom: 16px;
        }
        h1, h2, h3, h4 { color: #00ffff !important; }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        .card { 
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-left: 6px solid #1e88e5; 
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            margin-bottom: 16px;
        }
    </style>
    """, unsafe_allow_html=True)

# ==================== Main Data Loader ====================
def load_data():
    """Loads CSV. If missing, generates it using update_data.py."""
    if not os.path.exists("dashboard_data.csv"):
        with st.spinner("Generating initial data..."):
            try:
                df = build_data()
                df.to_csv("dashboard_data.csv", index=False)
            except Exception as e:
                st.error(f"Failed to generate initial data: {e}")
                return pd.DataFrame()
            
    try:
        df = pd.read_csv("dashboard_data.csv")
        # Ensure 'Details' column is string to avoid errors
        if 'Details' in df.columns:
            df['Details'] = df['Details'].fillna("").astype(str)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# ==================== Sidebar: Force Refresh ====================
# This button triggers the script to run and fetch new data
if st.sidebar.button("Force Refresh Data"):
    with st.spinner("Fetching fresh market data from Yahoo & Google News..."):
        try:
            # 1. Run the generator function from update_data.py
            new_df = build_data()
            # 2. Save to CSV
            new_df.to_csv("dashboard_data.csv", index=False)
            # 3. Clear cache to reload the new CSV
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Update failed: {e}")

# Load the data (Cached)
df = load_data()

# ==================== Dashboard UI ====================
st.title("NIFTY 50 Pro Dashboard")
st.markdown(f"**Live Chart • FII/DII • Key Drivers • News**")

# --- FII / DII Section (Moneycontrol Source) ---
st.subheader("Latest FII / DII Net Flow (₹ Cr)")

@st.cache_data(ttl=3600)
def get_fii_dii():
    try:
        # Source: Moneycontrol (More reliable for scraping than NSE)
        url = "https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/index.php"
        
        # Headers to look like a real browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Pandas can extract all tables from the HTML automatically
        # We look for the table containing "FII" and "DII" text
        dfs = pd.read_html(response.text)
        
        for df in dfs:
            # Convert to string to safely check for keywords
            if "FII" in df.to_string() and "DII" in df.to_string():
                # Usually Moneycontrol's table has columns like:
                # [Institution, Gross Purchase, Gross Sales, Net Purchase, Date]
                # We need to clean column names to be sure
                df.columns = [c.lower() for c in df.columns]
                
                # Filter rows
                fii_row = df[df.iloc[:, 0].astype(str).str.contains("FII", case=False, na=False)]
                dii_row = df[df.iloc[:, 0].astype(str).str.contains("DII", case=False, na=False)]
                
                if not fii_row.empty and not dii_row.empty:
                    # Extract Net Value (usually the 4th column, index 3)
                    # Values might be strings like "1,234.56" -> need cleanup
                    fii_val = fii_row.iloc[0, 3]
                    dii_val = dii_row.iloc[0, 3]
                    
                    # Helper to convert "1,234.50" string to float
                    def clean_val(x):
                        return float(str(x).replace(",", ""))

                    fii_net = clean_val(fii_val)
                    dii_net = clean_val(dii_val)
                    
                    # Moneycontrol doesn't always have the date in the row, 
                    # but we can assume it's the latest available if we fetched it live.
                    return "Latest", fii_net, dii_net

        return "Data Not Found", 0.0, 0.0
        
    except Exception as e:
        print(f"Error fetching FII/DII: {e}")
        return "Error", 0.0, 0.0

# Call the function
date_fii, fii_net, dii_net = get_fii_dii()

# Display Metrics
c1, c2 = st.columns(2)
c1.metric("FII Net", f"₹{fii_net:,.0f} Cr", delta=fii_net)
c2.metric("DII Net", f"₹{dii_net:,.0f} Cr", delta=dii_net)
st.caption(f"Source: Moneycontrol • Status: {date_fii}")

# --- Cards Section ---
st.markdown("---")
st.subheader("Key Market Drivers")

# Helper to render cards
def render_card(col, row):
    title = row.get('Event', 'Unknown')
    value = row.get('Value', 'N/A')
    impact = row.get('Impact', 'Neutral')
    details = row.get('Details', '')
    
    color = "#00C853" if any(x in str(impact) for x in ["Positive","Bullish","Low"]) else \
            "#D50000" if any(x in str(impact) for x in ["Negative","Bearish","High"]) else "#FF9800"

    with col:
        st.markdown(f"""
        <div class="card">
            <h4 style="margin:0 0 12px 0;">{title}</h4>
            <div style="font-size:32px; font-weight:bold; color:{color}">{value}</div>
            <div style="margin-top:8px; font-weight:bold; color:{color}">Impact: {impact}</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Latest News"):
            if details and str(details).lower() != "nan" and details.strip() != "":
                for art in details.split("|||"):
                    parts = art.split("|")
                    if len(parts) >= 2:
                        st.markdown(f"• [{parts[0]}]({parts[1]})")
            else:
                st.caption("No recent news found.")

if not df.empty:
    # Layout Columns
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("##### 1-Day Triggers")
        for _, r in df[df['Timeframe'] == "1-Day"].iterrows(): render_card(col1, r)

    with col2:
        st.markdown("##### 7-Day Outlook")
        for _, r in df[df['Timeframe'] == "7-Day"].iterrows(): render_card(col2, r)

    with col3:
        st.markdown("##### 30-Day Trends")
        for _, r in df[df['Timeframe'] == "30-Day"].iterrows(): render_card(col3, r)

    # --- Footer ---
    try:
        updated = df[df['Timeframe'] == 'Meta']['Value'].iloc[0]
        st.caption(f"Last Full Update: {updated} IST")
    except:
        pass
else:
    st.warning("Dashboard data is empty. Click 'Force Refresh Data' to fetch.")
