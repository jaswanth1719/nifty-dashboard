import pandas as pd
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pytz
import warnings
warnings.filterwarnings("ignore")

# News Engine (unchanged, reliable)
def get_related_news(topic, days_lookback=2):
    formatted_topic = topic.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={formatted_topic}+when:{days_lookback}d&hl=en-IN&gl=IN&ceid=IN:en"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=8)
        root = ET.fromstring(response.content)
        links = []
        for item in root.findall('./channel/item')[:3]:
            title = item.find('title').text or ""
            link = item.find('link').text or ""
            pubDate = item.find('pubDate').text or ""
            try:
                dt = datetime.strptime(pubDate.replace("GMT", "+0000"), "%a, %d %b %Y %H:%M:%S %z")
                clean_date = dt.strftime("%b %d")
            except:
                clean_date = "Recent"
            links.append(f"{title}|{link}|{clean_date}")
        return "|||".join(links) if links else "No news"
    except:
        return "News unavailable"

# Change Calc (with fallback)
def get_change_and_news(ticker, query_term):
    try:
        tick = yf.Ticker(ticker)
        hist = tick.history(period="5d")
        if len(hist) < 2: return 0.0, "Data unavailable"
        latest = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change = ((latest - prev) / prev) * 100
        news = get_related_news(query_term, 2)
        return round(change, 2), news
    except:
        return 0.0, "Data unavailable"

# Seasonality (unchanged, solid)
def get_seasonality_impact():
    try:
        current_month = datetime.now().month
        current_year = datetime.now().year
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="12y", interval="1mo")
        hist['Return'] = hist['Close'].pct_change() * 100
        seasonal = hist[hist.index.month == current_month]
        if not seasonal.empty and seasonal.index[-1].year == current_year:
            seasonal = seasonal.iloc[:-1]
        if seasonal.empty: return "N/A", "Neutral"
        avg = seasonal['Return'].mean()
        impact = "Bullish" if avg > 1.5 else "Positive" if avg > 0 else "Bearish" if avg < -1.5 else "Negative"
        return f"{avg:+.2f}%", impact
    except:
        return "Error", "Neutral"

# Build Data (Expanded with new events)
def build_data():
    events = []
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist)

    # 1-Day (Expanded)
    val, news = get_change_and_news("^GSPC", "S&P 500 market analysis")
    events.append({"Timeframe": "1-Day", "Event": "US Market Trend", "Value": f"{val:+.2f}%", "Impact": "Positive" if val > 0 else "Negative", "Details": news})
    
    val, news = get_change_and_news("CL=F", "Crude Oil India impact")
    events.append({"Timeframe": "1-Day", "Event": "Crude Oil Price", "Value": f"{val:+.2f}%", "Impact": "Positive" if val < 0 else "Negative", "Details": news})
    
    try:
        vix = yf.Ticker("^VIX").history(period="2d")['Close'].iloc[-1]
        impact = "Low" if vix < 15 else "Normal" if vix < 20 else "High"
    except:
        vix, impact = 0, "Unavailable"
    events.append({"Timeframe": "1-Day", "Event": "Global VIX (Fear)", "Value": f"{vix:.2f}", "Impact": impact, "Details": get_related_news("VIX volatility")})
    
    val, news = get_change_and_news("INR=X", "USD INR forex India")  # New: USD/INR (rise negative for India)
    events.append({"Timeframe": "1-Day", "Event": "USD/INR Rate", "Value": f"{val:+.2f}%", "Impact": "Negative" if val > 0 else "Positive", "Details": news})
    
    try:
        india_vix = yf.Ticker("^INDIAVIX").history(period="2d")['Close'].iloc[-1]
        impact = "Low" if india_vix < 15 else "Normal" if india_vix < 20 else "High"
    except:
        india_vix, impact = 0, "Unavailable"
    events.append({"Timeframe": "1-Day", "Event": "India VIX", "Value": f"{india_vix:.2f}", "Impact": impact, "Details": get_related_news("India VIX NIFTY")})  # New
    
    # 7-Day (Expanded with economic data placeholder)
    days_to_thu = (3 - today.weekday() + 7) % 7 or 7
    expiry = (today + timedelta(days=days_to_thu)).strftime('%b %d')
    events.append({"Timeframe": "7-Day", "Event": "NIFTY Expiry (Thu)", "Value": expiry, "Impact": "High Volatility", "Details": get_related_news("Nifty expiry analysis", 7)})
    
    # Example weekly event: US Jobless Claims (Thu), but static for now
    events.append({"Timeframe": "7-Day", "Event": "US Jobless Claims", "Value": "Thu Release", "Impact": "Volatile if High", "Details": get_related_news("US jobless claims India impact", 7)})  # New

    # 30-Day (Expanded)
    month = today.strftime('%B')
    seas_val, seas_impact = get_seasonality_impact()
    events.append({"Timeframe": "30-Day", "Event": f"{month} Seasonality", "Value": seas_val, "Impact": seas_impact, "Details": get_related_news(f"Nifty {month} outlook")})
    
    try:
        bond = yf.Ticker("IND10Y.BO").history(period="2mo")['Close'].iloc[-1]  # India 10Y Bond Yield
        prev_bond = yf.Ticker("IND10Y.BO").history(period="2mo")['Close'].iloc[-2]
        change = ((bond - prev_bond) / prev_bond) * 100
        impact = "Negative" if change > 0 else "Positive"  # Rising yields negative
    except:
        change, impact = 0, "Unavailable"
    events.append({"Timeframe": "30-Day", "Event": "10Y Bond Yield", "Value": f"{change:+.2f}%", "Impact": impact, "Details": get_related_news("India bond yields Nifty", 30)})  # New
    
    # Meta
    events.append({"Timeframe": "Meta", "Event": "Last Updated", "Value": today.strftime('%Y-%m-%d %H:%M:%S'), "Impact": "Info", "Details": ""})
    
    return pd.DataFrame(events)

if __name__ == "__main__":
    df = build_data()
    df.to_csv("dashboard_data.csv", index=False)
    print("Dashboard data updated!")
