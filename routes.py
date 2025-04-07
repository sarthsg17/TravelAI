import asyncio
import httpx
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import UserPreference
from config import get_db, GOOGLE_API_KEY
from fastapi.templating import Jinja2Templates
import urllib.parse
import random
from typing import Optional

templates = Jinja2Templates(directory="templates")
router = APIRouter()

# Get coordinates using Google Maps Geocoding API
async def get_coordinates_google(location: str):
    async with httpx.AsyncClient() as client:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(location)}&key={GOOGLE_API_KEY}"
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            if data["results"]:
                loc = data["results"][0]["geometry"]["location"]
                return loc["lat"], loc["lng"]
    return None

# Get places (attractions, restaurants, activities, accommodations)
async def get_google_places(lat, lon, keyword, budget, place_type=None):
    async with httpx.AsyncClient() as client:
        radius = 5000
        price_level = 1 if budget < 1500 else 2 if budget < 3000 else 4
        url = (
            f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            f"?location={lat},{lon}&radius={radius}&keyword={urllib.parse.quote(keyword)}"
            f"&minprice=0&maxprice={price_level}&key={GOOGLE_API_KEY}"
        )
        if place_type:
            url += f"&type={place_type}"
        
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if not results:
                print(f"No results found for keyword: {keyword}, type: {place_type} at {lat}, {lon}")
            sorted_places = sorted(
                results,
                key=lambda x: x.get("rating", 0),
                reverse=True
            )
            return [place["name"] for place in sorted_places if "name" in place]
        else:
            print(f"Google Places API Error: {response.status_code}, {response.text}")
    return []


# Get directions between source and destination using Google Directions API
async def get_transport_mode(source, destination):
    async with httpx.AsyncClient() as client:
        url = f"https://maps.googleapis.com/maps/api/directions/json?origin={urllib.parse.quote(source)}&destination={urllib.parse.quote(destination)}&key={GOOGLE_API_KEY}"
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            if data["routes"]:
                steps = data["routes"][0]["legs"][0].get("steps", [])
                modes = list(set([step["travel_mode"] for step in steps if "travel_mode" in step]))
                return ", ".join(modes)
    return "Data not available"


@router.post("/submit/")
async def submit_preferences(
    request: Request,
    source: str = Form(...),
    destination: str = Form(...),
    duration: int = Form(...),
    budget: str = Form(...),
    interests: str = Form(...),
    halal: Optional[bool] = Form(False),
    vegetarian: Optional[bool] = Form(False),
    travel_date: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        budget_int = int(budget)

        pref = UserPreference(
            source=source,
            destination=destination,
            duration=duration,
            budget=budget_int,
            interests=interests,
            halal=halal,
            vegetarian=vegetarian,
            travel_date=travel_date
        )

        db.add(pref)
        await db.commit()
        await db.refresh(pref)
        return RedirectResponse(url=f"/itinerary/{pref.id}", status_code=303)

    except Exception as e:
        await db.rollback()
        print("Database Error:", e)
        return templates.TemplateResponse("error.html", {
            "request": request,
            "message": "Database error. Please try again."
        })

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

        coords = await get_coordinates_google(pref.destination)
        if not coords:
            raise HTTPException(status_code=400, detail="Invalid destination")
        lat, lon = coords

        interests = [i.strip() for i in pref.interests.split(',') if i.strip()] or ["sightseeing"]

        itinerary = {
            "destination": pref.destination,
            "start_date": str(pref.travel_date),
            "duration": pref.duration,
            "budget": f"${pref.budget}",
            "food_preferences": {
                "halal": bool(pref.halal),
                "vegetarian": bool(pref.vegetarian)
            },
            "route": [],
            "transport_mode": await get_transport_mode(pref.source, pref.destination)
        }

        for day in range(1, pref.duration + 1):
            interest = interests[(day - 1) % len(interests)]

            attraction_task = get_google_places(lat, lon, "tourist attraction", pref.budget, place_type="tourist_attraction")
            restaurant_task = get_google_places(lat, lon, "restaurant", pref.budget, place_type="restaurant")
            activity_task = get_google_places(lat, lon, interest, pref.budget)
            hotel_task = get_google_places(lat, lon, "hotel", pref.budget, place_type="lodging")

            attraction_list, restaurant_list, activity_list, hotel_list = await asyncio.gather(
                attraction_task, restaurant_task, activity_task, hotel_task
            )

            def pick(place_list, fallback):
                return random.choice(place_list) if place_list else f"No {fallback} found"

            food_desc = []
            if pref.halal:
                food_desc.append("Halal-friendly")
            if pref.vegetarian:
                food_desc.append("Vegetarian")

            day_plan = {
                "day": f"Day {day}",
                "plan": [
                    pick(attraction_list, "tourist attraction"),
                    f"Lunch spot: {pick(restaurant_list, 'restaurant')}" + (f" ({', '.join(food_desc)})" if food_desc else ""),
                    f"Activity: {pick(activity_list, interest)} ({interest.capitalize()})",
                    f"Stay: {pick(hotel_list, 'hotel')}"
                ]
            }

            itinerary["route"].append(day_plan)

        return itinerary

    except Exception as e:
        print(f"Error generating itinerary: {str(e)}")
        raise HTTPException(status_code=500, detail="Itinerary generation failed")

