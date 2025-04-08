# schemas.py
from typing import List
from pydantic import BaseModel

class ItineraryDay(BaseModel):
    day: str                   # e.g., "Day 1"
    attractions: List[str]     # e.g., ["Eiffel Tower", "Louvre"]
    dining: List[str]         # e.g., ["Le Jules Verne"]
    activities: List[str]      # e.g., ["Boat Tour"]
    hotels: List[str]         # e.g., ["Hotel Ritz Paris"]

class ItineraryResponse(BaseModel):
    destination: str          # e.g., "Paris, France"
    duration: int             # e.g., 5 (days)
    days: List[ItineraryDay]   # List of daily itineraries