import pandas as pd
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pytz

# --- 1. NEWS ENGINE (FRESHNESS ENFORCED) ---
def get_related_news(topic, days_lookback=2):
    """
    Fetches news from Google News RSS with a strict date filter.
    days_lookback: 2 means 'last 48 hours'.
    """
    # 1. Format topic for URL
    formatted_topic = topic.replace(" ", "+")
    
    # 2. Add 'when:Xd' to force recent results
    # q={topic}+when:{days}d
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
            
            # Clean Date Format (Mon, 05 Dec 2023...) -> (Dec 05)
            try:
                dt = datetime.strptime(pubDate, "%a, %d %b %Y %H:%M:%S %Z")
                clean_date = dt.strftime("%b %d, %H:%M")
            except:
                clean_date = "Recent"
            
            # Create a Markdown link string: "Title|Link|Date"
            links.append(f"{title}|{link}|{clean_date}")
            count += 1
            
        return "|||".join(links)
    except:
        return ""

# --- 2. DATA ENGINE ---
def get_change_and_news(ticker, name, query_term):
    try:
        # Data
        tick = yf.Ticker(ticker)
        hist = tick.history(period="5d")
        if len(hist) < 2: return 0.0, ""
        
        latest = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change = ((latest - prev) / prev) * 100
        
        # News (Strict 2-day limit for daily items)
        news_block = get_related_news(query_term, days_lookback=2)
        
        return float(change), news_block
    except:
        return 0.0, ""

# --- 3. BUILD DASHBOARD ---
def build_data():
    events = []
    
    # --- 1 DAY ITEMS (Tactical - 48h News) ---
    
    # US Markets
    # Query: "US Stock Market India Impact" to find relevance
    val, news = get_change_and_news("^GSPC", "US Markets", "US Stock Market S&P 500 analysis")
    if val == 0: val, news = get_change_and_news("SPY", "US Markets", "US Stock Market analysis")
    
    events.append({
        "Timeframe": "1-Day", "Event": "🇺🇸 US Market Trend", 
        "Value": f"{val:.2f}%", "Impact": "Positive" if val > 0 else "Negative",
        "Details": news
    })

    # Crude Oil
    val, news = get_change_and_news("CL=F", "Crude Oil", "Crude Oil Price India economy")
    events.append({
        "Timeframe": "1-Day", "Event": "🛢️ Crude Oil Impact", 
        "Value": f"{val:.2f}%", "Impact": "Negative" if val > 0 else "Positive",
        "Details": news
    })

    # VIX
    tick = yf.Ticker("^VIX")
    hist = tick.history(period="2d")
    vix_val = hist['Close'].iloc[-1] if not hist.empty else 0
    events.append({
        "Timeframe": "1-Day", "Event": "📉 Market Fear (VIX)", 
        "Value": f"{vix_val:.2f}", "Impact": "High" if vix_val > 20 else "Normal",
        "Details": get_related_news("Global Market Volatility VIX", days_lookback=2)
    })

    # --- 7 DAY ITEMS (Weekly - 7d News) ---
    today = datetime.now()
    days_ahead = 3 - today.weekday()
    if days_ahead <= 0: days_ahead += 7
    next_expiry = today + timedelta(days=days_ahead)
    expiry_date = next_expiry.strftime('%b %d')
    
    # For weekly view, we allow 7 days lookback
    events.append({
        "Timeframe": "7-Day", "Event": "📅 Weekly Expiry", 
        "Value": expiry_date, "Impact": "Volatile",
        "Details": get_related_news("Nifty 50 Option Chain Analysis", days_lookback=7)
    })

    # --- 30 DAY ITEMS (Macro - 30d News) ---
    month_name = datetime.now().strftime('%B')
    events.append({
        "Timeframe": "30-Day", "Event": f"📊 {month_name} Seasonality", 
        "Value": "Check History", "Impact": "Info",
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
print("✅ Dashboard updated with FRESH sources")
