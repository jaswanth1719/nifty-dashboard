import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

def fetch_data():
    # Define tickers
    # ^GSPC = S&P 500 (US Impact)
    # ^NSEI = NIFTY 50
    # CL=F = Crude Oil
    # ^VIX = CBOE Volatility Index (Global Sentiment)
    # ^INDIAVIX = India VIX (Need to check if yf supports it, often safer to use ^VIX as proxy or calculate)
    
    # Note: Yahoo Finance ticker for India VIX can be inconsistent. 
    # We will use US VIX as a global sentiment proxy if India VIX fails, or skip it.
    tickers = ['^GSPC', '^NSEI', 'CL=F', '^VIX']
    
    try:
        data = yf.download(tickers, period='5d', progress=False)['Close']
        
        # Calculate % Change
        # We use iloc[-1] (latest) and iloc[-2] (previous) to calculate change manually for accuracy
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        changes = ((latest - prev) / prev) * 100
        
        # Get current time in IST
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')

        # Structure the data
        dashboard_data = [
            {"Metric": "US Markets (S&P 500)", "Value": f"{changes['^GSPC']:.2f}%", "Status": "Bullish" if changes['^GSPC'] > 0 else "Bearish"},
            {"Metric": "Crude Oil", "Value": f"{changes['CL=F']:.2f}%", "Status": "Bearish" if changes['CL=F'] > 0 else "Bullish"}, # Inverse logic for Oil
            {"Metric": "NIFTY 50 (Last Close)", "Value": f"{changes['^NSEI']:.2f}%", "Status": "Bullish" if changes['^NSEI'] > 0 else "Bearish"},
            {"Metric": "Global VIX", "Value": f"{data['^VIX'].iloc[-1]:.2f}", "Status": "Volatile" if data['^VIX'].iloc[-1] > 20 else "Stable"},
            {"Metric": "Last Updated (IST)", "Value": now, "Status": "Info"}
        ]
        
        return dashboard_data
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

# Execute and Save
data = fetch_data()
if data:
    df = pd.DataFrame(data)
    df.to_csv("dashboard_data.csv", index=False)
    print("✅ CSV updated successfully")
else:
    print("❌ Failed to update CSV")
