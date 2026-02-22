"""
Page routes for server-side rendered HTML pages.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_303_SEE_OTHER
from bson import ObjectId
from backend.database import get_database
from backend.auth import get_current_user, require_login
from backend.services.stock_service import get_stock_info

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page with description and login CTA."""
    user = await get_current_user(request)
    return templates.TemplateResponse(
        "landing.html", {"request": request, "user": user}
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login form page."""
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)
    flash = request.session.pop("flash", None)
    return templates.TemplateResponse(
        "login.html", {"request": request, "flash": flash}
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration form page."""
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)
    flash = request.session.pop("flash", None)
    return templates.TemplateResponse(
        "register.html", {"request": request, "flash": flash}
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Portfolio dashboard showing all user assets."""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    db = get_database()

    # Fetch all assets for this user
    assets = []
    cursor = db.assets.find({"user_id": user["_id"]})
    async for asset in cursor:
        asset["_id"] = str(asset["_id"])
        asset["user_id"] = str(asset["user_id"])

        # Get transactions for this asset
        txns = []
        txn_cursor = db.transactions.find({"asset_id": asset["_id"]})
        async for t in txn_cursor:
            t["_id"] = str(t["_id"])
            t["asset_id"] = str(t["asset_id"])
            txns.append(t)

        # Compute totals from transactions
        purchase_txns = [t for t in txns if t.get("transaction_type", "purchase") == "purchase"]
        dividend_txns = [t for t in txns if t.get("transaction_type") == "dividend"]

        total_units = sum(t.get("quantity", 0) for t in purchase_txns)
        total_paid = sum(t.get("debit", t.get("price_per_unit", 0) * t.get("quantity", 0)) for t in purchase_txns)
        total_fees = sum(t.get("fees", 0) for t in txns)
        total_dividends = sum(t.get("credit", 0) for t in dividend_txns)

        # Fetch live stock data
        stock_info = get_stock_info(asset["symbol"])
        current_price = stock_info.get("current_price", 0)
        total_value = current_price * total_units
        total_profit = total_value - total_paid + total_dividends
        is_gain = total_profit >= 0

        asset["total_units"] = total_units
        asset["total_paid"] = round(total_paid, 2)
        asset["total_fees"] = round(total_fees, 2)
        asset["total_dividends"] = round(total_dividends, 2)
        asset["current_price"] = current_price
        asset["total_value"] = round(total_value, 2)
        asset["total_profit"] = round(total_profit, 2)
        asset["is_gain"] = is_gain
        asset["change_percent"] = stock_info.get("change_percent", 0)
        asset["currency"] = stock_info.get("currency", "USD")

        assets.append(asset)

    # Portfolio totals
    portfolio_invested = sum(a["total_paid"] for a in assets)
    portfolio_value = sum(a["total_value"] for a in assets)
    portfolio_fees = sum(a["total_fees"] for a in assets)
    portfolio_dividends = sum(a["total_dividends"] for a in assets)
    portfolio_profit = portfolio_value - portfolio_invested + portfolio_dividends
    portfolio_is_gain = portfolio_profit >= 0

    flash = request.session.pop("flash", None)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "assets": assets,
            "portfolio_invested": round(portfolio_invested, 2),
            "portfolio_value": round(portfolio_value, 2),
            "portfolio_fees": round(portfolio_fees, 2),
            "portfolio_dividends": round(portfolio_dividends, 2),
            "portfolio_profit": round(portfolio_profit, 2),
            "portfolio_is_gain": portfolio_is_gain,
            "flash": flash,
        },
    )


def _tv_symbol_for_asset(asset: dict) -> str:
    """Build TradingView symbol from asset exchange and symbol."""
    exchange = (asset.get("exchange") or "N/A").upper()
    if exchange in ("N/A", ""):
        tv_exchange = "NASDAQ"
    elif exchange in ("NMS", "NGM", "NCM"):
        tv_exchange = "NASDAQ"
    elif exchange in ("NYQ", "NYS"):
        tv_exchange = "NYSE"
    else:
        tv_exchange = exchange
    return f"{tv_exchange}:{asset['symbol']}"


async def _load_asset_context(asset_id: str, user: dict):
    """
    Load asset, transactions, stock_info, and computed totals.
    Returns (asset, transactions, stock_info, context_dict) or (None, None, None, None) if not found.
    """
    db = get_database()
    asset = await db.assets.find_one(
        {"_id": ObjectId(asset_id), "user_id": user["_id"]}
    )
    if not asset:
        return None, None, None, None

    asset["_id"] = str(asset["_id"])
    asset["user_id"] = str(asset["user_id"])

    transactions = []
    txn_cursor = db.transactions.find(
        {"asset_id": asset["_id"]}
    ).sort("purchase_date", -1)
    async for t in txn_cursor:
        t["_id"] = str(t["_id"])
        t["asset_id"] = str(t["asset_id"])
        transactions.append(t)

    stock_info = get_stock_info(asset["symbol"])
    current_price = stock_info.get("current_price", 0)

    purchase_txns = [t for t in transactions if t.get("transaction_type", "purchase") == "purchase"]
    dividend_txns = [t for t in transactions if t.get("transaction_type") == "dividend"]

    total_units = sum(t.get("quantity", 0) for t in purchase_txns)
    total_paid = sum(t.get("debit", t.get("price_per_unit", 0) * t.get("quantity", 0)) for t in purchase_txns)
    total_fees = sum(t.get("fees", 0) for t in transactions)
    total_dividends = sum(t.get("credit", 0) for t in dividend_txns)
    total_value = current_price * total_units
    total_profit = total_value - total_paid + total_dividends
    is_gain = total_profit >= 0

    for t in transactions:
        tx_type = t.get("transaction_type", "purchase")
        if tx_type == "purchase":
            t["total_cost"] = round(t.get("price_per_unit", 0) * t.get("quantity", 0), 2)
            t["current_value"] = round(current_price * t.get("quantity", 0), 2)
            t["profit"] = round(t["current_value"] - t["total_cost"], 2)
            t["is_gain"] = t["profit"] >= 0
        else:
            t["total_cost"] = 0.0
            t["current_value"] = 0.0
            t["profit"] = t.get("credit", 0)
            t["is_gain"] = True

    tv_symbol = _tv_symbol_for_asset(asset)
    context = {
        "asset": asset,
        "transactions": transactions,
        "stock_info": stock_info,
        "current_price": current_price,
        "total_units": total_units,
        "total_paid": round(total_paid, 2),
        "total_fees": round(total_fees, 2),
        "total_dividends": round(total_dividends, 2),
        "total_value": round(total_value, 2),
        "total_profit": round(total_profit, 2),
        "is_gain": is_gain,
        "tv_symbol": tv_symbol,
    }
    return asset, transactions, stock_info, context


@router.get("/dashboard/asset/{asset_id}", response_class=HTMLResponse)
async def asset_gateway_page(request: Request, asset_id: str):
    """Asset gateway: summary, last 3 transactions, TradingView."""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    asset, transactions, stock_info, ctx = await _load_asset_context(asset_id, user)
    if not ctx:
        return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)

    transactions_last3 = ctx["transactions"][:3]
    has_more_transactions = len(ctx["transactions"]) > 3
    flash = request.session.pop("flash", None)

    return templates.TemplateResponse(
        "asset_gateway.html",
        {
            "request": request,
            "user": user,
            "asset": ctx["asset"],
            "transactions_last3": transactions_last3,
            "has_more_transactions": has_more_transactions,
            "stock_info": ctx["stock_info"],
            "current_price": ctx["current_price"],
            "total_units": ctx["total_units"],
            "total_paid": ctx["total_paid"],
            "total_fees": ctx["total_fees"],
            "total_dividends": ctx["total_dividends"],
            "total_value": ctx["total_value"],
            "total_profit": ctx["total_profit"],
            "is_gain": ctx["is_gain"],
            "tv_symbol": ctx["tv_symbol"],
            "flash": flash,
            "asset_view": "overview",
        },
    )


@router.get("/dashboard/asset/{asset_id}/company", response_class=HTMLResponse)
async def asset_company_page(request: Request, asset_id: str):
    """Company details: all yfinance-derived info grouped."""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    asset, _, stock_info, ctx = await _load_asset_context(asset_id, user)
    if not ctx:
        return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)

    flash = request.session.pop("flash", None)

    return templates.TemplateResponse(
        "asset_company.html",
        {
            "request": request,
            "user": user,
            "asset": ctx["asset"],
            "stock_info": ctx["stock_info"],
            "current_price": ctx["current_price"],
            "flash": flash,
            "asset_view": "company",
        },
    )


@router.get("/dashboard/asset/{asset_id}/purchases", response_class=HTMLResponse)
async def asset_purchases_page(request: Request, asset_id: str):
    """Purchase details: full transaction history and Add Transaction form."""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    asset, transactions, stock_info, ctx = await _load_asset_context(asset_id, user)
    if not ctx:
        return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)

    flash = request.session.pop("flash", None)

    return templates.TemplateResponse(
        "asset_purchases.html",
        {
            "request": request,
            "user": user,
            "asset": ctx["asset"],
            "transactions": ctx["transactions"],
            "stock_info": ctx["stock_info"],
            "current_price": ctx["current_price"],
            "flash": flash,
            "asset_view": "purchases",
        },
    )
