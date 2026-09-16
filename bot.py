import os
import datetime
import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# 1. Fetch and sanitize API credentials
API_KEY = (os.getenv("API_KEY") or os.getenv("APCA_API_KEY_ID") or "").strip()
SECRET_KEY = (os.getenv("SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY") or "").strip()

if not API_KEY or not SECRET_KEY:
    raise ValueError("Missing or invalid Alpaca API credentials. Ensure secrets are set properly.")

# 2. Initialize Alpaca clients
trading_client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(api_key=API_KEY, secret_key=SECRET_KEY)

def get_market_data(symbol="QQQ", timeframe=TimeFrame.Hour, limit=100):
    """Fetches historical stock bars to calculate indicators."""
    end_dt = datetime.datetime.now(datetime.timezone.utc)
    start_dt = end_dt - datetime.timedelta(days=15)
    
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=start_dt,
        end=end_dt
    )
    
    bars = data_client.get_stock_bars(request_params)
    df = bars.df
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol)
    return df

def calculate_indicators(df):
    """Calculates EMA and RSI indicators for decision logic."""
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

def execute_rotation(target_symbol):
    """Sells existing opposite leverage position and buys target asset."""
    positions = trading_client.get_all_positions()
    current_symbols = [p.symbol for p in positions]
    
    # Close positions in the opposing ticker if present
    opposite_symbol = "SQQQ" if target_symbol == "TQQQ" else "TQQQ"
    if opposite_symbol in current_symbols:
        print(f"Closing position in {opposite_symbol}...")
        trading_client.close_position(opposite_symbol)
        
    # Check if already holding target symbol
    if target_symbol in current_symbols:
        print(f"Already holding target symbol: {target_symbol}. No trade needed.")
        return

    # Account buying power check
    account = trading_client.get_account()
    buying_power = float(account.buying_power)
    
    if buying_power > 100:
        print(f"Submitting market order for {target_symbol} using available cash...")
        order_data = MarketOrderRequest(
            symbol=target_symbol,
            notional=round(buying_power * 0.95, 2),  # Use 95% of available funds
            side=OrderSide.BUY,
            time_in_force=TimeInForce.GTC
        )
        order = trading_client.submit_order(order_data)
        print(f"Order executed for {target_symbol}: ID {order.id}")
    else:
        print("Insufficient buying power to execute order.")

def run_strategy_with_execution():
    """Main execution entry point."""
    print("Fetching latest hourly market data from Alpaca...")
    df = get_market_data("QQQ")
    df = calculate_indicators(df)
    
    latest = df.iloc[-1]
    ema_9 = latest['EMA_9']
    ema_21 = latest['EMA_21']
    rsi = latest['RSI']
    
    print(f"Latest QQQ Data | Close: {latest['close']:.2f} | EMA9: {ema_9:.2f} | EMA21: {ema_21:.2f} | RSI: {rsi:.2f}")
    
    # Strategy Decision Logic
    if ema_9 > ema_21 and rsi > 45:
        print("Signal: BULLISH -> Rotating to TQQQ")
        execute_rotation("TQQQ")
    elif ema_9 < ema_21 and rsi < 55:
        print("Signal: BEARISH -> Rotating to SQQQ")
        execute_rotation("SQQQ")
    else:
        print("Signal: NEUTRAL -> Holding current positions.")

if __name__ == "__main__":
    run_strategy_with_execution()
