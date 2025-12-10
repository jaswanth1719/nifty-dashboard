import streamlit as st
import pandas as pd

# ------------------ Page Config ------------------
st.set_page_config(
    page_title="NIFTY 50 Impact Dashboard",
    page_icon="chart_with_upwards_trend",
    layout="wide"
)

st.title("NIFTY 50 Live Impact Dashboard")
st.markdown("**Real-time market movers • Click any card → View News & Sources**")

# ------------------ Custom CSS ------------------
st.markdown("""
<style>
    .card {
        padding: 18px;
        border-radius: 12px;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-left: 6px solid #1e88e5;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin-bottom: 16px;
        transition: transform 0.2s;
    }
    .card:hover { transform: translateY(-4px); }
    .impact-positive { color: #00C853; font-weight: bold; }
    .impact-negative { color: #D50000; font-weight: bold; }
    .impact-neutral { color: #FF9800; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ------------------ Load Data ------------------
@st.cache_data(ttl=300)  # 5 min cache
def load_data():
    try:
        df = pd.read_csv("dashboard_data.csv")
        df['Details'] = df['Details'].fillna("").astype(str)
        return df
    except FileNotFoundError:
        st.error("dashboard_data.csv not found. Run your data script first!")
        st.stop()
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

df = load_data()

# ------------------ Render Card (Fixed: uses correct column!) ------------------
def render_card(column, row):
    title = row['Event']
    value = row['Value']
    impact = row['Impact']
    details = row['Details']

    # Color logic
    if any(x in impact for x in ["Positive", "Bullish", "Low Fear"]):
        color = "#00C853"
        badge_class = "impact-positive"
    elif any(x in impact for x in ["Negative", "Bearish", "High", "Volatile"]):
        color = "#D50000"
        badge_class = "impact-negative"
    else:
        color = "#FF9800"
        badge_class = "impact-neutral"

    with column:
        st.markdown(f"""
        <div class="card">
            <h4 style="margin:0 0 10px 0; color:#1565c0">{title}</h4>
            <div style="font-size:32px; font-weight:bold; color:{color}; margin:10px 0">
                {value}
            </div>
            <div class="{badge_class}">Impact: {impact}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("View News & Sources", expanded=False):
            if details and details.strip() and details != "nan":
                for article in details.split("|||"):
                    parts = article.split("|", 2)
                    if len(parts) >= 2:
                        headline, url = parts[0], parts[1]
                        date = parts[2] if len(parts) > 2 else "Recent"
                        st.markdown(f"**{date}** → [{headline}]({url})")
            else:
                st.caption("No recent news available.")

# ------------------ Layout ------------------
col1, col2, col3 = st.columns(3)

# 1-Day
with col1:
    st.subheader("1-Day Triggers")
    for _, row in df[df['Timeframe'] == "1-Day"].iterrows():
        render_card(col1, row)  # ← Correct column passed!

# 7-Day
with col2:
    st.subheader("7-Day Outlook")
    for _, row in df[df['Timeframe'] == "7-Day"].iterrows():
        render_card(col2, row)

# 30-Day
with col3:
    st.subheader("30-Day Trends")
    for _, row in df[df['Timeframe'] == "30-Day"].iterrows():
        render_card(col3, row)

# ------------------ Footer ------------------
try:
    update_time = df[df['Timeframe'] == 'Meta']['Value'].iloc[0]
    st.markdown(f"**Last Updated:** {update_time} IST")
except:
    pass

# Refresh button + auto-refresh every 5 mins
col_btn, _ = st.columns([1, 4])
with col_btn:
    if st.button("Refresh Now"):
        st.cache_data.clear()
        st.rerun()

# Silent auto-refresh
st.markdown("""
<script>
    setTimeout(() => location.reload(), 300000);  // 5 minutes
</script>
""", unsafe_allow_html=True)
