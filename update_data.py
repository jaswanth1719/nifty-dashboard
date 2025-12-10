import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# --- HELPER FUNCTIONS ---
def get_change(ticker_symbol):
    """
    Fetches the % change of a ticker over the last 2 trading days.
    Uses history() which is more stable than download().
    """
    try:
        # Fetch 5 days to be safe against weekends/holidays
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="5d")
        
        if len(hist) < 2:
            return 0.0
            
        # Get last two closes
        latest = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        
        # Calculate Percentage
        change = ((latest - prev) / prev) * 100
        return float(change)
    except Exception as e:
        print(f"Error fetching {ticker_symbol}: {e}")
        return 0.0

def get_price(ticker_symbol):
    """Fetches the latest absolute price."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="2d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
        return 0.0
    except:
        return 0.0

# --- MAIN LOGIC ---

def get_1_day_impact():
    events = []
    
    # 1. US Markets (Try S&P 500, Fallback to SPY ETF if Index fails)
    us_change = get_change("^GSPC")
    if us_change == 0.0:
        us_change = get_change("SPY") # Fallback
        
    events.append({
        "Timeframe": "1-Day", 
        "Event": "🇺🇸 US Market Trend", 
        "Value": f"{us_change:.2f}%", 
        "Impact": "Positive" if us_change > 0 else "Negative"
    })

    # 2. Crude Oil
    oil_change = get_change("CL=F")
    events.append({
        "Timeframe": "1-Day", 
        "Event": "🛢️ Crude Oil Impact", 
        "Value": f"{oil_change:.2f}%", 
        "Impact": "Negative" if oil_change > 0 else "Positive"
    })

    # 3. VIX
    vix_val = get_price("^VIX")
    events.append({
        "Timeframe": "1-Day", 
        "Event": "📉 Market Fear (VIX)", 
        "Value": f"{vix_val:.2f}", 
        "Impact": "High" if vix_val > 20 else "Normal"
    })
    
    return events

def get_7_day_impact():
    events = []
    try:
        today = datetime.now()
        # Calculate Next Thursday
        days_ahead = 3 - today.weekday()
        if days_ahead <= 0: days_ahead += 7
        next_expiry = today + timedelta(days=days_ahead)
        
        events.append({
            "Timeframe": "7-Day", 
            "Event": "📅 Weekly Expiry", 
            "Value": next_expiry.strftime('%b %d'), 
            "Impact": "Volatile"
        })
    except:
        pass
    return events

def get_30_day_impact():
    events = []
    try:
        current_month = datetime.now().month
        month_name = datetime.now().strftime('%B')
        
        # Fetch NIFTY History
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="5y", interval="1mo")
        
        if not hist.empty:
            # Filter for current month
            hist_monthly = hist[hist.index.month == current_month]
            
            if not hist_monthly.empty:
                monthly_returns = hist_monthly['Close'].pct_change() * 100
                avg_return = float(monthly_returns.mean())
                
                # Check for NaN result
                if pd.isna(avg_return): avg_return = 0.0
                
                events.append({
                    "Timeframe": "30-Day",
                    "Event": f"📊 {month_name} Seasonality",
                    "Value": f"Avg: {avg_return:.2f}%",
                    "Impact": "Bullish" if avg_return > 0 else "Bearish"
                })
    except Exception as e:
        print(f"Error in 30-Day: {e}")
        
    return events

# --- EXECUTION ---
all_events = []
all_events.extend(get_1_day_impact())
all_events.extend(get_7_day_impact())
all_events.extend(get_30_day_impact())

# Timestamp
ist = pytz.timezone('Asia/Kolkata')
now = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')
all_events.append({"Timeframe": "Meta", "Event": "Last Updated", "Value": now, "Impact": "Info"})

# Save
df = pd.DataFrame(all_events)
df.to_csv("dashboard_data.csv", index=False)
print("✅ Fixed: Dashboard Data Updated")
