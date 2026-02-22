# TrainingCur Web Application

A Python web application (StockFolio) with a FastAPI backend, Jinja2-templated frontend, MongoDB storage, and session-based authentication.

## Features

- **Backend**: FastAPI-based REST API with async MongoDB (PyMongo)
- **Frontend**: Jinja2-templated HTML with modern styling
- **Auth**: Cookie-based sessions (Starlette), password hashing (bcrypt), login/register
- **Data**: Portfolio assets and transactions stored in MongoDB; live stock data via yfinance
- **Architecture**: Extensible structure for adding new features

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure MongoDB is running (default: `mongodb://localhost:27017`).

3. Run the application:
```bash
python main.py
```

4. Open your browser and navigate to:
```
http://localhost:8000
```

## Dependencies (`requirements.txt`)

Every listed package and how it is used in this application:

| Package | Version | Usage in this application |
|--------|---------|----------------------------|
| **fastapi** | 0.104.1 | Core web framework: `FastAPI` app, `APIRouter`, `Request`, `Form`, `Depends`, `StaticFiles`, `HTMLResponse`, `RedirectResponse`, `JSONResponse`, `Jinja2Templates`, `HTTPException`. Used in `backend/main.py`, `backend/routes/api.py`, `backend/routes/auth_routes.py`, `backend/routes/page_routes.py`, and `backend/auth.py`. |
| **uvicorn[standard]** | 0.24.0 | ASGI server that runs the app. Used in `main.py` to start the server with `uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)`. |
| **jinja2** | 3.1.2 | HTML templating. Used via FastAPI’s `Jinja2Templates` in `backend/routes/page_routes.py` to render pages (landing, login, register, dashboard, asset detail, company details). |
| **python-multipart** | 0.0.6 | Parsing form data. Required by FastAPI when using `Form(...)`. Used in `backend/routes/auth_routes.py` for login and register endpoints (`username`, `password`, `display_name`). |
| **pymongo** | 4.14.1 | MongoDB driver. Used in `backend/database.py` with `AsyncMongoClient` for connection, indexes, and database access. Also used in `migrate_transactions.py` for migration scripts. |
| **yfinance** | 1.1.0 | Yahoo Finance data. Used in `backend/services/stock_service.py` for live quotes, company info, symbol validation, and in `migrate_transactions.py` for name/exchange lookups. |
| **bcrypt** | 4.1.2 | Password hashing. Used in `backend/auth.py` for `hash_password()` (registration) and `verify_password()` (login). |
| **itsdangerous** | 2.1.2 | Secure signing (e.g. cookies). Dependency of Starlette’s `SessionMiddleware`; used indirectly for signing session cookies. |
| **starlette** | 0.27.0 | ASGI toolkit. Used in `backend/main.py` for `SessionMiddleware` (cookie-based sessions), and in `backend/auth.py` and route modules for `HTTP_303_SEE_OTHER` and status codes. |

## Project Structure

```
TrainingCur/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan, SessionMiddleware, static mount, routers
│   ├── auth.py              # Password hashing (bcrypt), session/user helpers
│   ├── database.py          # MongoDB connection (pymongo AsyncMongoClient)
│   ├── routes/
│   │   ├── api.py           # REST API: hello, stock lookup, assets, transactions
│   │   ├── auth_routes.py   # Login, register, logout (Form + sessions)
│   │   └── page_routes.py   # HTML pages via Jinja2 (landing, login, register, dashboard, asset/company)
│   └── services/
│       └── stock_service.py # yfinance-based stock info and caching
├── templates/               # Jinja2 HTML templates
├── static/                  # CSS, JS, assets
├── main.py                  # Entry point: uvicorn.run(backend.main:app)
├── requirements.txt         # Python dependencies
├── migrate_transactions.py  # Optional migration script (pymongo, yfinance)
└── README.md
```

## API Endpoints

- `GET /api/hello` — Returns a hardcoded "hello stranger" message
- `GET /api/stock/{symbol}` — Live stock info (via yfinance)
- `POST /api/assets` — Add asset (auth required)
- `DELETE /api/assets/{asset_id}` — Delete asset (auth required)
- `POST /api/assets/{asset_id}/transactions` — Add purchase or dividend (auth required)
- `DELETE /api/assets/{asset_id}/transactions/{transaction_id}` — Delete transaction (auth required)

Pages: `GET /` (landing), `/login`, `/register`, `/dashboard`, asset and company detail pages.

## Adding New Features

### Adding a new API endpoint

1. Create or update a route in `backend/routes/api.py`:
```python
@router.get("/your-endpoint")
async def your_handler(request: Request):
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    return {"data": "your data"}
```

### Adding a new frontend page

1. Add a template in `templates/`.
2. Add a route in `backend/routes/page_routes.py`:
```python
@router.get("/your-page", response_class=HTMLResponse)
async def your_page(request: Request):
    return templates.TemplateResponse("your-template.html", {"request": request})
```

## Development

The application runs with auto-reload enabled (`reload=True` in `main.py`), so changes will refresh when you save files.
