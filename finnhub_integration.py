from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx
import time
import numpy as np

app = FastAPI(title="Yahoo Finance Minute Data API")

YF_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


@app.get("/.well-known/health")
def health():
    return {"status": "ok"}


@app.get("/minute-data")
async def get_minute_data(
    symbols: str = Query(..., description="Comma-separated stock symbols, e.g. AAPL,MSFT"),
    minutes: int = Query(60, ge=1, le=4320, description="How many minutes back to fetch (max 4320 = 3 days)"),
):
    """
    Fetch 1-minute historical data for the last N minutes from Yahoo Finance.
    NO API key required.
    Yahoo Finance provides up to ~7 days of 1-minute data for most stocks.
    """

    symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbols_list:
        raise HTTPException(status_code=400, detail="No valid symbols provided.")

    now = int(time.time())
    period_seconds = minutes * 60
    start = now - period_seconds

    results = {
        "requested_minutes": minutes,
        "from": start,
        "to": now,
        "resolution": "1",
        "symbols": {}
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        for sym in symbols_list:
            url = YF_CHART_URL.format(symbol=sym)
            params = {
                "interval": "1m",
                "range": f"{minutes}m" if minutes <= 1440 else "7d"
            }

            response = await client.get(url, params=params)

            if response.status_code != 200:
                results["symbols"][sym] = {
                    "status": "error",
                    "message": f"HTTP {response.status_code} from Yahoo Finance"
                }
                continue

            data = response.json()

            try:
                result = data["chart"]["result"][0]
                timestamps = result["timestamp"]
                indicators = result["indicators"]["quote"][0]

                candles = []
                for i, ts in enumerate(timestamps):
                    candles.append({
                        "timestamp": ts,
                        "open": indicators["open"][i],
                        "high": indicators["high"][i],
                        "low": indicators["low"][i],
                        "close": indicators["close"][i],
                        "volume": indicators["volume"][i],
                    })

                results["symbols"][sym] = {
                    "status": "ok",
                    "count": len(candles),
                    "candles": candles
                }

            except Exception as e:
                results["symbols"][sym] = {
                    "status": "error",
                    "message": f"Failed to parse Yahoo response: {str(e)}"
                }

    return JSONResponse(results)
