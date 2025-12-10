import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# --- CONFIGURATION ---
# We track the "Big 5" weights in NIFTY. 
# If they move, NIFTY moves.
TOP_STOCKS = {
    'RELIANCE.NS': 'Reliance',
    'HDFCBANK.NS': 'HDFC Bank',
    'INFY.NS': 'Infosys',
    'TCS.NS': 'TCS',
    'ICICIBANK.NS': 'ICICI Bank'
}

def get_1_day_impact():
    """Fetches immediate global cues."""
    tickers = ['^GSPC', 'CL=F', '^VIX'] # S&P500, Oil, VIX
    try:
        data = yf.download(tickers, period='2d', progress=False)['Close']
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        change = ((latest - prev) / prev) * 100
        
        return [
            {"Timeframe": "1-Day", "Event": "🇺🇸 US Market Trend", "Value": f"{change['^GSPC']:.2f}%", "Impact": "Positive" if change['^GSPC'] > 0 else "Negative"},
            {"Timeframe": "1-Day", "Event": "🛢️ Crude Oil Impact", "Value": f"{change['CL=F']:.2f}%", "Impact": "Negative" if change['CL=F'] > 0 else "Positive"}, # Oil UP is bad
            {"Timeframe": "1-Day", "Event": "📉 Market Fear (VIX)", "Value": f"{latest['^VIX']:.2f}", "Impact": "High" if latest['^VIX'] > 20 else "Normal"}
        ]
    except:
        return []

def get_7_day_impact():
    """Calculates Expiry and looks for upcoming earnings."""
    events = []
    today = datetime.now()
    
    # 1. Next Weekly Expiry (Thursday)
    days_ahead = 3 - today.weekday()
    if days_ahead <= 0: days_ahead += 7
    next_expiry = today + timedelta(days=days_ahead)
    events.append({
        "Timeframe": "7-Day", 
        "Event": "📅 Weekly Expiry", 
        "Value": next_expiry.strftime('%b %d'), 
        "Impact": "Volatile"
    })
    
    # 2. Earnings Check (Next 7 Days)
    # Note: Free APIs for exact future earnings dates are rare. 
    # We use a placeholder logic here or check yfinance if available.
    # Real reliable future earnings require paid APIs, so we note "Check Key Stocks".
    
    return events

def get_30_day_impact():
    """Calculates Historical Seasonality for the current month."""
    events = []
    current_month = datetime.now().month
    month_name = datetime.now().strftime('%B')
    
    # Fetch 10 years of NIFTY history
    nifty = yf.download('^NSEI', period='10y', interval='1mo', progress=False)['Close']
    
    # Filter for current month only
    nifty_monthly = nifty[nifty.index.month == current_month]
    
    # Calculate returns for this specific month over years
    monthly_returns = nifty_monthly.pct_change() * 100
    avg_return = monthly_returns.mean()
    win_rate = (monthly_returns > 0).sum() / len(monthly_returns) * 100
    
    events.append({
        "Timeframe": "30-Day",
        "Event": f"📊 {month_name} Seasonality",
        "Value": f"Avg: {avg_return:.2f}%",
        "Impact": "Bullish" if avg_return > 0 else "Bearish"
    })
    
    events.append({
        "Timeframe": "30-Day",
        "Event": "📈 Historical Win Rate",
        "Value": f"{int(win_rate)}% Positive",
        "Impact": "Info"
    })
    
    return events

# --- MAIN EXECUTION ---
all_events = []
all_events.extend(get_1_day_impact())
all_events.extend(get_7_day_impact())
all_events.extend(get_30_day_impact())

# Add Timestamp
ist = pytz.timezone('Asia/Kolkata')
now = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')
all_events.append({"Timeframe": "Meta", "Event": "Last Updated", "Value": now, "Impact": "Info"})

# Save
df = pd.DataFrame(all_events)
df.to_csv("dashboard_data.csv", index=False)
print("✅ Structured Dashboard Data Updated")
