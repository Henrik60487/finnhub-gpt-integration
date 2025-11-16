import requests
import time
from fastapi import FastAPI

API_KEY = "d4c6s51r01qoua32po1gd4c6s51r01qoua32po20"
BASE_URL = "https://finnhub.io/api/v1"

app = FastAPI()

def get_stock_candles(symbol: str, resolution: str = "1", days_back: int = 365):
    now = int(time.time())
    past = now - days_back * 24 * 60 * 60
    url = f"{BASE_URL}/stock/candle"
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "from": past,
        "to": now,
        "token": API_KEY
    }
    r = requests.get(url, params=params)
    data = r.json()
    if data.get("s") != "ok":
        raise ValueError(f"Error fetching candles: {data}")
    return data

@app.get("/candles")
def candles(symbol: str = "AAPL", resolution: str = "1", days_back: int = 365):
    return get_stock_candles(symbol, resolution, days_back)
