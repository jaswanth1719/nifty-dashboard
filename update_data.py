import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import requests
import xml.etree.ElementTree as ET

def get_google_news():
    # Fetch RSS feed for "Nifty 50 India Economy"
    url = "https://news.google.com/rss/search?q=Nifty+50+India+Economy+Market&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        
        # Get top 3 headlines
        headlines = []
        count = 0
        for item in root.findall('./channel/item'):
            title = item.find('title').text
            pubDate = item.find('pubDate').text
            # Clean up date format
            try:
                dt = datetime.strptime(pubDate, "%a, %d %b %Y %H:%M:%S %Z")
                pubDate = dt.strftime("%b %d, %H:%M")
            except:
                pass
                
            headlines.append({"Metric": "News", "Value": title, "Status": pubDate})
            count += 1
            if count >= 3: break
            
        return headlines
    except:
        return [{"Metric": "News", "Value": "Could not fetch news", "Status": "Error"}]

def get_next_expiry():
    # Calculate next Thursday
    today = datetime.now()
    days_ahead = 3 - today.weekday() # Thursday is 3
    if days_ahead <= 0: 
        days_ahead += 7
    next_thursday = today + timedelta(days=days_ahead)
    return next_thursday.strftime("%b %d (Thu)")

def fetch_data():
    tickers = ['^GSPC', '^NSEI', 'CL=F', '^VIX']
    data_list = []
    
    # 1. MARKET DATA (The Numbers)
    try:
        data = yf.download(tickers, period='5d', progress=False)['Close']
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        changes = ((latest - prev) / prev) * 100
        
        data_list = [
            {"Metric": "US Markets (S&P 500)", "Value": f"{changes.get('^GSPC', 0):.2f}%", "Status": "Bullish" if changes.get('^GSPC', 0) > 0 else "Bearish"},
            {"Metric": "Crude Oil", "Value": f"{changes.get('CL=F', 0):.2f}%", "Status": "Bearish" if changes.get('CL=F', 0) > 0 else "Bullish"},
            {"Metric": "Global VIX", "Value": f"{data['^VIX'].iloc[-1]:.2f}", "Status": "Volatile" if data['^VIX'].iloc[-1] > 20 else "Stable"},
        ]
    except Exception as e:
        print(f"Market Data Error: {e}")

    # 2. CALCULATED EVENTS
    expiry = get_next_expiry()
    data_list.append({"Metric": "📅 Next Weekly Expiry", "Value": expiry, "Status": "Critical"})

    # 3. NEWS EVENTS
    news_items = get_google_news()
    data_list.extend(news_items)
    
    # 4. TIMESTAMP
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')
    data_list.append({"Metric": "Last Updated", "Value": now, "Status": "Info"})

    return data_list

# Execute and Save
data = fetch_data()
if data:
    df = pd.DataFrame(data)
    df.to_csv("dashboard_data.csv", index=False)
    print("✅ CSV updated with News & Events")
