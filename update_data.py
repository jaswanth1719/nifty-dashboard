# update_data.py ← FINAL WORKING VERSION (no syntax errors)

import pandas as pd
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pytz
from pathlib import Path

# -------------------------- Config --------------------------
IST = pytz.timezone("Asia/Kolkata")
DATA_FILE = Path("dashboard_data.csv")
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# -------------------------- 1. News (cached) --------------------------
def get_related_news(topic: str, days: int = 3) -> str:
    cache_file = CACHE_DIR / f"news_{topic.replace(' ', '_')[:40]}_{days}d.cache"
    if cache_file.exists():
        age = datetime.now(IST) - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if age.total_seconds() < 1800:  # 30 minutes
            try:
                return cache_file.read_text(encoding="utf-8")
            except:
                pass

    url = f"https://news.google.com/rss/search?q={topic.replace(' ', '+')}+when:{days}d&hl=en-IN&gl=IN&ceid=IN:en"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        articles = []
        for item in root.findall("./channel/item")[:6]:
            title = item.find("title").text if item.find("title") is not None else ""
            link  = item.find("link").text  if item.find("link")  is not None else ""
            if title and link:
                articles.append(f"{title}|{link}|Recent")
                if len(articles) >= 3:
                    break
        result = "|||".join(articles) if articles else "No recent news"
        cache_file.write_text(result, encoding="utf-8")
        return result
    except:
        return "News unavailable"

# -------------------------- 2. Safe % change --------------------------
def safe_change(tickers, period="5d"):
    for t in tickers:
        try:
            d = yf.download(t, period=period, interval="1d", progress=False, auto_adjust=True, threads=False)
            if len(d) >= 2:
                return round((d["Close"].iloc[-1] / d["Close"].iloc[-2] - 1) * 100, 2)
        except:
            pass
    return 0.0

# -------------------------- 3. Seasonality --------------------------
def get_seasonality():
    try:
        now = datetime.now(IST)
        nifty = yf.download("^NSEI", period="15y", interval="1mo", progress=False, threads=False)
        nifty["Ret"] = nifty["Close"].pct_change() * 100
        monthly = nifty[nifty.index.month == now.month]
        if len(monthly) > 1 and monthly.index[-1].month == now.month and monthly.index[-1].year == now.year:
            monthly = monthly.iloc[:-1]
        avg = monthly["Ret"].mean()
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
        return "N/A", "Neutral"

# -------------------------- 4. Major Economic Events --------------------------
def get_key_events():
    events = []
    now = datetime.now(IST).date()

    # Next RBI Policy
    rbi_dates = ["2025-02-07","2025-04-09","2025-06-06","2025-08-08","2025-10-09","2025-12-05","2026-02-06"]
    next_rbi = next((datetime.strptime(d,"%Y-%m-%d").date() for d in rbi_dates if datetime.strptime(d,"%Y-%m-%d").date() > now), None)
    if next_rbi:
        days = (next_rbi - now).days
        events.append({"Timeframe":"Upcoming","Event":"Next RBI Policy","Value":f"{next_rbi.strftime('%b %d')} ({days} days)","Impact":"Very High","Details":get_related_news("RBI monetary policy",7)})

    # Next US Fed FOMC
    fomc_dates = ["2025-01-29","2025-03-19","2025-04-30","2025-06-18","2025-07-30","2025-09-17","2025-10-29","2025-12-17","2026-01-28"]
    next_fomc = next((datetime.strptime(d,"%Y-%m-%d").date() for d in fomc_dates if datetime.strptime(d,"%Y-%m-%d").date() > now), None)
    if next_fomc:
        days = (next_fomc - now).days
        events.append({"Timeframe":"Upcoming","Event":"Next US Fed (FOMC)","Value":f"{next_fomc.strftime('%b %d')} ({days} days)","Impact":"Very High","Details":get_related_news("FOMC rate decision",7)})

    # Next India CPI (12th of every month)
    cpi = (now.replace(day=1) + timedelta(days=40)).replace(day=12)
    if cpi <= now:
        cpi = (cpi.replace(day=1) + timedelta(days=40)).replace(day=12)
    days = (cpi - now).days
    events.append({"Timeframe":"Upcoming","Event":"Next India CPI","Value":f"{cpi.strftime('%b %d')} ({days} days)","Impact":"High","Details":get_related_news("India CPI inflation",7)})

    # Quarterly Results Season
    if now.month in [1,4,7,10]:
        events.append({"Timeframe":"Ongoing","Event":"Quarterly Results Season","Value":"Active Now","Impact":"High Volatility","Details":get_related_news("Nifty earnings season",10)})

    return events

# -------------------------- 5. Build Dashboard --------------------------
def build_data():
    events = []
    now = datetime.now(IST)

    # 1-Day Triggers
    sp = safe_change(["^GSPC", "SPY"])
    events.append({"Timeframe":"1-Day","Event":"US Market (S&P 500)","Value":f"{sp:+.2f}%","Impact":"Bullish" if sp>0 else "Bearish","Details":get_related_news("S&P 500",2)})

    oil = safe_change(["CL=F"])
    events.append({"Timeframe":"1-Day","Event":"Crude Oil","Value":f"{oil:+.2f}%","Impact":"Bearish" if oil>1 else "Bullish" if oil<-1 else "Neutral","Details":get_related_news("crude oil India",2)})

    try:
        vix = round(yf.Ticker("^INDIAVIX").history(period="2d")["Close"].iloc[-1], 2)
        vix_imp = "Extreme Fear" if vix>25 else "High Fear" if vix>18 else "Calm"
    except:
        vix = "N/A"
        vix_imp = "Unknown"
    events.append({"Timeframe":"1-Day","Event":"India VIX","Value":str(vix),"Impact":vix_imp,"Details":get_related_news("India VIX",2)})

    # 7-Day (Expiries)
    days_to_thu = (3 - now.weekday() + 7) % 7 or 7
    weekly = now + timedelta(days=days_to_thu)
    events.append({"Timeframe":"7-Day","Event":"Next Weekly Expiry","Value":weekly.strftime("%b %d (%A)"),"Impact":"High Volatility","Details":get_related_news("Nifty weekly expiry",5)})

    # 30-Day Seasonality
    val, imp = get_seasonality()
    events.append({"Timeframe":"30-Day","Event":f"{now.strftime('%B')} Seasonality","Value":val,"Impact":imp,"Details":get_related_news("Nifty seasonality",30)})

    # Major Upcoming Events
    events.extend(get_key_events())

    # Meta
    events.append({"Timeframe":"Meta","Event":"Last Updated","Value":now.strftime("%b %d, %H:%M IST"),"Impact":"Live","Details":""})

    df = pd.DataFrame(events)
    df.to_csv(DATA_FILE, index=False)
    return df

# -------------------------- Run --------------------------
if __name__ == "__main__":
    build_data()
    print("Dashboard updated!")
