"""
Authentication helpers: password hashing and session management.
"""
import bcrypt
from fastapi import Request, HTTPException
from bson import ObjectId

from backend.database import get_database


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(
        password.encode("utf-8"), password_hash.encode("utf-8")
    )


async def get_current_user(request: Request) -> dict | None:
    """
    Read the current user from session cookie.
    Returns user dict (with _id as string) or None if not logged in.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    try:
        db = get_database()
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None
    if not user:
        return None
    user["_id"] = str(user["_id"])
    return user


async def require_login(request: Request) -> dict:
    """
    Dependency that requires a logged-in user.
    Raises HTTPException with redirect if not authenticated.
    """
    user = await get_current_user(request)
    if user is None:
        raise HTTPException(
            status_code=303,
            headers={"Location": "/login"},
            detail="Not authenticated",
        )
    return user
