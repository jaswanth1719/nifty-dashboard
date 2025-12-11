import pandas as pd
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pytz
import warnings
import os
from pathlib import Path

warnings.filterwarnings("ignore")
IST")

# -----------------------------
# CONFIG
# -----------------------------
IST = pytz.timezone('Asia/Kolkata')
DATA_FILE = Path("dashboard_data.csv")
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# -----------------------------
# 1. ROBUST NEWS FETCHER (with caching)
# -----------------------------
def get_related_news(topic: str, days_lookback: int = 3) -> str:
    """Fetch top 3 recent news with caching and better reliability."""
    cache_file = CACHE_DIR / f"news_{topic.replace(' ', '_')}_{days_lookback}d.cache"
    
    # Serve from cache if < 30 mins old
    if cache_file.exists():
        age = datetime.now(IST) - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if age.total_seconds() < 1800:  # 30 mins
            try:
                return cache_file.read_text(encoding='utf-8')
            except:
                pass

    formatted_topic = topic.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={formatted_topic}+when:{days_lookback}d&hl=en-IN&gl=IN&ceid=IN:en"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/130.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        articles = []
        for item in root.findall('./channel/item')[:5]:  # Get top 5, pick best 3
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""

            if not title or not link:
                continue

            # Clean date
            try:
                pub_dt = datetime.strptime(pub_date[:25], "%a, %d %b %Y %H:%M:%S")
                date_str = pub_dt.strftime("%b %d")
            except:
                date_str = "Recent"

            articles.append(f"{title}|{link}|{date_str}")

            if len(articles) >= 3:
                break

        result = "|||".join(articles) if articles else "No recent news"
        
        # Cache result
        cache_file.write_text(result, encoding='utf-8')
        return result

    except Exception as e:
        print(f"News fetch failed ({topic}): {e}")
        return "News temporarily unavailable"


# -----------------------------
# 2. SAFE YFINANCE WRAPPER
# -----------------------------
def safe_yf_change(tickers, period="5d", fallback_to_etf=True):
    """Try multiple ticker variants, return % change and raw data."""
    for t in tickers:
        try:
            tick = yf.Ticker(t)
            hist = tick.history(period=period, interval="1d", auto_adjust=True)
            if len(hist) < 2:
                continue
            latest = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            change_pct = (latest - prev) / prev * 100
            return round(change_pct, 2), latest
        except Exception as e:
            continue
    return 0.0, None


# -----------------------------
# 3. SEASONALITY (Improved Logic)
# -----------------------------
def get_seasonality_impact():
    try:
        now = datetime.now(IST)
        current_month = now.month

        nifty = yf.download("^NSEI", period="15y", interval="1mo", progress=False)
        if nifty.empty or len(nifty) < 24:
            return "N/A", "Neutral"

        nifty['Return'] = nifty['Close'].pct_change() * 100
        monthly = nifty[nifty.index.month == current_month]

        # Exclude current incomplete month
        if not monthly.empty and monthly.index[-1].date() >= now.date().replace(day=1):
            monthly = monthly.iloc[:-1]

        if len(monthly) < 3:
            return "Limited Data", "Neutral"

        avg_return = monthly['Return'].mean()
        std_dev = monthly['Return'].std()

        if avg_return > 1.2:
            impact = "Strongly Bullish"
        elif avg_return > 0.5:
            impact = "Bullish"
        elif avg_return < -1.2:
            impact = "Strongly Bearish"
        elif avg_return < -0.5:
            impact = "Bearish"
        else:
            impact = "Neutral"

        return f"{avg_return:+.2f}%", impact

    except Exception as e:
        print(f"Seasonality error: {e}")
        return "Error", "Neutral"


# -----------------------------
# 4. BUILD DASHBOARD DATA
# -----------------------------
def build_data():
    events = []
    now_ist = datetime.now(IST)

    # 1. US Market (S&P 500)
    sp_change, _ = safe_yf_change(["^GSPC", "SPY"])
    events.append({
        "Timeframe": "1-Day",
        "Event": "US Market (S&P 500)",
        "Value": f"{sp_change:+.2f}%",
        "Impact": "Bullish" if sp_change > 0 else "Bearish",
        "Details": get_related_news("S&P 500 today", days_lookback=2)
    })

    # 2. Crude Oil
    oil_change, _ = safe_yf_change(["CL=F", "CRUDEOIL.NS"])
    impact_oil = "Bearish" if oil_change > 2 else "Bullish" if oil_change < -1 else "Neutral"
    events.append({
        "Timeframe": "1-Day",
        "Event": "Crude Oil Price",
        "Value": f"{oil_change:+.2f}%",
        "Impact": impact_oil,
        "Details": get_related_news("Crude oil price India impact", days_lookback=2)
    })

    # 3. India VIX
    try:
        india_vix = yf.Ticker("^INDIAVIX").history(period="2d")['Close'].iloc[-1]
        vix_val = round(india_vix, 2)
        vix_impact = "Extreme Fear" if vix_val > 25 else "High Fear" if vix_val > 18 else "Calm"
    except:
        vix_val, vix_impact = "N/A", "Unknown"

    events.append({
        "Timeframe": "1-Day",
        "Event": "India VIX (Fear Gauge)",
        "Value": str(vix_val),
        "Impact": vix_impact,
        "Details": get_related_news("India VIX today", days_lookback=2)
    })

    # 4. Weekly Expiry
    days_to_thursday = (3 - now_ist.weekday() + 7) % 7 or 7
    next_expiry = now_ist + timedelta(days=days_to_thursday)
    events.append({
        "Timeframe": "7-Day",
        "Event": "Next Weekly Expiry",
        "Value": next_expiry.strftime('%b %d (%A)'),
        "Impact": "High Volatility Expected",
        "Details": get_related_news("Nifty weekly expiry strategy", days_lookback=5)
    })

    # 5. Monthly Seasonality
    month_name = now_ist.strftime('%B')
    seas_val, seas_impact = get_seasonality_impact()
    events.append({
        "Timeframe": "30-Day",
        "Event": f"{month_name} Seasonality",
        "Value": seas_val,
        "Impact": seas_impact,
        "Details": get_related_news(f"Nifty {month_name} historical performance", days_lookback=30)
    })

    # 6. Next Major Events (RBI, CPI, FOMC, etc.) - Bonus!
    events.append({
        "Timeframe": "Upcoming",
        "Event": "Major Economic Events",
        "Value": "RBI Policy, CPI, FOMC",
        "Impact": "Watch Calendar",
        "Details": get_related_news("India economic calendar RBI FOMC CPI GDP this month", days_lookback=15)
    })

    # Meta
    events.append({
        "Timeframe": "Meta",
        "Event": "Last Updated (IST)",
        "Value": now_ist.strftime('%b %d, %H:%M'),
        "Impact": "Live",
        "Details": ""
    })

    df = pd.DataFrame(events)
    df.to_csv(DATA_FILE, index=False)
    print(f"Dashboard updated at {now_ist.strftime('%Y-%m-%d %H:%M:%S IST')}")
    return df


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    df = build_data()
    print(df[['Timeframe', 'Event', 'Value', 'Impact']])
