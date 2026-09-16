import datetime
import pandas as pd
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# Ensure your client is initialized
# data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

def get_market_data(symbol="QQQ", timeframe=TimeFrame.Hour, limit=10000):
    # End timestamp set to current UTC time
    end_dt = datetime.datetime.now(datetime.timezone.utc)
    start_dt = end_dt - datetime.timedelta(days=15)
    
    # Passing feed=DataFeed.IEX resolves the 403 "subscription does not permit querying recent SIP data" error
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=start_dt,
        end=end_dt,
        limit=limit,
        feed=DataFeed.IEX
    )
    
    bars = data_client.get_stock_bars(request_params)
    df = bars.df
    
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol)
        
    return df
