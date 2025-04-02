import asyncio
import httpx
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import UserPreference
from config import get_db
import time
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
router = APIRouter()

FOURSQUARE_API_KEY = "fsq3Uz0C6s6XLGU4xB+lQOfNa0Q/BPxiV5edWxVY9wpZV/I="  # Keep secure in production

class NominatimLimiter:
    last_request = 0
    
    @classmethod
    async def wait(cls):
        elapsed = time.time() - cls.last_request
        if elapsed < 1:
            await asyncio.sleep(1 - elapsed)
        cls.last_request = time.time()

async def get_coordinates(location: str):
    await NominatimLimiter.wait()
    async with httpx.AsyncClient() as client:
        url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json"
        headers = {'User-Agent': 'TravelAI/1.0'}
        response = await client.get(url, headers=headers)
        if response.status_code != 200 or not response.json():
            return None
        data = response.json()[0]
        return float(data['lat']), float(data['lon'])

async def get_places(lat: float, lon: float, interest: str):
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
      node["tourism"](around:5000,{lat},{lon});
      node["amenity"~"{interest}"](around:5000,{lat},{lon});
      way["tourism"](around:5000,{lat},{lon});
      way["amenity"~"{interest}"](around:5000,{lat},{lon});
    );
    out center;
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(overpass_url, params={'data': query})
        if response.status_code != 200:
            return []
        data = response.json()
        return [element['tags']['name'] for element in data.get('elements', []) if 'tags' in element and 'name' in element['tags']]

async def get_foursquare_restaurants(lat: float, lon: float, budget: int):
    price_range = "1,2" if budget < 1500 else "2,3" if budget < 3000 else "3,4"
    url = f"https://api.foursquare.com/v3/places/search?ll={lat},{lon}&categories=13000&limit=3&price={price_range}"
    headers = {"Accept": "application/json", "Authorization": FOURSQUARE_API_KEY}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return [place["name"] for place in response.json().get("results", []) if "name" in place]
    except Exception as e:
        print(f"Foursquare API error: {e}")
    return [f"Local {budget}-budget restaurant"]

@router.post("/submit/")
async def submit_preferences(
    request: Request,
    source: str = Form(...),
    destination: str = Form(...),
    duration: int = Form(...),
    budget: str = Form(...),
    interests: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        budget_int = int(budget)
        pref = UserPreference(source=source, destination=destination, duration=duration, budget=budget_int, interests=interests)
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
        return RedirectResponse(url=f"/itinerary/{pref.id}", status_code=303)
    except Exception as e:
        print(f"Error saving preferences: {e}")
        await db.rollback()
        return templates.TemplateResponse("error.html", {"request": request, "message": "Database error. Please try again."})

@router.get("/itinerary/{user_id}", name="show_itinerary")
async def show_itinerary(request: Request, user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        itinerary = await generate_itinerary(user_id, db)
        return templates.TemplateResponse("itinerary.html", {"request": request, "itinerary": itinerary})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to display itinerary: {str(e)}")

@router.get("/generate-itinerary/{user_id}")
async def generate_itinerary(user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(UserPreference).where(UserPreference.id == user_id))
        pref = result.scalars().first()
        if not pref:
            raise HTTPException(status_code=404, detail="User not found")
        
        interests = [i.strip() for i in pref.interests.split(',') if i.strip()]
        interests = interests if interests else ["sightseeing"]
        
        coords = await get_coordinates(pref.destination)
        if not coords:
            raise HTTPException(status_code=400, detail="Location not found")
        lat, lon = coords
        
        itinerary = {"destination": pref.destination, "duration": pref.duration, "budget": pref.budget, "route": []}
        
        for day in range(1, pref.duration + 1):
            interest_idx = day % len(interests) if interests else 0
            attraction, restaurants, activity = await asyncio.gather(
                get_places(lat, lon, "attraction"),
                get_foursquare_restaurants(lat, lon, pref.budget),
                get_places(lat, lon, interests[interest_idx])
            )
            
            day_plan = {
                "day": day,
                "activities": [
                    {"time": "9:00 AM", "place": attraction[0] if attraction else "Popular attraction", "activity": "Sightseeing", "type": "Attraction"},
                    {"time": "12:00 PM", "place": restaurants[0] if restaurants else "Local restaurant", "activity": "Lunch", "type": "Dining", "budget_level": pref.budget},
                    {"time": "2:00 PM", "place": activity[0] if activity else f"{interests[interest_idx]} spot", "activity": interests[interest_idx].capitalize(), "type": "Activity"}
                ]
            }
            itinerary["route"].append(day_plan)
        
        return itinerary
    except Exception as e:
        print(f"Error generating itinerary: {str(e)}")
        raise HTTPException(status_code=500, detail="Itinerary generation failed")
