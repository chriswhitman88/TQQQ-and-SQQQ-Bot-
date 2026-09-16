import os
import datetime
import pandas as pd
import pandas_ta as ta

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed

# Environment Variables from GitHub Secrets
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    raise ValueError("Missing ALPACA_API_KEY or ALPACA_SECRET_KEY environment variables.")

# Initialize Clients (Paper Trading enabled)
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

def get_market_data(symbol="QQQ", timeframe=TimeFrame.Hour, limit=100):
    """Fetches historical market data from Alpaca using the free IEX feed."""
    end_dt = datetime.datetime.now(datetime.timezone.utc)
    start_dt = end_dt - datetime.timedelta(days=15)
    
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=start_dt,
        end=end_dt,
        limit=limit,
        feed=DataFeed.IEX  # Explicitly enforces the free IEX feed
    )
    
    bars = data_client.get_stock_bars(request_params)
    df = bars.df
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol)
    return df

def calculate_indicators(df):
    """Calculates EMA 9, EMA 21, and RSI 14 indicators."""
    df['ema_9'] = ta.ema(df['close'], length=9)
    df['ema_21'] = ta.ema(df['close'], length=21)
    df['rsi'] = ta.rsi(df['close'], length=14)
    return df

def get_position(symbol):
    """Checks if there is an existing open position for the given symbol."""
    try:
        position = trading_client.get_open_position(symbol)
        return float(position.qty)
    except Exception:
        return 0.0

def execute_order(symbol, side, qty):
    """Executes a market order on Alpaca paper account."""
    market_order_data = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=side,
        time_in_force=TimeInForce.GTC
    )
    order = trading_client.submit_order(order_data=market_order_data)
    print(f"Executed {side.value} order for {qty} shares of {symbol}. Order ID: {order.id}")

def run_strategy_with_execution():
    """Main strategy execution routine."""
    print("Fetching latest hourly market data from Alpaca (IEX Feed)...")
    df = get_market_data("QQQ")
    df = calculate_indicators(df)
    
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    
    print(f"Latest Timestamp: {latest.name}")
    print(f"Close: {latest['close']:.2f} | EMA9: {latest['ema_9']:.2f} | EMA21: {latest['ema_21']:.2f} | RSI: {latest['rsi']:.2f}")

    # Crossover Logic
    bullish_cross = (previous['ema_9'] <= previous['ema_21']) and (latest['ema_9'] > latest['ema_21'])
    bearish_cross = (previous['ema_9'] >= previous['ema_21']) and (latest['ema_9'] < latest['ema_21'])

    tqqq_qty = get_position("TQQQ")
    sqqq_qty = get_position("SQQQ")

    if bullish_cross:
        print("BULLISH SIGNAL DETECTED (EMA 9 crossed above EMA 21)")
        if sqqq_qty > 0:
            print("Closing SQQQ short hedge...")
            execute_order("SQQQ", OrderSide.SELL, sqqq_qty)
        if tqqq_qty == 0:
            print("Buying TQQQ...")
            execute_order("TQQQ", OrderSide.BUY, 10) # Adjust quantity as needed

    elif bearish_cross:
        print("BEARISH SIGNAL DETECTED (EMA 9 crossed below EMA 21)")
        if tqqq_qty > 0:
            print("Closing TQQQ long position...")
            execute_order("TQQQ", OrderSide.SELL, tqqq_qty)
        if sqqq_qty == 0:
            print("Buying SQQQ...")
            execute_order("SQQQ", OrderSide.BUY, 10) # Adjust quantity as needed

    else:
        print("NO CROSSOVER SIGNAL DETECTED. Maintaining current positions.")

if __name__ == "__main__":
    run_strategy_with_execution()
