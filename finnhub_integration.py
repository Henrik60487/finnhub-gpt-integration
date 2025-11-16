from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import os
import time
import httpx

app = FastAPI(title="Finnhub Minute Data API")

# Your Finnhub API key will come from an environment variable
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY")


@app.get("/.well-known/health")
def health():
    """Health check to verify service is running."""
    return {"status": "ok"}


@app.get("/minute-data")
async def get_minute_data(
    symbols: str = Query(
        ...,
        description="Comma-separated list of symbols, e.g. AAPL,MSFT"
    ),
    minutes: int = Query(
        60,
        ge=1,
        le=1440,
        description="How many minutes back to fetch (1-1440)"
    ),
):
    """
    Fetch minute-by-minute data for one or multiple symbols.
    Example: /minute-data?symbols=AAPL,MSFT&minutes=120
    """

    if not FINNHUB_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="FINNHUB_API_KEY not set in Render environment variables."
        )

    now = int(time.time())
    from_ts = now - minutes * 60

    base_url = "https://finnhub.io/api/v1/stock/candle"

    symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbols_list:
        raise HTTPException(status_code=400, detail="No valid symbols provided.")

    result = {
        "from": from_ts,
        "to": now,
        "resolution": "1",
        "minutes": minutes,
        "symbols": {}
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        for sym in symbols_list:
            params = {
                "symbol": sym,
                "resolution": "1",
                "from": from_ts,
                "to": now,
                "token": FINNHUB_API_KEY
            }
            resp = await client.get(base_url, params=params)

            if resp.status_code != 200:
                result["symbols"][sym] = {
                    "status": "error",
                    "message": f"HTTP {resp.status_code} from Finnhub"
                }
                continue

            data = resp.json()

            if data.get("s") != "ok":
                result["symbols"][sym] = {
                    "status": data.get("s", "unknown"),
                    "message": f"Finnhub returned '{data.get('s')}'"
                }
                continue

            # Assemble candle data into clean format
            timestamps = data.get("t", [])
            opens = data.get("o", [])
            highs = data.get("h", [])
            lows = data.get("l", [])
            closes = data.get("c", [])
            volumes = data.get("v", [])

            candles = []
            for i, ts in enumerate(timestamps):
                candles.append({
                    "timestamp": ts,
                    "open": opens[i],
                    "high": highs[i],
                    "low": lows[i],
                    "close": closes[i],
                    "volume": volumes[i],
                })

            result["symbols"][sym] = {
                "status": "ok",
                "count": len(candles),
                "candles": candles,
            }

    return JSONResponse(result)
