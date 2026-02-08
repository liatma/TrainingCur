# TrainingCur Web Application

A Python web application with FastAPI backend and Jinja2 frontend.

## Features

- **Backend**: FastAPI-based REST API
- **Frontend**: Jinja2 templated HTML with modern styling
- **Architecture**: Extensible structure for adding new features

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

3. Open your browser and navigate to:
```
http://localhost:8000
```

## Project Structure

```
TrainingCur/
├── backend/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   └── routes/
│       ├── __init__.py
│       └── api.py       # API endpoints
├── templates/
│   └── index.html       # Frontend template
├── static/
│   ├── style.css        # CSS styles
│   └── app.js           # Frontend JavaScript
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## API Endpoints

- `GET /api/hello` - Returns a hardcoded "hello stranger" message
- `GET /` - Frontend homepage

## Adding New Features

### Adding a new API endpoint:

1. Create or update a route in `backend/routes/api.py`:
```python
@router.get("/your-endpoint")
async def your_handler():
    return {"data": "your data"}
```

### Adding a new frontend page:

1. Create a new template in `templates/`
2. Add a route in `backend/main.py`:
```python
@app.get("/your-page", response_class=HTMLResponse)
async def your_page(request: Request):
    return templates.TemplateResponse("your-template.html", {"request": request})
```

## Development

The application runs with auto-reload enabled, so changes will automatically refresh when you save files.

