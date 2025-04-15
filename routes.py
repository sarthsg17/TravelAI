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
from typing import Optional, List, Dict
import logging
from schemas import ItineraryResponse, ItineraryDay

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) 

# Create console handler
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Initialize templates once
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

# Get places with their place_ids for further details
async def get_google_places(lat: float, lon: float, keyword: str, budget: int, place_type: str = None) -> List[Dict]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Smarter radius calculation based on urban/rural areas
            radius = 50000 if "tourist" in keyword else 20000
            
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
            
            # Process results - return dict with place info
            if data.get("status") == "OK":
                return [
                    {
                        "name": place["name"],
                        "place_id": place.get("place_id", ""),
                        "price_level": place.get("price_level", 0),
                        "rating": place.get("rating", 0),
                        "location": place.get("geometry", {}).get("location", {})
                    }
                    for place in data.get("results", [])
                    if place.get("business_status", "OPERATIONAL") == "OPERATIONAL"
                ][:15]  # Return top 15 results
            
            return []
            
    except Exception as e:
        logger.error(f"Google API error: {str(e)}")
        return []
    
async def get_osm_places(lat: float, lon: float, query: str) -> List[Dict]:
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://nominatim.openstreetmap.org/search.php?q={query}+near+{lat},{lon}&format=jsonv2"
            headers = {"User-Agent": "TravelItineraryApp/1.0"}
            response = await client.get(url, headers=headers)
            return [
                {
                    "name": item["display_name"],
                    "place_id": item.get("osm_id", ""),
                    "price_level": 0,  # OSM doesn't provide price level
                    "rating": 0,
                    "location": {"lat": float(item.get("lat", lat)), "lng": float(item.get("lon", lon))}
                }
                for item in response.json()[:10]
            ]
    except Exception as e:
        logger.error(f"OSM API error: {str(e)}")
        return []

async def get_foursquare_places(lat: float, lon: float, category: str) -> List[Dict]:
    try:
        async with httpx.AsyncClient() as client:
            url = "https://api.foursquare.com/v3/places/search"
            headers = {
                "Authorization": "fsq3Uz0C6s6XLGU4xB+lQOfNa0Q/BPxiV5edWxVY9wpZV/I=",
                "Accept": "application/json"
            }
            params = {
                "ll": f"{lat},{lon}",
                "query": category,
                "limit": 10
            }
            response = await client.get(url, headers=headers, params=params)
            data = response.json()
            return [
                {
                    "name": item.get("name", ""),
                    "place_id": item.get("fsq_id", ""),
                    "price_level": int(item.get("price", 0)),
                    "rating": item.get("rating", 0) / 2 if item.get("rating") else 0,  # Convert to 5-star scale
                    "location": item.get("geocodes", {}).get("main", {"lat": lat, "lng": lon})
                }
                for item in data.get("results", [])
            ]
    except Exception as e:
        logger.error(f"Foursquare API error: {str(e)}")
        return []

# Get directions between two points and calculate distance and time
async def get_directions(origin_lat, origin_lng, dest_lat, dest_lng, mode="driving"):
    try:
        async with httpx.AsyncClient() as client:
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": f"{origin_lat},{origin_lng}",
                "destination": f"{dest_lat},{dest_lng}",
                "mode": mode,
                "key": GOOGLE_API_KEY
            }
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "OK" and data.get("routes"):
                    leg = data["routes"][0]["legs"][0]
                    return {
                        "distance": leg["distance"]["value"] / 1000,  # km
                        "duration": leg["duration"]["value"] / 60,    # minutes
                        "transport_mode": mode
                    }
        return {"distance": 0, "duration": 0, "transport_mode": mode}
    except Exception as e:
        logger.error(f"Error getting directions: {str(e)}")
        return {"distance": 0, "duration": 0, "transport_mode": mode}

# Get place details using Google Places API
async def get_place_details(place_id: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://maps.googleapis.com/maps/api/place/details/json"
            params = {
                "place_id": place_id,
                "fields": "name,formatted_address,price_level,rating,types,website,opening_hours,geometry",
                "key": GOOGLE_API_KEY
            }
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "OK":
                    return data.get("result", {})
    except Exception as e:
        logger.error(f"Error fetching place details: {str(e)}")
    return {}

# Calculate costs based on place type and available data
def calculate_place_cost(place_info: dict, place_type: str, budget_level: int) -> float:
    # For explicit price levels from API data
    price_level = place_info.get("price_level", 0)
    
    # Adjust price level if not available based on budget_level
    if price_level == 0:
        # Scale from 1-5 budget levels to 1-4 price levels
        price_level = max(1, min(4, round(budget_level * 0.8)))
    
    # Base costs by category and price level
    cost_matrix = {
        "attraction": {0: 100, 1: 150, 2: 300, 3: 500, 4: 1000},
        "restaurant": {0: 150, 1: 250, 2: 500, 3: 1000, 4: 2000},
        "hotel": {0: 1000, 1: 1500, 2: 3000, 3: 5000, 4: 10000},
        "activity": {0: 200, 1: 300, 2: 600, 3: 1000, 4: 2000}
    }
    
    # Get appropriate category
    if place_type not in cost_matrix:
        place_type = "attraction"  # Default category
    
    # Get cost from matrix using price level
    return cost_matrix[place_type][price_level]

# Calculate transportation cost
def calculate_transport_cost(distance_km: float, mode: str = "driving") -> float:
    # Cost per km by mode
    cost_per_km = {
        "driving": 10,   # ₹10/km for car
        "transit": 5,    # ₹5/km for public transport
        "walking": 0,    # Free for walking
        "bicycling": 2   # ₹2/km for bike rental
    }
    
    return distance_km * cost_per_km.get(mode, 10)  # Default to driving cost

@router.post("/submit/")
async def submit_preferences(
    request: Request,
    source: str = Form(...),
    destination: str = Form(...),
    duration: int = Form(...),
    interests: str = Form(...),
    travel_date: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    try:

        pref = UserPreference(
            source=source,
            destination=destination,
            duration=duration,
            interests=interests,
            travel_date=travel_date
        )

        db.add(pref)
        await db.commit()
        await db.refresh(pref)
        return RedirectResponse(url=f"/itinerary/{pref.id}", status_code=303)

    except Exception as e:
        await db.rollback()
        logger.error(f"Database Error: {str(e)}", exc_info=True)
        return templates.TemplateResponse("error.html", {
            "request": request,
            "message": "Database error. Please try again."
        })

@router.get("/itinerary/{user_id}", name="show_itinerary")
async def show_itinerary(request: Request, user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        # Get user preferences first to access the source
        result = await db.execute(select(UserPreference).where(UserPreference.id == user_id))
        pref = result.scalars().first()
        if not pref:
            raise HTTPException(status_code=404, detail="User not found")
            
        itinerary = await generate_itinerary(user_id, db)
        return templates.TemplateResponse("itinerary.html", {
            "request": request, 
            "itinerary": itinerary,
            "source": pref.source  # Pass source to the template
        })
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error displaying itinerary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to display itinerary: {str(e)}")

@router.get("/generate-itinerary/{user_id}")
async def generate_itinerary(user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(UserPreference).where(UserPreference.id == user_id))
        pref = result.scalars().first()
        if not pref:
            raise HTTPException(status_code=404, detail="User not found")

        # Calculate budget level (1-5)
        budget_level = 1
        
        # Get coordinates for destination
        dest_coords = await get_coordinates_google(pref.destination)
        if not dest_coords:
            dest_coords = (31.6200, 74.8765)  # Default fallback
        dest_lat, dest_lon = dest_coords
        
        # Get coordinates for source
        source_coords = await get_coordinates_google(pref.source)
        if not source_coords:
            # Use a point 100km away as fallback
            source_coords = (dest_lat - 0.5, dest_lon - 0.5)
        source_lat, source_lon = source_coords
        
        # Calculate initial travel cost (source to destination)
        initial_travel = await get_directions(source_lat, source_lon, dest_lat, dest_lon)
        initial_travel_cost = calculate_transport_cost(
            initial_travel["distance"], 
            initial_travel["transport_mode"]
        )
        
        # Parse interests
        interests = [i.strip() for i in pref.interests.split(',') if i.strip()] or ["sightseeing"]

        # Fetching places with enriched data
        async def get_places_with_fallbacks(category: str, place_type: str = None):
            results = await get_google_places(dest_lat, dest_lon, category, place_type)
            if len(results) < 5:
                osm_results = await get_osm_places(dest_lat, dest_lon, category)
                results.extend(r for r in osm_results if not any(x["name"] == r["name"] for x in results))
            if len(results) < 5 and place_type:
                fsq_results = await get_foursquare_places(dest_lat, dest_lon, category)
                results.extend(r for r in fsq_results if not any(x["name"] == r["name"] for x in results))
            return results

        # Fetch different types of places
        all_attractions = await get_places_with_fallbacks("attraction", "tourist_attraction")
        all_restaurants = await get_places_with_fallbacks("restaurant", "restaurant")
        all_hotels = await get_places_with_fallbacks("hotel", "lodging")
        
        # Initialize tracking variables
        interest_activities = {}
        used_attractions = set()
        used_restaurants = set()
        used_activities = set()
        used_hotels = set()
        
        days_list = []
        total_cost = initial_travel_cost  # Start with initial travel cost
        
        # Calculate hotel cost only once for the entire stay
        # Select a hotel first
        selected_hotel = all_hotels[:1] or [{"name": f"Stay in {pref.destination}", "place_id": "", "location": {"lat": dest_lat, "lng": dest_lon}}]
        used_hotels.update(h["name"] for h in selected_hotel)
        
        # Get hotel details and calculate the total accommodation cost
        hotel_total_cost = 0
        if selected_hotel:
            hotel = selected_hotel[0]
            if hotel["place_id"]:
                details = await get_place_details(hotel["place_id"])
                if details:
                    hotel["details"] = details
                    hotel["price_level"] = details.get("price_level", hotel.get("price_level", 0))
            hotel_total_cost = calculate_place_cost(hotel, "hotel", budget_level) * pref.duration
        
        # Daily accommodation cost
        daily_hotel_cost = hotel_total_cost / pref.duration if pref.duration > 0 else 0
        
        # Build itinerary day by day
        for day in range(1, pref.duration + 1):
            # Get specific interest for this day
            interest = interests[(day - 1) % len(interests)]
            
            # Fetch interest-specific activities if not already fetched
            if interest not in interest_activities:
                interest_activities[interest] = await get_places_with_fallbacks(interest)
            
            # Filter out already used places
            available_attractions = [a for a in all_attractions if a["name"] not in used_attractions]
            available_restaurants = [r for r in all_restaurants if r["name"] not in used_restaurants]
            available_activities = [a for a in interest_activities.get(interest, []) if a["name"] not in used_activities]
            
            # Pick places for this day
            day_attractions = available_attractions[:2] or [{"name": f"Explore {pref.destination}", "place_id": "", "location": {"lat": dest_lat, "lng": dest_lon}}]
            day_restaurants = available_restaurants[:3] or [{"name": f"Local cuisine in {pref.destination}", "place_id": "", "location": {"lat": dest_lat, "lng": dest_lon}}]
            day_activities = available_activities[:2] or [{"name": f"{interest.capitalize()} activity", "place_id": "", "location": {"lat": dest_lat, "lng": dest_lon}}]
            
            # Track used places
            used_attractions.update(a["name"] for a in day_attractions)
            used_restaurants.update(r["name"] for r in day_restaurants)
            used_activities.update(a["name"] for a in day_activities)
            
            # Calculate costs with API data when available
            attraction_costs = []
            restaurant_costs = []
            activity_costs = []
            
            # Calculate attraction costs
            for attraction in day_attractions:
                if attraction["place_id"]:
                    details = await get_place_details(attraction["place_id"])
                    if details:
                        attraction["details"] = details
                        attraction["price_level"] = details.get("price_level", attraction.get("price_level", 0))
                cost = calculate_place_cost(attraction, "attraction", budget_level)
                attraction_costs.append(cost)
            
            # Calculate restaurant costs
            for restaurant in day_restaurants:
                if restaurant["place_id"]:
                    details = await get_place_details(restaurant["place_id"])
                    if details:
                        restaurant["details"] = details
                        restaurant["price_level"] = details.get("price_level", restaurant.get("price_level", 0))
                cost = calculate_place_cost(restaurant, "restaurant", budget_level)
                restaurant_costs.append(cost)
            
            # Calculate activity costs
            for activity in day_activities:
                if activity["place_id"]:
                    details = await get_place_details(activity["place_id"])
                    if details:
                        activity["details"] = details
                        activity["price_level"] = details.get("price_level", activity.get("price_level", 0))
                cost = calculate_place_cost(activity, "activity", budget_level)
                activity_costs.append(cost)
            
            # Calculate local transportation costs for the day
            # Start with hotel location
            current_lat = selected_hotel[0]["location"]["lat"] if selected_hotel else dest_lat
            current_lng = selected_hotel[0]["location"]["lng"] if selected_hotel else dest_lon
            
            daily_transport_distance = 0
            # Add travel to each attraction
            for place in day_attractions + day_activities:
                target_lat = place["location"]["lat"] if place["location"] else dest_lat
                target_lng = place["location"]["lng"] if place["location"] else dest_lon
                
                directions = await get_directions(
                    current_lat, current_lng, 
                    target_lat, target_lng
                )
                
                daily_transport_distance += directions["distance"]
                current_lat, current_lng = target_lat, target_lng
            
            # Return to hotel at the end of the day
            hotel_lat = selected_hotel[0]["location"]["lat"] if selected_hotel else dest_lat
            hotel_lng = selected_hotel[0]["location"]["lng"] if selected_hotel else dest_lon
            
            return_directions = await get_directions(
                current_lat, current_lng, 
                hotel_lat, hotel_lng
            )
            
            daily_transport_distance += return_directions["distance"]
            
            # Calculate local transport cost
            local_transport_cost = calculate_transport_cost(daily_transport_distance, "driving")
            
            # Daily totals
            day_attractions_cost = sum(attraction_costs)
            day_restaurants_cost = sum(restaurant_costs)
            day_activities_cost = sum(activity_costs)
            
            # Total for this day
            day_total = day_attractions_cost + day_restaurants_cost + day_activities_cost + daily_hotel_cost + local_transport_cost
            
            # Build day entry with detailed cost breakdown
            day_entry = ItineraryDay(
                day=f"Day {day}",
                attractions=[a["name"] for a in day_attractions],
                dining=[r["name"] for r in day_restaurants],
                activities=[a["name"] for a in day_activities],
                hotels=[h["name"] for h in selected_hotel],  # Use the same hotel for all days
                estimated_cost=round(day_total, 2),
                cost_breakdown={
                    "attractions": round(day_attractions_cost, 2),
                    "dining": round(day_restaurants_cost, 2),
                    "activities": round(day_activities_cost, 2),
                    "accommodation": round(daily_hotel_cost, 2),  # Hotel cost is evenly distributed
                    "local_transport": round(local_transport_cost, 2)
                },
                travel_cost=round(initial_travel_cost, 2) if day == 1 else 0,  # Only include initial travel cost on day 1
                travel_distance=round(initial_travel["distance"], 2) if day == 1 else 0,
                local_travel_distance=round(daily_transport_distance, 2)
            )
            
            days_list.append(day_entry)
            total_cost += day_total - (daily_hotel_cost if day > 1 else 0)  # Avoid double-counting hotel costs
        
        # Create full itinerary response
        itinerary = ItineraryResponse(
            destination=pref.destination,
            duration=pref.duration,
            days=days_list,
            total_budget=round(total_cost, 2),
            budget_breakdown={
                "accommodation": round(hotel_total_cost, 2),  # Use the total hotel cost here
                "food": round(sum(day.cost_breakdown["dining"] for day in days_list), 2),
                "attractions": round(sum(day.cost_breakdown["attractions"] for day in days_list), 2),
                "activities": round(sum(day.cost_breakdown["activities"] for day in days_list), 2),
                "transportation": round(initial_travel_cost + sum(day.cost_breakdown["local_transport"] for day in days_list), 2)
            }
        )
        
        return itinerary

    except Exception as e:
        logger.error(f"Error generating itinerary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Itinerary generation failed: {str(e)}")