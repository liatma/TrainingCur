"""
Stock price service using yfinance with simple in-memory caching.
"""
import time
import yfinance as yf
from typing import Optional

# Simple in-memory cache: { symbol: { "data": {...}, "timestamp": float } }
_cache: dict = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def get_stock_info(symbol: str) -> dict:
    """
    Fetch stock information for a given symbol.
    Returns dict with current_price, previous_close, change_percent,
    change_amount, currency, name, exchange, day_high, day_low.
    Uses a simple in-memory cache to avoid repeated API calls.
    """
    symbol = symbol.upper().strip()

    # Check cache
    cached = _cache.get(symbol)
    if cached and (time.time() - cached["timestamp"]) < CACHE_TTL_SECONDS:
        return cached["data"]

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        current_price = info.get("currentPrice") or info.get(
            "regularMarketPrice", 0
        )
        previous_close = info.get("previousClose", 0) or info.get(
            "regularMarketPreviousClose", 0
        )

        if previous_close and current_price:
            change_amount = current_price - previous_close
            change_percent = (change_amount / previous_close) * 100
        else:
            change_amount = 0
            change_percent = 0

        data = {
            "symbol": symbol,
            "name": info.get("shortName") or info.get("longName", symbol),
            "exchange": info.get("exchange", "N/A"),
            "currency": info.get("currency", "USD"),
            "current_price": round(current_price, 2) if current_price else 0,
            "previous_close": round(previous_close, 2) if previous_close else 0,
            "change_amount": round(change_amount, 2),
            "change_percent": round(change_percent, 2),
            "day_high": round(info.get("dayHigh", 0) or 0, 2),
            "day_low": round(info.get("dayLow", 0) or 0, 2),
            "market_cap": info.get("marketCap", 0),
            "sector": info.get("sector", "N/A"),
            "success": True,
        }

        # Cache the result
        _cache[symbol] = {"data": data, "timestamp": time.time()}

        return data

    except Exception as e:
        return {
            "symbol": symbol,
            "name": symbol,
            "exchange": "N/A",
            "currency": "USD",
            "current_price": 0,
            "previous_close": 0,
            "change_amount": 0,
            "change_percent": 0,
            "day_high": 0,
            "day_low": 0,
            "market_cap": 0,
            "sector": "N/A",
            "success": False,
            "error": str(e),
        }


def lookup_symbol(symbol: str) -> Optional[dict]:
    """
    Quick lookup to validate a symbol and get basic info.
    Returns name and exchange if found, None otherwise.
    """
    try:
        info = get_stock_info(symbol)
        if info["success"] and info["current_price"] > 0:
            return {
                "symbol": info["symbol"],
                "name": info["name"],
                "exchange": info["exchange"],
                "current_price": info["current_price"],
                "currency": info["currency"],
            }
        return None
    except Exception:
        return None
