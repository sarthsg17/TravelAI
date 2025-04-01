from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal
from models import UserPreference

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse("form.html", {"request": request, "message": None})

@router.post("/submit/")
async def submit_preferences(
    request: Request,  # 🔹 Add this parameter
    destination: str = Form(...),
    duration: int = Form(...),
    budget: float = Form(...),
    interests: str = Form(...),
    db: Session = Depends(get_db),
):
    new_pref = UserPreference(
        destination=destination,
        duration=duration,
        budget=budget,
        interests=interests,
    )
    db.add(new_pref)
    db.commit()
    
    return templates.TemplateResponse(
        "form.html", 
        {"request": request, "message": "Preferences saved successfully!"}
    )