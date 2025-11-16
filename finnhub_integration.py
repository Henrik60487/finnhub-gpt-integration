from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import yfinance as yf
import pandas as pd

app = FastAPI(title="Yahoo Finance Minute Data API (Stable Version)")


@app.get("/.well-known/health")
def health():
    return {"status": "ok"}


@app.get("/minute-data")
def minute_data(
    symbols: str = Query(..., description="Symbols like AAPL,MSFT,TSLA"),
    minutes: int = Query(60, ge=1, le=4320, description="Minutes to return (1m resolution)"),
):
    """
    Fetch minute data with yfinance using 1-minute interval.
    Uses period=1d or 5d or 7d automatically to avoid 'no data returned'.
    """

    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=400, detail="No valid symbols provided.")

    # We always fetch up to 5 days of minute data (1m interval).
    # yfinance supports: 1d, 5d, 1mo, 3mo ...
    # For 1-minute data, max is ~7 days.
    if minutes <= 390:
        period = "1d"
    elif minutes <= 1950:
        period = "5d"
    else:
        period = "7d"

    interval = "1m"

    results = {
        "requested_minutes": minutes,
        "used_period": period,
        "interval": interval,
        "symbols": {}
    }

    for sym in symbol_list:
        try:
            df = yf.download(
                sym,
                interval=interval,
                period=period,
                progress=False
            )

            if df.empty:
                results["symbols"][sym] = {
                    "status": "error",
                    "message": "Yahoo returned no data (market closed, invalid symbol, or no 1m data)."
                }
                continue

            # Keep only the last N minutes requested
            df = df.tail(minutes)

            candles = []
            for idx, row in df.iterrows():
                candles.append({
                    "timestamp": int(idx.timestamp()),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                })

            results["symbols"][sym] = {
                "status": "ok",
                "count": len(candles),
                "candles": candles
            }

        except Exception as e:
            results["symbols"][sym] = {
                "status": "error",
                "message": str(e)
            }

    return JSONResponse(results)
