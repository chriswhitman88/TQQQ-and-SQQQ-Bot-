from alpaca.data.enums import DataFeed  # Make sure this import is at the top

def get_market_data(symbol="QQQ", timeframe=TimeFrame.Hour, limit=100):
    end_dt = datetime.datetime.now(datetime.timezone.utc)
    start_dt = end_dt - datetime.timedelta(days=15)
    
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=start_dt,
        end=end_dt,
        feed=DataFeed.IEX  # Explicitly set free IEX feed
    )
    
    bars = data_client.get_stock_bars(request_params)
    df = bars.df
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol)
    return df
