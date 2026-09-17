import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import DataFeed
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

print("DEBUG: Running the newest bot.py file successfully!")

API_KEY = os.environ.get("APO_API_KEY") or os.environ.get("APCA_API_KEY_ID")
API_SECRET = os.environ.get("APO_API_SECRET") or os.environ.get("APCA_API_SECRET_KEY")

if not API_KEY or not API_SECRET:
    API_KEY = os.environ.get("APCA_API_KEY_ID")
    API_SECRET = os.environ.get("APCA_API_SECRET_KEY")

if API_KEY: API_KEY = API_KEY.strip()
if API_SECRET: API_SECRET = API_SECRET.strip()

trading_client = TradingClient(API_KEY, API_SECRET, paper=True)
data_client = StockHistoricalDataClient(API_KEY, API_SECRET)

def fetch_market_data():
    print("Fetching latest hourly market data from Alpaca...")
    request_params = StockBarsRequest(
        symbol_or_symbols=["QQQ"], 
        timeframe=TimeFrame(1, TimeFrameUnit.Hour), 
        start=datetime.now() - timedelta(days=7),
        feed=DataFeed.IEX
    )
    bars = data_client.get_stock_bars(request_params)
    df = bars.df
    
    # --- SAFEGUARDS TO PREVENT EMPTY DATAFRAMES & KEYERRORS ---
    if df is None or df.empty:
        raise ValueError("Fetched empty DataFrame from Alpaca! Check network or market status.")
        
    if isinstance(df.index, pd.MultiIndex):
        if "symbol" in df.index.names:
            df = df.xs("QQQ", level="symbol")
        else:
            df = df.reset_index(level=0, drop=True)
            
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # ----------------------------------------------------------

    return df.reset_index()

def calculate_indicators(df):
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def get_current_position():
    try:
        position = trading_client.get_open_position("TQQQ")
        return "TQQQ", float(position.qty)
    except Exception:
        try:
            position = trading_client.get_open_position("SQQQ")
            return "SQQQ", float(position.qty)
        except Exception:
            return None, 0.0

def execute_rotation(target_symbol):
    current_symbol, current_qty = get_current_position()
    if current_symbol == target_symbol:
        print(f"Already holding {target_symbol}. No rotation needed.")
        return

    if current_symbol:
        print(f"Closing position in {current_symbol}...")
        trading_client.close_position(current_symbol)
    
    account = trading_client.get_account()
    available_cash = float(account.cash)
    
    if available_cash < 1.0:
        print("Warning: Insufficient cash available to trade.")
        return

    price_request = StockBarsRequest(
        symbol_or_symbols=[target_symbol], timeframe=TimeFrame(1, TimeFrameUnit.Minute), limit=1, feed=DataFeed.IEX
    )
    price_bars = data_client.get_stock_bars(price_request)
    current_price = float(price_bars.df.iloc[-1]['close'])
    
    shares_qty = int(available_cash / current_price)
    
    if shares_qty < 1:
        print("Warning: Available cash is less than the price of a single share.")
        return

    print(f"Submitting market order for {shares_qty} whole shares of {target_symbol}...")
    
    order_req = MarketOrderRequest(
        symbol=target_symbol,
        qty=shares_qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY
    )
    
    order = trading_client.submit_order(order_req)
    print(f"Successfully ordered {target_symbol}! Order ID: {order.id}")

def run_strategy_with_execution():
    df = fetch_market_data()
    df = calculate_indicators(df)
    latest = df.iloc[-1]
    close, ema9, ema21, rsi = latest['close'], latest['EMA9'], latest['EMA21'], latest['RSI']
    
    print(f"Latest QQQ Data | Close: {close:.2f} | EMA9: {ema9:.2f} | EMA21: {ema21:.2f} | RSI: {rsi:.2f}")
    
    if ema9 > ema21:
        print("Signal: BULLISH -> Rotating to TQQQ")
        execute_rotation("TQQQ")
    else:
        print("Signal: BEARISH -> Rotating to SQQQ")
        execute_rotation("SQQQ")

if __name__ == "__main__":
    run_strategy_with_execution()
