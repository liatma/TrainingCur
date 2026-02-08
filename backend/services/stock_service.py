"""
Stock price service using yfinance with simple in-memory caching.
"""
import time
import yfinance as yf
from typing import Optional

# Simple in-memory cache: { symbol: { "data": {...}, "timestamp": float } }
_cache: dict = {}
CACHE_TTL_SECONDS = 300  # 5 minutes

# Map of exchange codes to friendly names
EXCHANGE_MAP = {
    "NMS": "NASDAQ",
    "NGM": "NASDAQ",
    "NCM": "NASDAQ",
    "NYQ": "NYSE",
    "NYS": "NYSE",
    "PCX": "NYSE ARCA",
    "BTS": "BATS",
    "ASE": "NYSE American",
    "LSE": "London",
    "TYO": "Tokyo",
}


def _friendly_exchange(code: str) -> str:
    """Convert exchange code to a human-friendly name."""
    return EXCHANGE_MAP.get(code, code)


def get_stock_info(symbol: str) -> dict:
    """
    Fetch stock information for a given symbol.
    Uses fast_info for price data (faster, more reliable) and
    .info for name/sector metadata.
    """
    symbol = symbol.upper().strip()

    # Check cache
    cached = _cache.get(symbol)
    if cached and (time.time() - cached["timestamp"]) < CACHE_TTL_SECONDS:
        return cached["data"]

    try:
        ticker = yf.Ticker(symbol)

        # fast_info is lightweight and reliable for price data
        fi = ticker.fast_info

        current_price = fi.get("lastPrice", 0) or 0
        previous_close = (
            fi.get("previousClose", 0)
            or fi.get("regularMarketPreviousClose", 0)
            or 0
        )
        exchange_raw = fi.get("exchange", "N/A") or "N/A"
        currency = fi.get("currency", "USD") or "USD"
        day_high = fi.get("dayHigh", 0) or 0
        day_low = fi.get("dayLow", 0) or 0
        market_cap = fi.get("marketCap", 0) or 0

        if previous_close and current_price:
            change_amount = current_price - previous_close
            change_percent = (change_amount / previous_close) * 100
        else:
            change_amount = 0
            change_percent = 0

        # Get name from .info (has more metadata)
        try:
            info = ticker.info
            name = info.get("shortName") or info.get("longName", symbol)
            sector = info.get("sector", "N/A")
        except Exception:
            name = symbol
            sector = "N/A"

        data = {
            "symbol": symbol,
            "name": name,
            "exchange": _friendly_exchange(exchange_raw),
            "currency": currency,
            "current_price": round(current_price, 2),
            "previous_close": round(previous_close, 2),
            "change_amount": round(change_amount, 2),
            "change_percent": round(change_percent, 2),
            "day_high": round(day_high, 2),
            "day_low": round(day_low, 2),
            "market_cap": market_cap,
            "sector": sector,
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
