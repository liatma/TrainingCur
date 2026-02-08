"""
MongoDB database connection using PyMongo Async API (AsyncMongoClient).
"""
from pymongo import AsyncMongoClient
from typing import Optional

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "portfolio_db"

client: Optional[AsyncMongoClient] = None


async def connect_to_mongo():
    """Create MongoDB async client and initialize indexes."""
    global client
    client = await AsyncMongoClient(MONGO_URL).aconnect()

    db = client[DB_NAME]

    # Create indexes
    await db.users.create_index("username", unique=True)
    await db.assets.create_index("user_id")
    await db.purchases.create_index("asset_id")


async def close_mongo_connection():
    """Close MongoDB client connection."""
    global client
    if client:
        await client.close()


def get_database():
    """Get the portfolio database instance."""
    return client[DB_NAME]
