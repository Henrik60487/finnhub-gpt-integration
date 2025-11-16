from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import yfinance as yf
import time
import pandas as pd

app = FastAPI(title="Yahoo Finance Minute Data API (yfinance)")

@app.get("/.well-known/health")
def health():
    return {"status": "ok"}


@app.get("/minute-data")
def minute_data(
    symbols: str = Query(..., description="Symbols like AAPL,MSFT,TSLA"),
    minutes: int = Query(60, ge=1, le=4320, description="How many minutes to load")
):
    """
    Fetch 1-minute data using yfinance, which avoids Yahoo's raw API rate limits.
    """

    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=400, detail="No valid symbols provided.")

    results = {
        "requested_minutes": minutes,
        "resolution": "1m",
        "symbols": {}
    }

    # yfinance interval format
    interval = "1m"

    # yfinance only returns up to ~7 days of 1-minute data
    period = f"{minutes}m" if minutes <= 390 else "7d"

    for sym in symbol_list:
        try:
            df = yf.download(
                tickers=sym,
                interval=interval,
                period=period,
                progress=False
            )

            if df.empty:
                results["symbols"][sym] = {
                    "status": "error",
                    "message": "No data returned"
                }
                continue

            # Convert dataframe to candles
            df = df.tail(minutes)   # limit to requested minutes

            candles = []
            for ts, row in df.iterrows():
                candles.append({
                    "timestamp": int(ts.timestamp()),
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
