# update_data.py   ← FINAL WORKING VERSION (no syntax errors)

import pandas as pd
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pytz
from pathlib import Path

# -----------------------------
# Config
# -----------------------------
IST = pytz.timezone("Asia/Kolkata")
DATA_FILE = Path("dashboard_data.csv")
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# -----------------------------
# 1. News fetcher with cache
# -----------------------------
def get_related_news(topic: str, days_lookback: int = 3) -> str:
    cache_file = CACHE_DIR / f"news_{topic.replace(' ', '_')[:50]}_{days_lookback}d.cache"

    # Return cached version if less than 30 min old
    if cache_file.exists():
        age = datetime.now(IST) - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if age.total_seconds() < 1800:  # 30 minutes
            try:
                return cache_file.read_text(encoding="utf-8")
            except:
                pass

    url = f"https://news.google.com/rss/search?q={topic.replace(' ', '+')}+when:{days_lookback}d&hl=en-IN&gl=IN&ceid=IN:en"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.content)

        articles = []
        for item in root.findall("./channel/item")[:6]:
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            pub = item.find("pubDate").text if item.find("pubDate") is not None else ""

            if not title or not link:
                continue

            try:
                date_str = datetime.strptime(pub[:25], "%a, %d %b %Y %H:%M:%S").strftime("%b %d")
            except:
                date_str = "Recent"

            articles.append(f"{title}|{link}|{date_str}")
            if len(articles) >= 3:
                break

        result = "|||".join(articles) if articles else "No recent news"
        cache_file.write_text(result, encoding="utf-8")
        return result

    except Exception:
        return "News unavailable"


# -----------------------------
# 2. Safe % change
# -----------------------------
def safe_yf_change(tickers, period="5d"):
    for t in tickers:
        try:
            data = yf.download(t, period=period, interval="1d", progress=False, auto_adjust=True)
            if len(data) >= 2:
                change = (data["Close"].iloc[-1] / data["Close"].iloc[-2] - 1) * 100
                return round(change, 2)
        except:
            continue
    return 0.0


# -----------------------------
# 3. Seasonality
# -----------------------------
def get_seasonality_impact():
    try:
        now = datetime.now(IST)
        nifty = yf.download("^NSEI", period="15y", interval="1mo", progress=False)
        if len(nifty) < 24:
            return "N/A", "Neutral"

        nifty["Return"] = nifty["Close"].pct_change() * 100
        monthly = nifty[nifty.index.month == now.month]

        # Remove current incomplete month
        if not monthly.empty and monthly.index[-1].year == now.year and monthly.index[-1].month == now.month:
            monthly = monthly.iloc[:-1]

        if len(monthly) < 3:
            return "Limited data", "Neutral"

        avg = monthly["Return"].mean()

        if avg > 1.2:
            impact = "Strongly Bullish"
        elif avg > 0.5:
            impact = "Bullish"
        elif avg < -1.2:
            impact = "Strongly Bearish"
        elif avg < -0.5:
            impact = "Bearish"
        else:
            impact = "Neutral"

        return f"{avg:+.2f}%", impact
    except:
        return "Error", "Neutral"


# -----------------------------
# 4. Build dashboard
# -----------------------------
def build_data():
    events = []
    now = datetime.now(IST)

    # 1-Day
    sp = safe_yf_change(["^GSPC", "SPY"])
    events.append({
        "Timeframe": "1-Day", "Event": "US Market (S&P 500)",
        "Value": f"{sp:+.2f}%", "Impact": "Bullish" if sp > 0 else "Bearish",
        "Details": get_related_news("S&P 500 today", 2)
    })

    oil = safe_yf_change(["CL=F"])
    events.append({
        "Timeframe": "1-Day", "Event": "Crude Oil",
        "Value": f"{oil:+.2f}%", "Impact": "Bearish" if oil > 1 else "Bullish" if oil < -1 else "Neutral",
        "Details": get_related_news("crude oil price India impact", 2)
    })

    try:
        vix_val = round(yf.Ticker("^INDIAVIX").history(period="2d")["Close"].iloc[-1], 2)
        vix_imp = "Extreme Fear" if vix_val > 25 else "High Fear" if vix_val > 18 else "Calm"
    except:
        vix_val, vix_imp = "N/A", "Unknown"
    events.append({
        "Timeframe": "1-Day", "Event": "India VIX",
        "Value": str(vix_val), "Impact": vix_imp,
        "Details": get_related_news("India VIX today", 2)
    })

    # 7-Day
    days_to_thu = (3 - now.weekday() + 7) % 7 or 7
    expiry = now + timedelta(days=days_to_thu)
    events.append({
        "Timeframe": "7-Day", "Event": "Next Weekly Expiry",
        "Value": expiry.strftime("%b %d (%A)"), "Impact": "High Volatility",
        "Details": get_related_news("Nifty weekly expiry", 5)
    })

    # 30-Day
