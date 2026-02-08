"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from bson import ObjectId


class PyObjectId(str):
    """Custom type for MongoDB ObjectId serialization."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)


def objectid_to_str(doc: dict) -> dict:
    """Convert MongoDB document ObjectId fields to strings."""
    if doc is None:
        return doc
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    if "user_id" in doc:
        doc["user_id"] = str(doc["user_id"])
    if "asset_id" in doc:
        doc["asset_id"] = str(doc["asset_id"])
    return doc


# --- Request Models ---

class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str


class UserLogin(BaseModel):
    username: str
    password: str


class AssetCreate(BaseModel):
    symbol: str
    name: str
    exchange: str
    asset_type: str = "stock"


class PurchaseCreate(BaseModel):
    price_per_unit: float
    quantity: float
    purchase_date: date
    notes: Optional[str] = ""


# --- Response Models ---

class UserResponse(BaseModel):
    id: str = Field(alias="_id")
    username: str
    display_name: str
    created_at: datetime

    class Config:
        populate_by_name = True


class AssetResponse(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    symbol: str
    name: str
    exchange: str
    asset_type: str
    created_at: datetime

    class Config:
        populate_by_name = True


class PurchaseResponse(BaseModel):
    id: str = Field(alias="_id")
    asset_id: str
    price_per_unit: float
    quantity: float
    purchase_date: date
    notes: Optional[str] = ""
    created_at: datetime

    class Config:
        populate_by_name = True
