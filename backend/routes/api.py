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


# --- Hello (keep original endpoint) ---

@router.get("/hello")
async def hello():
    """Returns a hardcoded hello stranger message."""
    return {"message": "hello stranger"}


# --- Stock Lookup ---

@router.get("/stock/{symbol}")
async def stock_lookup(symbol: str):
    """Fetch live stock info for a symbol."""
    info = get_stock_info(symbol)
    return info


# --- Assets CRUD ---

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

    # If name/exchange not provided, try to look them up
    if not name or not exchange:
        info = lookup_symbol(symbol)
        if info:
            name = name or info["name"]
            exchange = exchange or info["exchange"]
        else:
            name = name or symbol
            exchange = exchange or "N/A"

    db = get_database()

    # Check for duplicate asset for this user
    existing = await db.assets.find_one(
        {"user_id": user["_id"], "symbol": symbol}
    )
    if existing:
        return JSONResponse(
            {"error": f"Asset {symbol} already exists in your portfolio"},
            status_code=400,
        )

    asset_doc = {
        "user_id": user["_id"],
        "symbol": symbol,
        "name": name,
        "exchange": exchange,
        "asset_type": asset_type,
        "created_at": datetime.utcnow(),
    }
    result = await db.assets.insert_one(asset_doc)

    return {
        "success": True,
        "asset_id": str(result.inserted_id),
        "symbol": symbol,
        "name": name,
        "exchange": exchange,
    }


@router.delete("/assets/{asset_id}")
async def delete_asset(request: Request, asset_id: str):
    """Remove an asset and all its transactions."""
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    db = get_database()

    # Verify ownership
    asset = await db.assets.find_one(
        {"_id": ObjectId(asset_id), "user_id": user["_id"]}
    )
    if not asset:
        return JSONResponse({"error": "Asset not found"}, status_code=404)

    # Delete all transactions for this asset
    await db.transactions.delete_many({"asset_id": asset_id})

    # Delete the asset
    await db.assets.delete_one({"_id": ObjectId(asset_id)})

    return {"success": True, "message": f"Asset {asset['symbol']} deleted"}


# --- Transactions CRUD ---

@router.post("/assets/{asset_id}/transactions")
async def create_transaction(request: Request, asset_id: str):
    """Add a transaction (purchase or dividend) to an asset."""
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    db = get_database()

    # Verify asset ownership
    asset = await db.assets.find_one(
        {"_id": ObjectId(asset_id), "user_id": user["_id"]}
    )
    if not asset:
        return JSONResponse({"error": "Asset not found"}, status_code=404)

    body = await request.json()
    transaction_type = body.get("transaction_type", "purchase").strip().lower()
    purchase_date = body.get("purchase_date", "")
    notes = body.get("notes", "")

    if transaction_type not in ("purchase", "dividend"):
        return JSONResponse(
            {"error": "Transaction type must be 'purchase' or 'dividend'"},
            status_code=400,
        )

    if transaction_type == "purchase":
        price_per_unit = float(body.get("price_per_unit", 0))
        quantity = float(body.get("quantity", 0))
        fees = float(body.get("fees", 0))

        if price_per_unit <= 0 or quantity <= 0:
            return JSONResponse(
                {"error": "Price and quantity must be positive"}, status_code=400
            )

        debit = round(price_per_unit * quantity + fees, 2)
        credit = 0.0
    else:
        # Dividend
        credit = float(body.get("credit", 0))
        if credit <= 0:
            return JSONResponse(
                {"error": "Dividend amount must be positive"}, status_code=400
            )
        price_per_unit = 0.0
        quantity = 0.0
        fees = 0.0
        debit = 0.0

    transaction_doc = {
        "asset_id": asset_id,
        "transaction_type": transaction_type,
        "price_per_unit": price_per_unit,
        "quantity": quantity,
        "purchase_date": purchase_date,
        "fees": fees,
        "debit": debit,
        "credit": credit,
        "notes": notes,
        "created_at": datetime.utcnow(),
    }
    result = await db.transactions.insert_one(transaction_doc)

    return {
        "success": True,
        "transaction_id": str(result.inserted_id),
    }


@router.delete("/assets/{asset_id}/transactions/{transaction_id}")
async def delete_transaction(request: Request, asset_id: str, transaction_id: str):
    """Remove a transaction."""
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    db = get_database()

    # Verify asset ownership
    asset = await db.assets.find_one(
        {"_id": ObjectId(asset_id), "user_id": user["_id"]}
    )
    if not asset:
        return JSONResponse({"error": "Asset not found"}, status_code=404)

    # Delete the transaction
    result = await db.transactions.delete_one(
        {"_id": ObjectId(transaction_id), "asset_id": asset_id}
    )
    if result.deleted_count == 0:
        return JSONResponse({"error": "Transaction not found"}, status_code=404)

    return {"success": True, "message": "Transaction deleted"}
