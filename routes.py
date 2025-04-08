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
import logging
from schemas import ItineraryResponse, ItineraryDay

templates = Jinja2Templates(directory="templates")
router = APIRouter()

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) 

# Create console handler
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

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
async def get_google_places(lat: float, lon: float, keyword: str, budget: int, place_type: str = None) -> list:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Smarter radius calculation based on urban/rural areas
            radius = 50000 if "tourist" in keyword else 20000
            
            # Better budget mapping
            price_level = min(max(budget//2000, 4), 1)  # 1-4 scale
            
            # Base parameters
            params = {
                "location": f"{lat},{lon}",
                "radius": radius,
                "key": GOOGLE_API_KEY,
                "language": "en",
                "rankby": "prominence"  # Get most popular places first
            }
            
            # Dynamic keyword handling
            keyword_mapping = {
                "museums": "museum|art+exhibition",
                "culture": "cultural+center|historical+site",
                "nature": "park|garden|nature+reserve"
            }
            params["keyword"] = keyword_mapping.get(keyword.lower(), keyword)
            
            if place_type:
                params["type"] = place_type
            
            # First try - precise search
            response = await client.get(
                "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                params=params
            )
            
            data = response.json()
            
            # Fallback to broader search if no results
            if data.get("status") == "ZERO_RESULTS":
                params.pop("keyword", None)  # Remove keyword filter
                response = await client.get(
                    "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                    params=params
                )
                data = response.json()
            
            # Process results
            if data.get("status") == "OK":
                return [
                    place["name"] for place in data.get("results", [])
                    if place.get("business_status") == "OPERATIONAL"
                ][:15]  # Return top 15 results
            
            return []
            
    except Exception as e:
        logger.error(f"Google API error: {str(e)}")
        return []
    
async def get_osm_places(lat: float, lon: float, query: str) -> list:
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://nominatim.openstreetmap.org/search.php?q={query}+near+{lat},{lon}&format=jsonv2"
            headers = {"User-Agent": "TravelItineraryApp/1.0"}
            response = await client.get(url, headers=headers)
            return [item["display_name"] for item in response.json()[:10]]
    except Exception:
        return []

async def get_foursquare_places(lat: float, lon: float, category: str) -> list:
    try:
        async with httpx.AsyncClient() as client:
            url = "https://api.foursquare.com/v3/places/search"
            headers = {
                "Authorization": "fsq3Uz0C6s6XLGU4xB+lQOfNa0Q/BPxiV5edWxVY9wpZV/I= ",  # Get free key from developer.foursquare.com
                "Accept": "application/json"
            }
            params = {
                "ll": f"{lat},{lon}",
                "query": category,
                "limit": 10
            }
            response = await client.get(url, headers=headers, params=params)
            return [item["name"] for item in response.json().get("results", [])]
    except Exception:
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
        itinerary_dict = itinerary.dict()
        return templates.TemplateResponse("itinerary.html", {"request": request, "itinerary": itinerary})
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error displaying itinerary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to display itinerary: {str(e)}")
    
@router.get("/generate-itinerary/{user_id}")
# async def generate_itinerary(user_id: int, db: AsyncSession = Depends(get_db)):
#     try:
#         result = await db.execute(select(UserPreference).where(UserPreference.id == user_id))
#         pref = result.scalars().first()
#         if not pref:
#             raise HTTPException(status_code=404, detail="User not found")

#         coords = await get_coordinates_google(pref.destination)
#         if not coords:
#             raise HTTPException(status_code=400, detail="Invalid destination")
#         lat, lon = coords

#         interests = [i.strip() for i in pref.interests.split(',') if i.strip()] or ["sightseeing"]

#         itinerary = {
#             "destination": pref.destination,
#             "start_date": str(pref.travel_date),
#             "duration": pref.duration,
#             "budget": f"${pref.budget}",
#             "food_preferences": {
#                 "halal": bool(pref.halal),
#                 "vegetarian": bool(pref.vegetarian)
#             },
#             "route": [],
#             "transport_mode": await get_transport_mode(pref.source, pref.destination)
#         }

#         for day in range(1, pref.duration + 1):
#             interest = interests[(day - 1) % len(interests)]

#             attraction_task = get_google_places(lat, lon, "tourist attraction", pref.budget, place_type="tourist_attraction")
#             restaurant_task = get_google_places(lat, lon, "restaurant", pref.budget, place_type="restaurant")
#             activity_task = get_google_places(lat, lon, interest, pref.budget)
#             hotel_task = get_google_places(lat, lon, "hotel", pref.budget, place_type="lodging")

#             attraction_list, restaurant_list, activity_list, hotel_list = await asyncio.gather(
#                 attraction_task, restaurant_task, activity_task, hotel_task
#             )

#             def pick(place_list, fallback):
#                 return random.choice(place_list) if place_list else f"No {fallback} found"

#             food_desc = []
#             if pref.halal:
#                 food_desc.append("Halal-friendly")
#             if pref.vegetarian:
#                 food_desc.append("Vegetarian")

#             day_plan = {
#                 "day": f"Day {day}",
#                 "plan": [
#                     pick(attraction_list, "tourist attraction"),
#                     f"Lunch spot: {pick(restaurant_list, 'restaurant')}" + (f" ({', '.join(food_desc)})" if food_desc else ""),
#                     f"Activity: {pick(activity_list, interest)} ({interest.capitalize()})",
#                     f"Stay: {pick(hotel_list, 'hotel')}"
#                 ]
#             }

#             itinerary["route"].append(day_plan)

#         return itinerary
async def generate_itinerary(user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        # Fetch user preferences
        result = await db.execute(select(UserPreference).where(UserPreference.id == user_id))
        pref = result.scalars().first()
        if not pref:
            raise HTTPException(status_code=404, detail="User not found")

        # Get coordinates with fallback to Golden Temple if needed
        coords = await get_coordinates_google(pref.destination) or (31.6200, 74.8765)
        lat, lon = coords

        # Process interests with fallback to sightseeing
        interests = [i.strip() for i in pref.interests.split(',') if i.strip()] or ["sightseeing"]

        # Keep track of all suggested places to avoid repetition
        used_attractions = set()
        used_restaurants = set()
        used_activities = set()
        used_hotels = set()

        # Enhanced place fetcher with fallbacks
        async def get_places_with_fallbacks(category: str, place_type: str = None) -> list:
            """Get places from multiple sources with fallback logic"""
            # Try Google first
            results = await get_google_places(lat, lon, category, pref.budget, place_type)
            
            # Fallback to OSM for broader results if needed
            if len(results) < 5:  # Increased minimum to get more options
                osm_results = await get_osm_places(lat, lon, category)
                results.extend(x for x in osm_results if x not in results)
            
            # Final fallback to Foursquare for specific types
            if len(results) < 5 and place_type:
                fsq_results = await get_foursquare_places(lat, lon, place_type)
                results.extend(x for x in fsq_results if x not in results)
            
            # Ensure unique results
            return list(set(results))

        # Initialize empty lists to store each day's data
        days_list = []

        # Fetch a larger pool of all options at once to select from
        all_attractions_task = get_places_with_fallbacks("attraction", "tourist_attraction")
        all_restaurants_task = get_places_with_fallbacks("restaurant", "restaurant")
        all_hotels_task = get_places_with_fallbacks("hotel", "lodging")
        
        # Start fetching these right away
        all_attractions_future = asyncio.create_task(all_attractions_task)
        all_restaurants_future = asyncio.create_task(all_restaurants_task)
        all_hotels_future = asyncio.create_task(all_hotels_task)
        
        # Dictionary to store activity options by interest type
        interest_activities = {}

        # Generate each day's itinerary
        for day in range(1, pref.duration + 1):
            interest = interests[(day - 1) % len(interests)]
            
            # Fetch activities for this interest if not already fetched
            if interest not in interest_activities:
                interest_activities[interest] = await get_places_with_fallbacks(interest)
            
            # Get all other options
            if day == 1:
                # Wait for the futures on the first day
                all_attractions = await all_attractions_future
                all_restaurants = await all_restaurants_future
                all_hotels = await all_hotels_future
            
            # Filter out previously used options
            available_attractions = [a for a in all_attractions if a not in used_attractions]
            available_restaurants = [r for r in all_restaurants if r not in used_restaurants]
            available_activities = [a for a in interest_activities[interest] if a not in used_activities]
            available_hotels = [h for h in all_hotels if h not in used_hotels]
            
            # If we're running low on options, fetch more
            if len(available_attractions) < 3:
                more_attractions = await get_places_with_fallbacks(f"attraction in {pref.destination}", "tourist_attraction")
                available_attractions.extend([a for a in more_attractions if a not in used_attractions and a not in available_attractions])
                
            if len(available_restaurants) < 3:
                more_restaurants = await get_places_with_fallbacks(f"restaurant in {pref.destination}", "restaurant")
                available_restaurants.extend([r for r in more_restaurants if r not in used_restaurants and r not in available_restaurants])
                
            if len(available_activities) < 2:
                more_activities = await get_places_with_fallbacks(f"{interest} in {pref.destination}")
                available_activities.extend([a for a in more_activities if a not in used_activities and a not in available_activities])
                
            if len(available_hotels) < 2:
                more_hotels = await get_places_with_fallbacks(f"hotel in {pref.destination}", "lodging")
                available_hotels.extend([h for h in more_hotels if h not in used_hotels and h not in available_hotels])
            
            # Select unique places for this day
            day_attractions = available_attractions[:3]
            day_restaurants = available_restaurants[:3]
            day_activities = available_activities[:2]
            day_hotels = available_hotels[:2]
            
            # Add to used sets to avoid repetition
            used_attractions.update(day_attractions)
            used_restaurants.update(day_restaurants)
            used_activities.update(day_activities)
            used_hotels.update(day_hotels)
            
            # Fallback options if we don't have enough unique places
            if not day_attractions:
                day_attractions = [f"Explore {pref.destination} downtown area"]
            if not day_restaurants:
                day_restaurants = [f"Local cuisine in {pref.destination}"]
            if not day_activities:
                day_activities = [f"{interest.capitalize()} activity in {pref.destination}"]
            if not day_hotels:
                day_hotels = [f"Accommodation in {pref.destination}"]
            
            # Create a day entry according to our Pydantic model
            day_entry = ItineraryDay(
                day=f"Day {day}",
                attractions=day_attractions,
                dining=day_restaurants,
                activities=day_activities,
                hotels=day_hotels
            )
            
            days_list.append(day_entry)

        # Build the structured response according to our Pydantic model
        itinerary = ItineraryResponse(
            destination=pref.destination,
            duration=pref.duration,
            days=days_list
        )

        return itinerary

    except Exception as e:
        logger.error(f"Error generating itinerary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Itinerary generation failed: {str(e)}")
    # except Exception as e:
    #     logger.error(f"Error generating itinerary: {str(e)}", exc_info=True)
    #     raise HTTPException(status_code=500, detail="Itinerary generation failed")

    # except Exception as e:
    #     print(f"Error generating itinerary: {str(e)}")
    #     raise HTTPException(status_code=500, detail="Itinerary generation failed")

