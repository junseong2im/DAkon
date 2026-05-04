from fastapi import APIRouter, HTTPException
import yfinance as yf

router = APIRouter()

@router.get("/market/ohlcv")
def get_ohlcv(symbol: str):
    try:
        data = yf.download(symbol.upper(), period="3mo", auto_adjust=False, progress=False)

        if data.empty:
            raise HTTPException(status_code=404, detail="No data found")

        candles = []

        for idx, row in data.iterrows():
            candles.append({
                "time": str(idx.date()),
                "open": float(row["Open"].iloc[0] if hasattr(row["Open"], "iloc") else row["Open"]),
                "high": float(row["High"].iloc[0] if hasattr(row["High"], "iloc") else row["High"]),
                "low": float(row["Low"].iloc[0] if hasattr(row["Low"], "iloc") else row["Low"]),
                "close": float(row["Close"].iloc[0] if hasattr(row["Close"], "iloc") else row["Close"]),
                "volume": int(row["Volume"].iloc[0] if hasattr(row["Volume"], "iloc") else row["Volume"])
            })

        return {
            "status": "success",
            "data": {
                "symbol": symbol.upper(),
                "candles": candles
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        