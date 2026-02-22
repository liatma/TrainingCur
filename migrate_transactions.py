"""
Migration script: Import transactions from a MongoDB BSON dump into StockFolio.

Usage:
    python migrate_transactions.py <username> [path_to_bson]

Arguments:
    username       - An existing StockFolio user to assign the transactions to.
    path_to_bson   - Path to the Transactions.bson file (optional, defaults to
                     the known dump location).

Steps:
    1. Connects to MongoDB (portfolio_db)
    2. Looks up the target user by username
    3. Deletes all existing transactions from the DB
    4. Reads & parses the BSON dump
    5. Creates missing assets (uses yfinance for name/exchange)
    6. Maps each source document to the app's transaction schema
    7. Bulk-inserts all transactions
"""

import sys
import asyncio
from datetime import datetime
from pathlib import Path

import bson
from pymongo import AsyncMongoClient

# ---------------------------------------------------------------------------
# Attempt to import the stock service for yfinance lookups (optional)
# ---------------------------------------------------------------------------
try:
    from backend.services.stock_service import lookup_symbol
except ImportError:
    lookup_symbol = None

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "portfolio_db"

DEFAULT_BSON_PATH = (
    r"c:\Users\User\Downloads\mongodb dump 260825"
    r"\mongodb dump 260825\StockGardner\Transactions.bson"
)

# Source AssetType -> app asset_type
ASSET_TYPE_MAP = {"S": "stock", "E": "etf"}

# Source TransactionType -> app transaction_type
TXN_TYPE_MAP = {"P": "purchase", "D": "dividend"}


def normalize_date(raw: str) -> str:
    """Convert '2023-7-3' -> '2023-07-03'."""
    parts = raw.split("-")
    if len(parts) == 3:
        return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    return raw


def lookup_asset_info(symbol: str) -> dict:
    """Try to get name/exchange from yfinance. Returns dict with keys name, exchange."""
    if lookup_symbol is not None:
        try:
            info = lookup_symbol(symbol)
            if info:
                return {"name": info["name"], "exchange": info["exchange"]}
        except Exception as e:
            print(f"  [warn] yfinance lookup failed for {symbol}: {e}")
    return {"name": symbol, "exchange": "N/A"}


async def main():
    # --- Parse arguments ------------------------------------------------
    if len(sys.argv) < 2:
        print("Usage: python migrate_transactions.py <username> [path_to_bson]")
        sys.exit(1)

    target_username = sys.argv[1]
    bson_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_BSON_PATH

    if not Path(bson_path).exists():
        print(f"Error: BSON file not found at {bson_path}")
        sys.exit(1)

    # --- Connect to MongoDB ---------------------------------------------
    client = AsyncMongoClient(MONGO_URL)
    db = client[DB_NAME]

    # --- Verify user exists ---------------------------------------------
    user = await db.users.find_one({"username": target_username})
    if not user:
        print(f"Error: User '{target_username}' not found in the database.")
        print("Please register the user in the app first, then re-run this script.")
        await client.close()
        sys.exit(1)

    user_id = str(user["_id"])  # Store as string, matching the app convention
    print(f"Target user: {user['display_name']} (id: {user_id})")

    # --- Read BSON file --------------------------------------------------
    print(f"\nReading BSON from: {bson_path}")
    with open(bson_path, "rb") as f:
        raw_docs = bson.decode_all(f.read())
    print(f"  Found {len(raw_docs)} documents in the dump.")

    # --- Delete existing transactions ------------------------------------
    del_result = await db.transactions.delete_many({})
    print(f"\nCleared existing transactions: {del_result.deleted_count} removed.")

    # --- Build a set of unique symbols and their asset types -------------
    symbol_info: dict[str, str] = {}  # symbol -> source AssetType ('S' or 'E')
    for doc in raw_docs:
        sym = doc.get("Symbol", "").upper().strip()
        if sym and sym not in symbol_info:
            symbol_info[sym] = doc.get("AssetType", "S")

    print(f"\nUnique symbols to ensure: {sorted(symbol_info.keys())}")

    # --- Create missing assets -------------------------------------------
    symbol_to_asset_id: dict[str, str] = {}
    for sym, src_type in sorted(symbol_info.items()):
        existing = await db.assets.find_one({"user_id": user_id, "symbol": sym})
        if existing:
            symbol_to_asset_id[sym] = str(existing["_id"])
            print(f"  [exists] {sym} -> {symbol_to_asset_id[sym]}")
        else:
            # Look up name/exchange from yfinance
            info = lookup_asset_info(sym)
            asset_type = ASSET_TYPE_MAP.get(src_type, "stock")
            asset_doc = {
                "user_id": user_id,
                "symbol": sym,
                "name": info["name"],
                "exchange": info["exchange"],
                "asset_type": asset_type,
                "created_at": datetime.utcnow(),
            }
            result = await db.assets.insert_one(asset_doc)
            symbol_to_asset_id[sym] = str(result.inserted_id)
            print(f"  [created] {sym} ({info['name']}, {info['exchange']}, {asset_type}) -> {symbol_to_asset_id[sym]}")

    # --- Map and insert transactions -------------------------------------
    print(f"\nMapping {len(raw_docs)} transactions...")
    transactions_to_insert = []

    for doc in raw_docs:
        sym = doc.get("Symbol", "").upper().strip()
        asset_id = symbol_to_asset_id.get(sym)
        if not asset_id:
            print(f"  [skip] No asset for symbol '{sym}'")
            continue

        src_type = doc.get("TransactionType", "P")
        txn_type = TXN_TYPE_MAP.get(src_type, "purchase")

        raw_date = doc.get("Date", "")
        normalized_date = normalize_date(raw_date)

        fees = float(doc.get("Fees", 0) or 0)
        debit = float(doc.get("Debit", 0) or 0)
        credit = float(doc.get("Credit", 0) or 0)
        price_per_unit = float(doc.get("AssetPriceOnAction", 0) or 0)
        quantity = float(doc.get("StockCount", 0) or 0)

        if txn_type == "dividend":
            # For dividends: price, quantity, debit are irrelevant
            price_per_unit = 0.0
            quantity = 0.0
            debit = 0.0

        txn_doc = {
            "asset_id": asset_id,
            "transaction_type": txn_type,
            "price_per_unit": round(price_per_unit, 4),
            "quantity": round(quantity, 4),
            "purchase_date": normalized_date,
            "fees": round(fees, 2),
            "debit": round(debit, 2),
            "credit": round(credit, 2),
            "notes": "",
            "created_at": datetime.utcnow(),
        }
        transactions_to_insert.append(txn_doc)

    if transactions_to_insert:
        result = await db.transactions.insert_many(transactions_to_insert)
        print(f"\n  Inserted {len(result.inserted_ids)} transactions.")
    else:
        print("\n  No transactions to insert.")

    # --- Summary ---------------------------------------------------------
    purchases = [t for t in transactions_to_insert if t["transaction_type"] == "purchase"]
    dividends = [t for t in transactions_to_insert if t["transaction_type"] == "dividend"]
    total_debit = sum(t["debit"] for t in purchases)
    total_credit = sum(t["credit"] for t in dividends)
    total_fees = sum(t["fees"] for t in transactions_to_insert)

    print(f"\n--- Migration Summary ---")
    print(f"  Purchases : {len(purchases)}")
    print(f"  Dividends : {len(dividends)}")
    print(f"  Total Debit  : ${total_debit:,.2f}")
    print(f"  Total Credit : ${total_credit:,.2f}")
    print(f"  Total Fees   : ${total_fees:,.2f}")
    print(f"  Assets       : {len(symbol_to_asset_id)}")
    print(f"\nDone!")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
