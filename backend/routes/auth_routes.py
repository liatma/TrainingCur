"""
Authentication routes: login, register, logout.
"""
from datetime import datetime
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER

from backend.database import get_database
from backend.auth import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
):
    """Register a new user."""
    db = get_database()
    existing = await db.users.find_one({"username": username})
    if existing:
        request.session["flash"] = "Username already taken."
        return RedirectResponse(url="/register", status_code=HTTP_303_SEE_OTHER)

    await db.users.insert_one({
        "username": username,
        "password_hash": hash_password(password),
        "display_name": display_name,
        "created_at": datetime.utcnow(),
    })

    request.session["flash"] = "Registration successful! Please log in."
    return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    """Log in an existing user."""
    db = get_database()
    user = await db.users.find_one({"username": username})
    if not user or not verify_password(password, user["password_hash"]):
        request.session["flash"] = "Invalid username or password."
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    request.session["user_id"] = str(user["_id"])
    request.session["display_name"] = user["display_name"]

    return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)


@router.get("/logout")
async def logout(request: Request):
    """Log out the current user."""
    request.session.clear()
    return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)
