"""
API routes for assets, purchases, and stock lookup.
"""
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from bson import ObjectId

from backend.database import get_database
from backend.auth import get_current_user
from backend.services.stock_service import get_stock_info, lookup_symbol

router = APIRouter()


@router.get("/hello")
async def hello():
    """Returns a hardcoded hello stranger message."""
    return {"message": "hello stranger"}


@router.get("/stock/{symbol}")
async def stock_lookup(symbol: str):
    """Fetch live stock info for a symbol."""
    info = get_stock_info(symbol)
    return info


@router.post("/assets")
async def create_asset(request: Request):
    """Add a new asset to the user's portfolio."""
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    body = await request.json()
    symbol = body.get("symbol", "").upper().strip()
    name = body.get("name", "").strip()
    exchange = body.get("exchange", "").strip()
    asset_type = body.get("asset_type", "stock").strip()

    if not symbol:
        return JSONResponse({"error": "Symbol is required"}, status_code=400)

    if not name or not exchange:
        info = lookup_symbol(symbol)
        if info:
            name = name or info["name"]
            exchange = exchange or info["exchange"]
        else:
            name = name or symbol
            exchange = exchange or "N/A"

    db = get_database()
    existing = await db.assets.find_one({"user_id": user["_id"], "symbol": symbol})
    if existing:
        return JSONResponse(
            {"error": f"Asset {symbol} already exists in your portfolio"},
            status_code=400,
        )

    doc = {
        "user_id": user["_id"],
        "symbol": symbol,
        "name": name,
        "exchange": exchange,
        "asset_type": asset_type,
        "created_at": datetime.utcnow(),
    }
    result = await db.assets.insert_one(doc)

    return {
        "success": True,
        "asset_id": str(result.inserted_id),
        "symbol": symbol,
        "name": name,
        "exchange": exchange,
    }


@router.delete("/assets/{asset_id}")
async def delete_asset(request: Request, asset_id: str):
    """Remove an asset and all its purchases."""
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    try:
        oid = ObjectId(asset_id)
    except Exception:
        return JSONResponse({"error": "Invalid asset id"}, status_code=400)

    db = get_database()
    asset = await db.assets.find_one({"_id": oid, "user_id": user["_id"]})
    if not asset:
        return JSONResponse({"error": "Asset not found"}, status_code=404)

    await db.transactions.delete_many({"asset_id": asset_id})
    await db.assets.delete_one({"_id": oid})

    return {"success": True, "message": f"Asset {asset['symbol']} deleted"}


@router.post("/assets/{asset_id}/purchases")
async def create_purchase(request: Request, asset_id: str):
    """Add a purchase to an asset."""
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    try:
        oid = ObjectId(asset_id)
    except Exception:
        return JSONResponse({"error": "Invalid asset id"}, status_code=400)

    db = get_database()
    asset = await db.assets.find_one({"_id": oid, "user_id": user["_id"]})
    if not asset:
        return JSONResponse({"error": "Asset not found"}, status_code=404)

    body = await request.json()
    price_per_unit = float(body.get("price_per_unit", 0))
    quantity = int(body.get("quantity", 0))
    purchase_date_str = body.get("purchase_date", "")
    notes = (body.get("notes") or "").strip()

    if price_per_unit <= 0 or quantity <= 0:
        return JSONResponse(
            {"error": "Price and quantity must be positive"}, status_code=400
        )

    try:
        purchase_date = datetime.strptime(purchase_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return JSONResponse(
            {"error": "Invalid purchase_date (use YYYY-MM-DD)"}, status_code=400
        )

    debit = round(price_per_unit * quantity, 2)
    doc = {
        "asset_id": asset_id,
        "transaction_type": "purchase",
        "price_per_unit": price_per_unit,
        "quantity": quantity,
        "purchase_date": purchase_date,
        "fees": 0.0,
        "debit": debit,
        "credit": 0.0,
        "notes": notes,
        "created_at": datetime.utcnow(),
    }
    result = await db.transactions.insert_one(doc)

    return {"success": True, "purchase_id": str(result.inserted_id)}


@router.delete("/assets/{asset_id}/purchases/{purchase_id}")
async def delete_purchase(request: Request, asset_id: str, purchase_id: str):
    """Remove a purchase."""
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    db = get_database()
    try:
        asset_oid = ObjectId(asset_id)
        purchase_oid = ObjectId(purchase_id)
    except Exception:
        return JSONResponse({"error": "Invalid id"}, status_code=400)

    asset = await db.assets.find_one({"_id": asset_oid, "user_id": user["_id"]})
    if not asset:
        return JSONResponse({"error": "Asset not found"}, status_code=404)

    result = await db.transactions.delete_one(
        {"_id": purchase_oid, "asset_id": asset_id}
    )
    if result.deleted_count == 0:
        return JSONResponse({"error": "Purchase not found"}, status_code=404)

    return {"success": True, "message": "Purchase deleted"}
