"""
MongoDB database connection using PyMongo Async API (AsyncMongoClient).
Collections: users, assets, transactions (purchases live in transactions with transaction_type="purchase").
"""
from pymongo import AsyncMongoClient
from typing import Optional

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "portfolio_db"

client: Optional[AsyncMongoClient] = None


async def connect_to_mongo():
    """Create MongoDB async client and initialize indexes."""
    global client
    client = AsyncMongoClient(MONGO_URL)
    db = client[DB_NAME]
    await db.users.create_index("username", unique=True)
    await db.assets.create_index("user_id")
    await db.assets.create_index([("user_id", 1), ("symbol", 1)])
    await db.transactions.create_index("asset_id")


async def close_mongo_connection():
    """Close MongoDB client connection."""
    global client
    if client:
        await client.close()
        client = None


def get_database():
    """Get the portfolio database instance."""
    return client[DB_NAME]
