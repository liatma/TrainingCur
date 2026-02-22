"""
Page routes for server-side rendered HTML pages.
"""
import datetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from starlette.status import HTTP_303_SEE_OTHER

from backend.database import get_database
from backend.auth import get_current_user, require_login
from backend.services.stock_service import get_stock_info

_ANALYST_SCORE_MAP = {
    "strong_buy": 1,
    "buy": 2,
    "hold": 3,
    "underperform": 4,
    "sell": 5,
}


def _compute_profit_periods(purchases: list, total_profit: float) -> tuple[float | None, float | None]:
    """Return (profit_per_month, profit_per_year) based on holding duration.

    Uses earliest purchase date across all purchases. Both values are annualised
    simple returns: profit_per_year = profit_per_month * 12. Returns (None, None)
    when there are no purchases or holding duration is less than one day.
    """
    dates = []
    for p in purchases:
        pd = p.get("purchase_date")
        if pd is None:
            continue
        if isinstance(pd, datetime.datetime):
            dates.append(pd.date())
        elif isinstance(pd, datetime.date):
            dates.append(pd)
        elif isinstance(pd, str):
            try:
                dates.append(datetime.datetime.strptime(pd, "%Y-%m-%d").date())
            except ValueError:
                continue
    if not dates:
        return None, None
    first_date = min(dates)
    today = datetime.date.today()
    holding_days = (today - first_date).days
    if holding_days < 1:
        return None, None
    profit_per_month = round(total_profit / (holding_days / 30.44), 2)
    profit_per_year = round(profit_per_month * 12, 2)
    return profit_per_month, profit_per_year

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
        "login.html", {"request": request, "flash": flash, "user": None}
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration form page."""
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)
    flash = request.session.pop("flash", None)
    return templates.TemplateResponse(
        "register.html", {"request": request, "flash": flash, "user": None}
    )


def _purchase_total_cost(p: dict) -> float:
    """Total cost for a purchase/transaction: debit if set, else price * quantity."""
    debit = p.get("debit")
    if debit is not None and debit > 0:
        return float(debit)
    return float(p.get("price_per_unit", 0)) * float(p.get("quantity", 0))


async def _asset_dict_for_dashboard2(asset_doc: dict, stock_info: dict) -> dict:
    """Extended asset dict for dashboard2 table view — adds profit periods and analyst data."""
    db = get_database()
    asset_id_str = str(asset_doc["_id"])
    oid = asset_doc["_id"]
    purchases = await db.transactions.find(
        {
            "transaction_type": "purchase",
            "$or": [{"asset_id": asset_id_str}, {"asset_id": oid}],
        }
    ).to_list(length=None)
    total_units = sum(float(p.get("quantity", 0)) for p in purchases)
    total_paid = sum(_purchase_total_cost(p) for p in purchases)
    current_price = stock_info.get("current_price", 0)
    total_value = current_price * total_units
    total_profit = total_value - total_paid
    is_gain = total_profit >= 0

    profit_per_month, profit_per_year = _compute_profit_periods(purchases, total_profit)

    recommendation_key = stock_info.get("recommendation_key") or None
    analyst_score = _ANALYST_SCORE_MAP.get(recommendation_key, 99) if recommendation_key else 99

    return {
        "id": asset_id_str,
        "symbol": asset_doc["symbol"],
        "name": asset_doc["name"],
        "exchange": asset_doc["exchange"],
        "asset_type": asset_doc.get("asset_type", "stock"),
        "total_units": total_units,
        "total_paid": round(total_paid, 2),
        "current_price": current_price,
        "total_value": round(total_value, 2),
        "total_profit": round(total_profit, 2),
        "is_gain": is_gain,
        "change_percent": stock_info.get("change_percent", 0),
        "currency": stock_info.get("currency", "USD"),
        "profit_per_month": profit_per_month,
        "profit_per_year": profit_per_year,
        "recommendation_key": recommendation_key,
        "target_mean_price": stock_info.get("target_mean_price"),
        "analyst_score": analyst_score,
    }


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, user: dict = Depends(require_login)):
    """Portfolio dashboard — sortable table view with profit metrics and analyst data."""
    db = get_database()
    assets_docs = await db.assets.find({"user_id": user["_id"]}).to_list(length=None)
    assets = []
    for asset_doc in assets_docs:
        stock_info = get_stock_info(asset_doc["symbol"])
        assets.append(await _asset_dict_for_dashboard2(asset_doc, stock_info))

    portfolio_invested = sum(a["total_paid"] for a in assets)
    portfolio_value = sum(a["total_value"] for a in assets)
    portfolio_profit = portfolio_value - portfolio_invested
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
            "portfolio_profit": round(portfolio_profit, 2),
            "portfolio_is_gain": portfolio_is_gain,
            "flash": flash,
        },
    )


async def _load_asset_context(asset_id: str, user: dict) -> dict | None:
    """Load asset, purchases, stock_info, and computed totals. Returns context dict or None."""
    asset_id = (asset_id or "").strip()
    if not asset_id:
        return None
    try:
        oid = ObjectId(asset_id)
    except Exception:
        return None

    db = get_database()
    asset_doc = await db.assets.find_one({"_id": oid, "user_id": user["_id"]})
    if not asset_doc:
        return None

    asset_id_str = str(asset_doc["_id"])
    # Transactions collection: transaction_type "purchase", asset_id string or ObjectId
    purchases_cursor = db.transactions.find(
        {
            "transaction_type": "purchase",
            "$or": [{"asset_id": asset_id_str}, {"asset_id": oid}],
        }
    ).sort("purchase_date", -1)
    purchases_docs = await purchases_cursor.to_list(length=None)

    stock_info = get_stock_info(asset_doc["symbol"])
    current_price = stock_info.get("current_price", 0)

    total_units = sum(float(p.get("quantity", 0)) for p in purchases_docs)
    total_paid = sum(_purchase_total_cost(p) for p in purchases_docs)
    total_value = current_price * total_units
    total_profit = total_value - total_paid
    is_gain = total_profit >= 0

    purchases_data = []
    for p in purchases_docs:
        total_cost = _purchase_total_cost(p)
        qty = float(p.get("quantity", 0))
        current_value = current_price * qty
        profit = current_value - total_cost
        purchases_data.append({
            "id": str(p["_id"]),
            "purchase_date": p.get("purchase_date"),
            "price_per_unit": float(p.get("price_per_unit", 0)),
            "quantity": int(qty) if qty == int(qty) else qty,
            "total_cost": round(total_cost, 2),
            "current_value": round(current_value, 2),
            "profit": round(profit, 2),
            "is_gain": profit >= 0,
            "notes": p.get("notes") or "",
        })

    # Asset dict for template (id, symbol, name, exchange, asset_type)
    asset = {
        "id": asset_id_str,
        "symbol": asset_doc["symbol"],
        "name": asset_doc["name"],
        "exchange": asset_doc["exchange"],
        "asset_type": asset_doc.get("asset_type", "stock"),
    }

    # TradingView symbol: exchange:SYMBOL (e.g. NASDAQ:AAPL) or bare symbol
    exchange = (asset_doc.get("exchange") or "").strip().upper()
    symbol = (asset_doc.get("symbol") or "").strip()
    tv_symbol = f"{exchange}:{symbol}" if exchange and symbol else symbol or "NASDAQ:AAPL"

    profit_per_month, profit_per_year = _compute_profit_periods(purchases_docs, total_profit)

    recommendation_key = stock_info.get("recommendation_key") or None
    analyst_score = _ANALYST_SCORE_MAP.get(recommendation_key, 99) if recommendation_key else 99

    return {
        "asset": asset,
        "purchases": purchases_data,
        "stock_info": stock_info,
        "current_price": current_price,
        "total_units": total_units,
        "total_paid": round(total_paid, 2),
        "total_value": round(total_value, 2),
        "total_profit": round(total_profit, 2),
        "is_gain": is_gain,
        "tv_symbol": tv_symbol,
        "profit_per_month": profit_per_month,
        "profit_per_year": profit_per_year,
        "recommendation_key": recommendation_key,
        "target_mean_price": stock_info.get("target_mean_price"),
        "number_of_analyst_opinions": stock_info.get("number_of_analyst_opinions"),
        "analyst_score": analyst_score,
    }


@router.get("/dashboard/asset/{asset_id}", response_class=HTMLResponse)
async def asset_detail_page(
    request: Request,
    asset_id: str,
    user: dict = Depends(require_login),
):
    """Asset detail: purchase history and add purchase form."""
    ctx = await _load_asset_context(asset_id, user)
    if not ctx:
        return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)

    flash = request.session.pop("flash", None)

    return templates.TemplateResponse(
        "asset_detail.html",
        {
            "request": request,
            "user": user,
            "asset": ctx["asset"],
            "purchases": ctx["purchases"],
            "stock_info": ctx["stock_info"],
            "current_price": ctx["current_price"],
            "total_units": ctx["total_units"],
            "total_paid": ctx["total_paid"],
            "total_value": ctx["total_value"],
            "total_profit": ctx["total_profit"],
            "is_gain": ctx["is_gain"],
            "tv_symbol": ctx["tv_symbol"],
            "profit_per_month": ctx["profit_per_month"],
            "profit_per_year": ctx["profit_per_year"],
            "recommendation_key": ctx["recommendation_key"],
            "target_mean_price": ctx["target_mean_price"],
            "number_of_analyst_opinions": ctx["number_of_analyst_opinions"],
            "analyst_score": ctx["analyst_score"],
            "flash": flash,
        },
    )
