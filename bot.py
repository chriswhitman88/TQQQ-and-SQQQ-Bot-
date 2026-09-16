# 1. Update your Alpaca data imports at the top
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# 2. Update get_market_data() to request the IEX feed
def get_market_data(symbol="QQQ", timeframe=TimeFrame.Hour, limit=100):
    """Fetches historical stock bars to calculate indicators."""
    end_dt = datetime.datetime.now(datetime.timezone.utc)
    start_dt = end_dt - datetime.timedelta(days=15)
    
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=start_dt,
        end=end_dt,
        feed=DataFeed.IEX  # <-- Real-time data on free tier
    )
    
    bars = data_client.get_stock_bars(request_params)
    df = bars.df
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol)
    return df
