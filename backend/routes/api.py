"""
API routes
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/hello")
async def hello():
    """
    Returns a hardcoded hello stranger message
    """
    return {"message": "hello stranger"}

