# StockFolio (TrainingCur)

A Python web application for managing stock market portfolios: FastAPI backend, Jinja2-templated pages, MongoDB storage, and session-based authentication.

**Goal:** Let an investor manage their portfolio (stocks, ETFs, other assets). For each symbol, track purchases by date and price to compute gain/loss. Provide symbol overview, purchase details, and analysis (e.g. TradingView charts). The investor logs in to see a dashboard, add assets, record purchases and dividends, and view per-asset summaries and company data.

---

## Application overview

- **Landing** — Description and login/register entry.
- **Auth** — Login and register (cookie-based session; passwords hashed with bcrypt).
- **Dashboard** — Portfolio summary (total invested, value, profit/loss, dividends) and a grid of asset cards. Each card links to the asset.
- **Asset gateway** — Each asset has three views, reached from a **left-side menu**:
  - **Overview** — Name, symbol, exchange, current price, summary metrics (units, total paid, value, fees, dividends, P/L, status), last 3 transactions, TradingView chart, delete asset. “View all” links to Purchase details if there are more than 3 transactions.
  - **Company details** — yfinance-derived company/asset info (sector, industry, market cap, valuation, dividends, risk, analysts, profile). Data is grouped and only shown when present.
  - **Purchase details** — Full transaction history (table) and **Add Transaction** form (purchase or dividend: date, price/unit, quantity, fees, or dividend amount).
- **Transactions** — Two types: **purchase** (debit = price×quantity + fees) and **dividend** (credit = amount). Totals and P/L include fees and dividends.
- **Live data** — Prices and company info from Yahoo Finance (yfinance). TradingView widget for charts on the asset Overview.

---

## Features

- **Backend:** FastAPI REST API (assets, transactions, stock lookup) with async MongoDB (PyMongo).
- **Frontend:** Jinja2 HTML templates (base, landing, login, register, dashboard, asset base/gateway and related views), shared layout, static CSS/JS.
- **Auth:** Cookie-based sessions (Starlette `SessionMiddleware`, signed with itsdangerous), bcrypt password hashing, login/register/logout.
- **Data:** MongoDB `portfolio_db`: collections `users`, `assets`, `transactions`. Indexes on `username`, `user_id`, `asset_id`.
- **Stock data:** yfinance for quotes and company info; 5‑minute in-memory cache per symbol.
- **Migration:** Optional script to import transactions from a BSON dump (see [Migration](#migration)).

---

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **MongoDB**  
   Ensure MongoDB is running. Default connection: `mongodb://localhost:27017`. Database name: `portfolio_db`.

3. **Run the application**
   ```bash
   python main.py
   ```

4. **Browser**  
   Open **http://localhost:8000** (or http://127.0.0.1:8000 on Windows).

---

## Dependencies (`requirements.txt`)

| Package | Version | Usage in this application |
|--------|---------|----------------------------|
| **fastapi** | 0.104.1 | Web framework: `FastAPI`, `APIRouter`, `Request`, `Form`, `StaticFiles`, `Jinja2Templates`, `HTMLResponse`, `RedirectResponse`, `JSONResponse`, `HTTPException`. Used in `backend/main.py` and all route modules. |
| **uvicorn[standard]** | 0.24.0 | ASGI server. `main.py` runs `uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)`. |
| **jinja2** | 3.1.2 | HTML templating via FastAPI’s `Jinja2Templates` in `backend/routes/page_routes.py` for all rendered pages. |
| **python-multipart** | 0.0.6 | Form parsing. Required by FastAPI for `Form(...)`. Used in `backend/routes/auth_routes.py` for login and register. |
| **pymongo** | 4.14.1 | MongoDB async driver. `backend/database.py`: `AsyncMongoClient`, indexes. Routes and `migrate_transactions.py` use the same DB. |
| **yfinance** | 1.1.0 | Yahoo Finance. `backend/services/stock_service.py`: quotes, company info, symbol lookup; used by dashboard, asset pages, and migration. |
| **bcrypt** | 4.1.2 | Password hashing. `backend/auth.py`: `hash_password()` (register), `verify_password()` (login). |
| **itsdangerous** | 2.1.2 | Signing. Used by Starlette’s `SessionMiddleware` to sign the session cookie. |
| **starlette** | 0.27.0 | `SessionMiddleware` in `backend/main.py`; status codes (e.g. `HTTP_303_SEE_OTHER`) in routes and auth. |

---

## Data model

- **users** — `username` (unique), `password` (bcrypt hash), `display_name`, `created_at`.
- **assets** — `user_id`, `symbol`, `name`, `exchange`, `asset_type` (e.g. stock, etf), `created_at`. One asset per user per symbol.
- **transactions** — `asset_id`, `transaction_type` (`"purchase"` or `"dividend"`), `price_per_unit`, `quantity`, `purchase_date`, `fees`, `debit`, `credit`, `notes`, `created_at`. Purchases: debit = price×quantity + fees; dividends: credit = amount.

---

## Routes and pages

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Landing page. |
| GET | `/login` | Login form. |
| GET | `/register` | Registration form. |
| POST | `/auth/login` | Login (form). |
| POST | `/auth/register` | Register (form). |
| GET | `/auth/logout` | Logout. |
| GET | `/dashboard` | Dashboard (auth required). |
| GET | `/dashboard/asset/{id}` | Asset **Overview** (gateway): summary, last 3 transactions, TradingView. |
| GET | `/dashboard/asset/{id}/company` | **Company details** page (yfinance data). |
| GET | `/dashboard/asset/{id}/purchases` | **Purchase details**: full transaction table + Add Transaction form. |
| GET | `/api/hello` | Hello message. |
| GET | `/api/stock/{symbol}` | Live stock info (JSON). |
| POST | `/api/assets` | Create asset (auth). |
| DELETE | `/api/assets/{id}` | Delete asset (auth). |
| POST | `/api/assets/{id}/transactions` | Add transaction (auth). |
| DELETE | `/api/assets/{id}/transactions/{tid}` | Delete transaction (auth). |

---

## Project structure

```
TrainingCur/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan, SessionMiddleware, static, routers
│   ├── auth.py              # bcrypt hash/verify, get_current_user from session
│   ├── database.py          # AsyncMongoClient, connect/close, indexes, get_database
│   ├── models.py            # Pydantic: UserCreate, AssetCreate, TransactionCreate, responses
│   ├── routes/
│   │   ├── api.py           # REST: hello, stock, assets, transactions
│   │   ├── auth_routes.py   # Login, register, logout (Form + session)
│   │   └── page_routes.py   # All HTML routes; _load_asset_context; gateway/company/purchases
│   └── services/
│       └── stock_service.py # yfinance: get_stock_info (incl. company fields), lookup_symbol, cache
├── templates/
│   ├── base.html            # Layout, nav, flash
│   ├── landing.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── index.html
│   ├── asset_base.html      # Shared asset layout + left nav (Overview, Company details, Purchase details)
│   ├── asset_gateway.html   # Overview content
│   ├── asset_detail.html    # Legacy single-page asset view (if still used)
│   ├── asset_company.html   # Company details content (required by route)
│   └── asset_purchases.html # Purchase details content (required by route)
├── static/
│   ├── style.css
│   └── app.js               # Modals, lookup, add asset, add transaction, delete, transaction type toggle
├── main.py                  # uvicorn entry point
├── requirements.txt
├── migrate_transactions.py  # Import BSON dump into portfolio_db (see Migration)
└── README.md
```

---

## Migration

`migrate_transactions.py` imports transactions from a MongoDB BSON dump (e.g. from another app) into this app’s `portfolio_db`:

1. Connects to `portfolio_db`, looks up the given username.
2. Deletes existing documents in `transactions`.
3. For each unique symbol in the dump: ensures an asset exists for that user (creates with yfinance name/exchange if missing).
4. Maps each source document to the app’s transaction schema (transaction_type, purchase_date, fees, debit, credit, etc.) and bulk-inserts.

**Usage:** `python migrate_transactions.py <username> [path_to_Transactions.bson]`

---

## Adding new features

- **New API endpoint:** Add or extend routes in `backend/routes/api.py`. Use `get_current_user(request)` for protected endpoints.
- **New page:** Add a template under `templates/`, then a route in `backend/routes/page_routes.py` with `templates.TemplateResponse(...)`.
- **New company data field:** Add the key in `backend/services/stock_service.py` inside the `ticker.info` block and in the returned dict; then show it in `templates/asset_company.html`.

---

## Development

The app runs with Uvicorn `reload=True`; code and template changes trigger an automatic restart.
