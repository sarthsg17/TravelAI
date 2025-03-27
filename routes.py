from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
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
    request: Request,  
    username: str = Form(...),
    destination: str = Form(...),
    duration: int = Form(...),
    budget: float = Form(...),
    interests: str = Form(...),
    db: Session = Depends(get_db),
):
    # 🔹 Check if the username already exists
    existing_user = db.query(UserPreference).filter(UserPreference.username == username).first()
    
    if existing_user:
        return templates.TemplateResponse(
            "form.html", 
            {"request": request, "message": "Error: Username already exists!"}
        )

    # 🔹 Add the new record if username is unique
    new_pref = UserPreference(
        username=username,
        destination=destination,
        duration=duration,
        budget=budget,
        interests=interests,
    )
    db.add(new_pref)
    
    try:
        db.commit()
        return templates.TemplateResponse(
            "form.html", 
            {"request": request, "message": "Preferences saved successfully!"}
        )
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            "form.html", 
            {"request": request, "message": "Error: Username already exists!"}
        )
