import pandas as pd
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pytz

# --- 1. NEWS ENGINE ---
def get_related_news(topic):
    """Fetches top 3 news links for a specific topic via Google News RSS."""
    # topics: 'Crude Oil', 'S&P 500', 'Nifty 50', 'India VIX'
    formatted_topic = topic.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={formatted_topic}+finance+news&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        response = requests.get(url, timeout=4)
        root = ET.fromstring(response.content)
        
        links = []
        count = 0
        for item in root.findall('./channel/item'):
            if count >= 3: break
            title = item.find('title').text
            link = item.find('link').text
            pubDate = item.find('pubDate').text[:16] # Shorten date
            
            # Create a Markdown link string: "Title|Link|Date"
            links.append(f"{title}|{link}|{pubDate}")
            count += 1
            
        # Join with a special separator '|||' to split later
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
        
        # News
        news_block = get_related_news(query_term)
        
        return float(change), news_block
    except:
        return 0.0, ""

# --- 3. BUILD DASHBOARD ---
def build_data():
    events = []
    
    # --- 1 DAY ITEMS ---
    # US Markets
    val, news = get_change_and_news("^GSPC", "US Markets", "US Stock Market S&P 500")
    if val == 0: val, news = get_change_and_news("SPY", "US Markets", "US Stock Market") # Fallback
    
    events.append({
        "Timeframe": "1-Day", "Event": "🇺🇸 US Market Trend", 
        "Value": f"{val:.2f}%", "Impact": "Positive" if val > 0 else "Negative",
        "Details": news
    })

    # Crude Oil
    val, news = get_change_and_news("CL=F", "Crude Oil", "Crude Oil Price")
    events.append({
        "Timeframe": "1-Day", "Event": "🛢️ Crude Oil Impact", 
        "Value": f"{val:.2f}%", "Impact": "Negative" if val > 0 else "Positive",
        "Details": news
    })

    # VIX (No news needed usually, but we can add)
    tick = yf.Ticker("^VIX")
    hist = tick.history(period="2d")
    vix_val = hist['Close'].iloc[-1] if not hist.empty else 0
    events.append({
        "Timeframe": "1-Day", "Event": "📉 Market Fear (VIX)", 
        "Value": f"{vix_val:.2f}", "Impact": "High" if vix_val > 20 else "Normal",
        "Details": get_related_news("Global Market Volatility VIX")
    })

    # --- 7 DAY ITEMS ---
    # Weekly Expiry
    today = datetime.now()
    days_ahead = 3 - today.weekday()
    if days_ahead <= 0: days_ahead += 7
    next_expiry = today + timedelta(days=days_ahead)
    expiry_date = next_expiry.strftime('%b %d')
    
    events.append({
        "Timeframe": "7-Day", "Event": "📅 Weekly Expiry", 
        "Value": expiry_date, "Impact": "Volatile",
        "Details": get_related_news("Nifty 50 Option Chain Analysis")
    })

    # --- 30 DAY ITEMS ---
    # Seasonality
    month_name = datetime.now().strftime('%B')
    events.append({
        "Timeframe": "30-Day", "Event": f"📊 {month_name} Seasonality", 
        "Value": "Check History", "Impact": "Info",
        "Details": get_related_news(f"Stock Market Outlook {month_name} 2024 India")
    })

    # Meta
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')
    events.append({"Timeframe": "Meta", "Event": "Last Updated", "Value": now, "Impact": "Info", "Details": ""})

    return pd.DataFrame(events)

# EXECUTE
df = build_data()
df.to_csv("dashboard_data.csv", index=False)
print("✅ Dashboard updated with Sources & Links")
