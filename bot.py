import os
import pandas as pd
from datetime import datetime, timezone
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Fetch keys securely from GitHub environment variables
API_KEY = os.getenv('APCA_API_KEY_ID')
SECRET_KEY = os.getenv('APCA_API_SECRET_KEY')

# Initialize Alpaca clients in paper mode
trading_client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(api_key=API_KEY, secret_key=SECRET_KEY)

def run_strategy_with_execution():
    print("Fetching latest hourly market data from Alpaca...")
    
    symbols = ["TQQQ", "SQQQ", "QQQ"]
    request_params = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Hour,
        limit=1500
    )
    
    bars = data_client.get_stock_bars(request_params)
    df_dict = {}
    
    for symbol in symbols:
        try:
            df_dict[symbol] = bars.df.loc[symbol]
        except KeyError:
            print(f"Warning: Could not fetch data for {symbol}")
            
    if "TQQQ" not in df_dict:
        print("Data fetch incomplete. Retrying later.")
        return

    tqqq_df = df_dict["TQQQ"]
    
    # --- Indicator Calculations ---
    tqqq_df['EMA_5'] = tqqq_df['close'].ewm(span=5, adjust=False).mean()
    tqqq_df['EMA_13'] = tqqq_df['close'].ewm(span=13, adjust=False).mean()
    
    delta = tqqq_df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    tqqq_df['RSI'] = 100 - (100 / (1 + rs))
    
    latest = tqqq_df.iloc[-1]
    current_price = latest['close']
    ema_5 = latest['EMA_5']
    ema_13 = latest['EMA_13']
    rsi = latest['RSI']
    
    print(f"\n--- Latest Bar Analysis (TQQQ) ---")
    print(f"Price: ${current_price:.2f} | EMA 5: ${ema_5:.2f} | EMA 13: ${ema_13:.2f} | RSI: {rsi:.1f}")
    
    # Check current open positions in your paper account
    positions = trading_client.get_all_positions()
    position_map = {p.symbol: p for p in positions if p.symbol in ["TQQQ", "SQQQ"]}
    
    # --- Strategy Signal Logic ---
    is_bullish = (ema_5 > ema_13) and (rsi > 50)
    is_bearish = ema_5 < ema_13
    
    target_symbol = None
    if is_bullish:
        target_symbol = "TQQQ"
        print("Signal: BULLISH -> Target is TQQQ")
    elif is_bearish:
        target_symbol = "SQQQ"
        print("Signal: BEARISH -> Target is SQQQ")
    else:
        print("Signal: NEUTRAL -> Maintaining current state.")
        return

    # --- Automated Order Execution Logic ---
    holding_target = target_symbol in position_map
    
    if not holding_target:
        print(f"Executing rotation to {target_symbol}...")
        
        # 1. Close any existing opposite positions first
        for sym in list(position_map.keys()):
            if sym != target_symbol:
                print(f"Liquidating existing position in {sym}...")
                trading_client.close_position(sym)
        
        # 2. Calculate position size using available cash (95% allocation)
        account = trading_client.get_account()
        available_cash = float(account.cash) * 0.95
        
        target_price = df_dict[target_symbol].iloc[-1]['close']
        shares_to_buy = int(available_cash / target_price)
        
        if shares_to_buy > 0:
            # Add a slight limit offset buffer to ensure fill
            limit_price = round(target_price * 1.001, 2)
            print(f"Submitting paper buy order: {shares_to_buy} shares of {target_symbol} at ${limit_price}...")
            
            order_data = LimitOrderRequest(
                symbol=target_symbol,
                qty=shares_to_buy,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price
            )
            
            response = trading_client.submit_order(order_data)
            print(f"Paper Order Successfully Placed! Order ID: {response.id}")
        else:
            print("Insufficient cash balance to purchase shares.")
    else:
        print(f"Already holding target symbol ({target_symbol}). No rebalance needed.")

if __name__ == "__main__":
    run_strategy_with_execution()
