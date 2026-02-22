"""
FastAPI backend application - StockFolio
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from backend.database import connect_to_mongo, close_mongo_connection
from backend.routes import api
from backend.routes.auth_routes import router as auth_router
from backend.routes.page_routes import router as page_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown events."""
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(title="StockFolio", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key="stockfolio-secret-key-change-in-production",
    session_cookie="stockfolio_session",
    max_age=86400,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router)
app.include_router(page_router)
app.include_router(api.router, prefix="/api", tags=["api"])
