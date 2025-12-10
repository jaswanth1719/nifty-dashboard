import pandas as pd
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pytz
import warnings
warnings.filterwarnings("ignore")  # Optional: suppress yfinance warnings

# --- 1. NEWS ENGINE (More Reliable) ---
def get_related_news(topic, days_lookback=2):
    """Fetches top 3 recent news articles with strict date filtering."""
    formatted_topic = topic.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={formatted_topic}+when:{days_lookback}d&hl=en-IN&gl=IN&ceid=IN:en"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        links = []
        count = 0
        for item in root.findall('./channel/item'):
            if count >= 3:
                break
            title_elem = item.find('title')
            link_elem = item.find('link')
            pubDate_elem = item.find('pubDate')

            if None in (title_elem, link_elem, pubDate_elem):
                continue
                
            title = title_elem.text
            link = link_elem.text
            pubDate = pubDate_elem.text

            try:
                # Handle GMT/UTC in pubDate
                dt = datetime.strptime(pubDate.replace("GMT", "+0000"), "%a, %d %b %Y %H:%M:%S %z")
                clean_date = dt.strftime("%b %d")
            except:
                clean_date = "Recent"

            links.append(f"{title}|{link}|{clean_date}")
            count += 1

        return "|||".join(links) if links else "No recent news"
    except Exception as e:
        print(f"News fetch failed for '{topic}': {e}")
        return "News unavailable"


# --- 2. DATA CALCULATIONS ---
def get_change_and_news(ticker, query_term):
    """Calculates 1-day % change with fallback and better error handling."""
    for t in [ticker, ticker.replace("^", "")]:  # Try both ^GSPC and GSPC if needed
        try:
            tick = yf.Ticker(t)
            hist = tick.history(period="5d", interval="1d")
            if len(hist) < 2:
                continue

            latest = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            change = ((latest - prev) / prev) * 100

            news_block = get_related_news(query_term, days_lookback=2)
            return round(float(change), 2), news_block
        except Exception as e:
            continue
    return 0.0, "Data unavailable"


def get_seasonality_impact():
    """Historical average return for current month (excluding current incomplete month)"""
    try:
        current_month = datetime.now(pytz.timezone('Asia/Kolkata')).month
        current_year = datetime.now(pytz.timezone('Asia/Kolkata')).year

        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="12y", interval="1mo")  # More data = better avg
        
        if hist.empty or len(hist) < 12:
            return "N/A", "Info"

        hist['Return'] = hist['Close'].pct_change() * 100
        seasonal_data = hist[hist.index.month == current_month].copy()

        # Remove current incomplete month
        if not seasonal_data.empty:
            last_idx = seasonal_data.index[-1]
            if last_idx.year == current_year and last_idx.month == current_month:
                seasonal_data = seasonal_data.iloc[:-1]

        if len(seasonal_data) == 0:
            return "No Data", "Info"

        avg_return = seasonal_data['Return'].mean()

        if avg_return > 1.5:
            impact = "Bullish"
        elif avg_return > 0.5:
            impact = "Positive"
        elif avg_return < -1.5:
            impact = "Bearish"
        elif avg_return < -0.5:
            impact = "Negative"
        else:
            impact = "Neutral"

        return f"{avg_return:+.2f}%", impact

    except Exception as e:
        print(f"Seasonality Error: {e}")
        return "Error", "Info"


# --- 3. BUILD DASHBOARD ---
def build_data():
    events = []

    # === 1-Day Items ===
    val, news = get_change_and_news("^GSPC", "S&P 500 today market analysis")
    if abs(val) < 0.01:  # fallback to SPY
        val, news = get_change_and_news("SPY", "SPY ETF performance")
    events.append({
        "Timeframe": "1-Day", "Event": "US Market Trend",
        "Value": f"{val:+.2f}%", "Impact": "Positive" if val > 0 else "Negative",
        "Details": news
    })

    val, news = get_change_and_news("CL=F", "Crude Oil price impact India")
    events.append({
        "Timeframe": "1-Day", "Event": "Crude Oil Impact",
        "Value": f"{val:+.2f}%", "Impact": "Negative" if val > 0 else "Positive",
        "Details": news
    })

    try:
        vix = yf.Ticker("^VIX").history(period="2d")['Close'].iloc[-1]
        vix_val = round(vix, 2)
        vix_impact = "High Fear" if vix_val > 30 else "Elevated" if vix_val > 20 else "Low Fear"
    except:
        vix_val, vix_impact = 0.0, "Unavailable"

    events.append({
        "Timeframe": "1-Day", "Event": "Market Fear (VIX)",
        "Value": str(vix_val), "Impact": vix_impact,
        "Details": get_related_news("VIX volatility fear gauge", days_lookback=2)
    })

    # === 7-Day: Weekly Expiry (India) ===
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist)
    # Thursday expiry for NIFTY/BANKNIFTY
    days_to_thursday = (3 - today.weekday() + 7) % 7
    if days_to_thursday == 0:
        days_to_thursday = 7  # Next week if today is Thursday
    next_expiry = today + timedelta(days=days_to_thursday)
    expiry_str = next_expiry.strftime('%b %d')

    events.append({
        "Timeframe": "7-Day", "Event": "Weekly Expiry (Thu)",
        "Value": expiry_str, "Impact": "High Volatility",
        "Details": get_related_news("Nifty BankNifty weekly expiry option chain", days_lookback=7)
    })

    # === 30-Day: Monthly Seasonality ===
    month_name = today.strftime('%B')
    seas_val, seas_impact = get_seasonality_impact()
    events.append({
        "Timeframe": "30-Day", "Event": f"{month_name} Seasonality",
        "Value": seas_val, "Impact": seas_impact,
        "Details": get_related_news(f"India stock market outlook {month_name} seasonality", days_lookback=30)
    })

    # === Meta ===
    events.append({
        "Timeframe": "Meta", "Event": "Last Updated (IST)",
        "Value": today.strftime('%Y-%m-%d %H:%M:%S'), "Impact": "Info", "Details": ""
    })

    return pd.DataFrame(events)


# === EXECUTE ===
if __name__ == "__main__":
    df = build_data()
    df.to_csv("dashboard_data.csv", index=False)
    print("Dashboard updated successfully!")
    print(df.head(10))
