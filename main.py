from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import config
import asyncio
from database import Base
from routes import router
from database import Base, engine
import logging
from sqlalchemy.ext.asyncio import AsyncEngine

app = FastAPI()

# Templates folder setup
templates = Jinja2Templates(directory="templates")

# ✅ Mount the static folder to serve images, CSS, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Logging setup
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Include your routes
app.include_router(router)

# Home route (for index.html)
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Form page route (for form.html)
@app.get("/form")
async def show_form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

# Create database tables on app startup
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Global exception handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
    )
