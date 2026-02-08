"""
FastAPI backend application
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from backend.routes import api

app = FastAPI(title="TrainingCur App", version="1.0.0")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount static files (CSS, JS, images, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routes
app.include_router(api.router, prefix="/api", tags=["api"])


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Main frontend page
    """
    return templates.TemplateResponse("index.html", {"request": request})

