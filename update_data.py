import pandas as pd
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pytz

# --- 1. NEWS ENGINE ---
def get_related_news(topic, days_lookback=2):
    """Fetches news with strict date filtering."""
    formatted_topic = topic.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={formatted_topic}+when:{days_lookback}d&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        
        links = []
        count = 0
        for item in root.findall('./channel/item'):
            if count >= 3: break
            title = item.find('title').text
            link = item.find('link').text
            pubDate = item.find('pubDate').text
            
            try:
                dt = datetime.strptime(pubDate, "%a, %d %b %Y %H:%M:%S %Z")
                clean_date = dt.strftime("%b %d")
            except:
                clean_date = "Recent"
            
            links.append(f"{title}|{link}|{clean_date}")
            count += 1
            
        return "|||".join(links)
    except:
        return ""

# --- 2. DATA CALCULATIONS ---
def get_change_and_news(ticker, query_term):
    """Calculates % change for 1-Day items."""
    try:
        tick = yf.Ticker(ticker)
        hist = tick.history(period="5d")
        if len(hist) < 2: return 0.0, ""
        
        latest = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change = ((latest - prev) / prev) * 100
        
        news_block = get_related_news(query_term, days_lookback=2)
        return float(change), news_block
    except:
        return 0.0, ""

def get_seasonality_impact():
    """Calculates historical NIFTY returns for the current month (Excluding incomplete current month)."""
    try:
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Fetch 10 years of monthly data to get a solid average
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="10y", interval="1mo")
        
        if hist.empty:
            return "0.00%", "Info"
            
        # 1. Calculate Monthly Returns using standard % Change (Close vs Prev Close)
        # This correctly captures overnight gaps unlike (Close - Open)
        hist['Return'] = hist['Close'].pct_change() * 100
        
        # 2. Filter for ONLY the current month (e.g., all Decembers)
        seasonal_data = hist[hist.index.month == current_month].copy()
        
        # 3. CRITICAL FIX: Exclude the current incomplete month
        # If the last row is the current month of the current year, drop it.
        if not seasonal_data.empty:
            last_date = seasonal_data.index[-1]
            if last_date.month == current_month and last_date.year == current_year:
                seasonal_data = seasonal_data.iloc[:-1]
        
        if not seasonal_data.empty:
            avg_return = float(seasonal_data['Return'].mean())
            
            # Determine Impact
            if avg_return > 1.5: impact = "Bullish"
            elif avg_return > 0: impact = "Positive"
            elif avg_return < -1.5: impact = "Bearish"
            else: impact = "Negative"
            
            return f"Avg {avg_return:+.2f}%", impact
            
    except Exception as e:
        print(f"Seasonality Error: {e}")
        
    return "Neutral", "Info"

# --- 3. BUILD DASHBOARD ---
def build_data():
    events = []
    
    # --- 1 DAY ITEMS ---
    val, news = get_change_and_news("^GSPC", "US Stock Market S&P 500 analysis")
    if val == 0: val, news = get_change_and_news("SPY", "US Stock Market analysis")
    
    events.append({
        "Timeframe": "1-Day", "Event": "🇺🇸 US Market Trend", 
        "Value": f"{val:+.2f}%", "Impact": "Positive" if val > 0 else "Negative",
        "Details": news
    })

    val, news = get_change_and_news("CL=F", "Crude Oil Price India economy")
    events.append({
        "Timeframe": "1-Day", "Event": "🛢️ Crude Oil Impact", 
        "Value": f"{val:+.2f}%", "Impact": "Negative" if val > 0 else "Positive",
        "Details": news
    })

    tick = yf.Ticker("^VIX")
    hist = tick.history(period="2d")
    vix_val = hist['Close'].iloc[-1] if not hist.empty else 0
    events.append({
        "Timeframe": "1-Day", "Event": "📉 Market Fear (VIX)", 
        "Value": f"{vix_val:.2f}", "Impact": "High" if vix_val > 20 else "Normal",
        "Details": get_related_news("Global Market Volatility VIX", days_lookback=2)
    })

    # --- 7 DAY ITEMS ---
    today = datetime.now()
    days_ahead = 3 - today.weekday()
    if days_ahead <= 0: days_ahead += 7
    next_expiry = today + timedelta(days=days_ahead)
    expiry_date = next_expiry.strftime('%b %d')
    
    events.append({
        "Timeframe": "7-Day", "Event": "📅 Weekly Expiry", 
        "Value": expiry_date, "Impact": "Volatile",
        "Details": get_related_news("Nifty 50 Option Chain Analysis", days_lookback=7)
    })

    # --- 30 DAY ITEMS ---
    month_name = datetime.now().strftime('%B')
    seas_val, seas_impact = get_seasonality_impact()
    
    events.append({
        "Timeframe": "30-Day", "Event": f"📊 {month_name} Seasonality", 
        "Value": seas_val, "Impact": seas_impact,
        "Details": get_related_news(f"Stock Market Outlook {month_name} 2024 India", days_lookback=30)
    })

    # Meta
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')
    events.append({"Timeframe": "Meta", "Event": "Last Updated", "Value": now, "Impact": "Info", "Details": ""})

    return pd.DataFrame(events)

# EXECUTE
df = build_data()
df.to_csv("dashboard_data.csv", index=False)
print("✅ Dashboard updated: Seasonality Fixed")
