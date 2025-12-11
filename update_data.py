# update_data.py  ← FINAL VERSION WITH ALL MAJOR EVENTS (except FII/DII)

import pandas as pd
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pytz
from pathlib import Path

IST = pytz.timezone("Asia/Kolkata")
DATA_FILE = Path("dashboard_data.csv")
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# ===================================================================
# 1. Cached News
# ===================================================================
def get_related_news(topic: str, days: int = 3) -> str:
    cache_file = CACHE_DIR / f"news_{topic.replace(' ', '_')[:40]}_{days}d.cache"
    if cache_file.exists():
        age = datetime.now(IST) - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if age.total_seconds() < 1800:
            try: return cache_file.read_text(encoding="utf-8")
            except: pass

    url = f"https://news.google.com/rss/search?q={topic.replace(' ', '+')}+when:{days}d&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        articles = []
        for item in root.findall("./channel/item")[:6]:
            t = item.find("title").text if item.find("title") is not None else ""
            l = item.find("link").text  if item.find("link")  is not None else ""
            if t and l:
                articles.append(f"{t}|{l}|Recent")
                if len(articles) >= 3: break
        result = "|||".join(articles) if articles else "No recent news"
        cache_file.write_text(result, encoding="utf-8")
        return result
    except:
        return "News unavailable"

# ===================================================================
# 2. Safe % change
# ===================================================================
def safe_change(tickers, period="5d"):
    for t in tickers:
        try:
            d = yf.download(t, period=period, interval="1d", progress=False, auto_adjust=True)
            if len(d) >= 2:
                return round((d["Close"].iloc[-1] / d["Close"].iloc[-2] - 1) * 100, 2)
        except: pass
    return 0.0

# ===================================================================
# 3. Seasonality
# ===================================================================
def get_seasonality():
    try:
        now = datetime.now(IST)
        nifty = yf.download("^NSEI", period="15y", interval="1mo", progress=False)
        nifty["Ret"] = nifty["Close"].pct_change() * 100
        monthly = nifty[nifty.index.month == now.month]
        if len(monthly) > 1 and monthly.index[-1].month == now.month and monthly.index[-1].year == now.year:
            monthly = monthly.iloc[:-1]
        avg = monthly["Ret"].mean()
        if avg > 1.2:   imp = "Strongly Bullish"
        elif avg > 0.5: imp = "Bullish"
        elif avg < -1.2:imp = "Strongly Bearish"
        elif avg < -0.5:imp = "Bearish"
        else:           imp = "Neutral"
        return f"{avg:+.2f}%", imp
    except: return "N/A", "Neutral"

# ===================================================================
# 4. Economic Calendar Events (hard-coded 2025–2026 – super reliable)
# ===================================================================
def get_key_events():
    events = []
    now = datetime.now(IST).date()

    # RBI Policy Dates 2025–2026
    rbi_dates = [
        ("2025-02-07", "Feb 2025"), ("2025-04-09", "Apr 2025"), ("2025-06-06", "Jun 2025"),
        ("2025-08-08", "Aug 2025"), ("2025-10-09", "Oct 2025"), ("2025-12-05", "Dec 2025"),
        ("2026-02-06", "Feb 2026")
    ]
    next_rbi = min((datetime.strptime(d, "%Y-%m-%d").date() for d, _ in rbi_dates if datetime.strptime(d, "%Y-%m-%d").date() > now), default=None)
    if next_rbi:
        days = (next_rbi - now).days
        events.append({"Timeframe":"Upcoming", "Event":"Next RBI Policy", "Value":f"{next_rbi.strftime('%b %d')} ({days} days)", "Impact":"Very High", "Details":get_related_news("RBI monetary policy",7)})

    # US FOMC Dates 2025–2026
    fomc_dates = [
        "2025-01-29","2025-03-19","2025-04-30","2025-06-18",
        "2025-07-30","2025-09-17","2025-10-29","2025-12-17",
        "2026-01-28","2026-03-18"
    ]
    next_fomc = min((datetime.strptime(d, "%Y-%m-%d").date() for d in fomc_dates if datetime.strptime(d, "%Y-%m-%d").date() > now), default=None)
    if next_fomc:
        days = (next_fomc - now).days
        events.append({"Timeframe":"Upcoming", "Event":"Next US Fed (FOMC)", "Value":f"{next_fomc.strftime('%b %d')} ({days} days)", "Impact":"Very High", "Details":get_related_news("FOMC Fed rate decision",7)})

    # India CPI Dates (usually 12th of every month)
    cpi_date = (now.replace(day=1) + timedelta(days=32)).replace(day=12)
    if cpi_date < now: cpi_date = (cpi_date.replace(day=1) + timedelta(days=40)).replace(day=12)
    days = (cpi_date - now).days
    events.append({"Timeframe":"Upcoming", "Event":"Next India CPI", "Value":f"{cpi_date.strftime('%b %d')} ({days} days)", "Impact":"High", "Details":get_related_news("India CPI inflation data",7)})

    # Quarterly Results Season
    month = now.month
    if month in [1,4,7,10]:
        events.append({"Timeframe":"Ongoing", "Event":"Qtr Results Season", "Value":"Jan | Apr | Jul | Oct", "Impact":"High Volatility", "Details":get_related_news("Nifty earnings season",10)})
    
    return events

# ===================================================================
# 5. Build full dashboard
# ===================================================================
def build_data():
    events = []
    now = datetime.now(IST)

    # ── 1-Day ──
    events.append({"Timeframe":"1-Day","Event":"US Market (S&P500)","Value":safe_change(["^GSPC","SPY"]),"Value":f"{safe_change(['^GSPC','SPY']):+.2f}%","Impact":"Bullish" if safe_change(["^GSPC"])>0 else "Bearish","Details":get_related_news("S&P 500 today",2)})
    events.append({"Timeframe":"1-Day","Event":"Crude Oil","Value":f"{safe_change(['CL=F']):+.2f}%","Impact":"Bearish" if safe_change(['CL=F'])>1 else "Bullish" if safe_change(['CL=F'])<-1 else "Neutral","Details":get_related_news("crude oil price India",2)})
    try:
        vix = round(yf.Ticker("^INDIAVIX").history(period="2d")["Close"].iloc[-1],2)
        vix_i = "Extreme Fear" if vix>25 else "High Fear" if vix>18 else "Calm"
    except: vix, vix_i = "N/A","Unknown"
    events.append({"Timeframe":"1-Day","Event":"India VIX","Value":str(vix),"Impact":vix_i,"Details":get_related_news("India VIX",2)})

    # ── 7-Day ──
    days_to_thu = (3 - now.weekday() + 7) % 7 or 7
    weekly = now + timedelta(days=days_to_thu)
    monthly = weekly
    while monthly.weekday() != 3 or (monthly - now).days > 30: monthly += timedelta(days=7)
    events.append({"Timeframe":"7-Day","Event":"Next Weekly Expiry","Value":weekly.strftime("%b %d (%A)"),"Impact":"High Volatility","Details":get_related_news("Nifty weekly expiry",5)})
    events.append({"Timeframe":"7-Day","Event":"Next Monthly Expiry","Value":monthly.strftime("%b %d (%A)"),"Impact":"Very High Volatility","Details":get_related_news("Nifty monthly expiry",10)})

    # ── 30-Day ──
    val, imp = get_seasonality()
    events.append({"Timeframe":"30-Day","Event":f"{now.strftime('%B')} Seasonality","Value":val,"Impact":imp,"Details":get_related_news(f"Nifty {now.strftime('%B')} seasonality",30)})

    # ── Upcoming & Upcoming Events ──
    events.extend(get_key_events())

    # ── Meta ──
    events.append({"Timeframe":"Meta","Event":"Last Updated","Value":now.strftime("%b %d, %H:%M IST"),"Impact":"Live","Details":""})

    df = pd.DataFrame(events)
    df.to_csv(DATA_FILE, index=False)
    return df

if __name__ == "__main__":
    build_data()
