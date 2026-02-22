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

        # Get name and extended company info from .info
        try:
            info = ticker.info
            name = info.get("shortName") or info.get("longName", symbol)
            sector = info.get("sector", "N/A")
            # Extended company details for Company details page
            long_name = info.get("longName") or name
            industry = info.get("industry") or None
            website = info.get("website") or None
            week_52_high = info.get("fiftyTwoWeekHigh")
            week_52_low = info.get("fiftyTwoWeekLow")
            avg_volume = info.get("averageVolume")
            volume = info.get("volume") or fi.get("lastVolume")
            enterprise_value = info.get("enterpriseValue")
            trailing_pe = info.get("trailingPE")
            forward_pe = info.get("forwardPE")
            peg_ratio = info.get("pegRatio")
            price_to_book = info.get("priceToBook")
            dividend_yield = info.get("dividendYield")
            payout_ratio = info.get("payoutRatio")
            ex_dividend_date = info.get("exDividendDate")
            beta = info.get("beta")
            recommendation = info.get("recommendationKey")
            target_mean_price = info.get("targetMeanPrice")
            num_analysts = info.get("numberOfAnalystOpinions")
            description = info.get("longBusinessSummary")
            full_time_employees = info.get("fullTimeEmployees")
            address = info.get("address1")
            city = info.get("city")
            state = info.get("state")
            country = info.get("country")
        except Exception:
            name = symbol
            sector = "N/A"
            long_name = name
            industry = website = None
            week_52_high = week_52_low = avg_volume = volume = None
            enterprise_value = trailing_pe = forward_pe = peg_ratio = price_to_book = None
            dividend_yield = payout_ratio = ex_dividend_date = beta = None
            recommendation = target_mean_price = num_analysts = None
            description = full_time_employees = address = city = state = country = None

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
            # Company details page fields
            "long_name": long_name,
            "industry": industry,
            "website": website,
            "fifty_two_week_high": week_52_high,
            "fifty_two_week_low": week_52_low,
            "average_volume": avg_volume,
            "volume": volume,
            "enterprise_value": enterprise_value,
            "trailing_pe": trailing_pe,
            "forward_pe": forward_pe,
            "peg_ratio": peg_ratio,
            "price_to_book": price_to_book,
            "dividend_yield": dividend_yield,
            "payout_ratio": payout_ratio,
            "ex_dividend_date": ex_dividend_date,
            "beta": beta,
            "recommendation_key": recommendation,
            "target_mean_price": target_mean_price,
            "number_of_analyst_opinions": num_analysts,
            "description": description,
            "full_time_employees": full_time_employees,
            "address": address,
            "city": city,
            "state": state,
            "country": country,
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
            "long_name": symbol,
            "industry": None,
            "website": None,
            "fifty_two_week_high": None,
            "fifty_two_week_low": None,
            "average_volume": None,
            "volume": None,
            "enterprise_value": None,
            "trailing_pe": None,
            "forward_pe": None,
            "peg_ratio": None,
            "price_to_book": None,
            "dividend_yield": None,
            "payout_ratio": None,
            "ex_dividend_date": None,
            "beta": None,
            "recommendation_key": None,
            "target_mean_price": None,
            "number_of_analyst_opinions": None,
            "description": None,
            "full_time_employees": None,
            "address": None,
            "city": None,
            "state": None,
            "country": None,
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
