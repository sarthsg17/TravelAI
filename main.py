from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from routes import router

app = FastAPI()

app.include_router(router)

templates = Jinja2Templates(directory="templates")
