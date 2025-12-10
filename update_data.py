import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# --- HELPER FUNCTIONS ---
def safe_float(val):
    """Converts a value to float safely, handling Series/Lists."""
    try:
        if isinstance(val, pd.Series):
            val = val.iloc[0]
        return float(val)
    except:
        return 0.0

def get_1_day_impact():
    """Fetches immediate global cues (1-Day View)."""
    events = []
    tickers = ['^GSPC', 'CL=F', '^VIX']
    
    try:
        # Added auto_adjust=True to fix the FutureWarning
        data = yf.download(tickers, period='2d', progress=False, auto_adjust=True)['Close']
        
        # Calculate % Change
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        change = ((latest - prev) / prev) * 100
        
        # 1. US Markets
        us_change = safe_float(change.get('^GSPC', 0))
        events.append({
            "Timeframe": "1-Day", 
            "Event": "🇺🇸 US Market Trend", 
            "Value": f"{us_change:.2f}%", 
            "Impact": "Positive" if us_change > 0 else "Negative"
        })
        
        # 2. Crude Oil
        oil_change = safe_float(change.get('CL=F', 0))
        events.append({
            "Timeframe": "1-Day", 
            "Event": "🛢️ Crude Oil Impact", 
            "Value": f"{oil_change:.2f}%", 
            "Impact": "Negative" if oil_change > 0 else "Positive"
        })
        
        # 3. VIX
        vix_val = safe_float(latest.get('^VIX', 0))
        events.append({
            "Timeframe": "1-Day", 
            "Event": "📉 Market Fear (VIX)", 
            "Value": f"{vix_val:.2f}", 
            "Impact": "High" if vix_val > 20 else "Normal"
        })
            
    except Exception as e:
        print(f"Error in 1-Day: {e}")
        # Add error placeholder so dashboard isn't empty
        events.append({"Timeframe": "1-Day", "Event": "Error Fetching Data", "Value": "0.00%", "Impact": "Info"})
        
    return events

def get_7_day_impact():
    """Calculates Expiry (7-Day View)."""
    events = []
    try:
        today = datetime.now()
        days_ahead = 3 - today.weekday()
        if days_ahead <= 0: days_ahead += 7
        next_expiry = today + timedelta(days=days_ahead)
        
        events.append({
            "Timeframe": "7-Day", 
            "Event": "📅 Weekly Expiry", 
            "Value": next_expiry.strftime('%b %d'), 
            "Impact": "Volatile"
        })
    except Exception as e:
        print(f"Error in 7-Day: {e}")
    return events

def get_30_day_impact():
    """Calculates Seasonality (30-Day View)."""
    events = []
    try:
        current_month = datetime.now().month
        month_name = datetime.now().strftime('%B')
        
        # Fetch 10 years of NIFTY history
        # Added auto_adjust=True
        nifty = yf.download('^NSEI', period='10y', interval='1mo', progress=False, auto_adjust=True)['Close']
        
        # Filter for current month
        nifty_monthly = nifty[nifty.index.month == current_month]
        
        if not nifty_monthly.empty:
            # Calculate average return
            monthly_returns = nifty_monthly.pct_change() * 100
            raw_mean = monthly_returns.mean()
            
            # FIX: Ensure we have a single float, not a Series
            avg_return = safe_float(raw_mean)
            
            events.append({
                "Timeframe": "30-Day",
                "Event": f"📊 {month_name} Seasonality",
                "Value": f"Avg: {avg_return:.2f}%",
                "Impact": "Bullish" if avg_return > 0 else "Bearish"
            })
    except Exception as e:
        print(f"Error in 30-Day: {e}")
        
    return events

# --- MAIN EXECUTION ---
all_events = []
all_events.extend(get_1_day_impact())
all_events.extend(get_7_day_impact())
all_events.extend(get_30_day_impact())

# TIMESTAMP
ist = pytz.timezone('Asia/Kolkata')
now = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')
all_events.append({"Timeframe": "Meta", "Event": "Last Updated", "Value": now, "Impact": "Info"})

# SAVE
df = pd.DataFrame(all_events)
df.to_csv("dashboard_data.csv", index=False)
print("✅ Dashboard Data Updated Successfully")
