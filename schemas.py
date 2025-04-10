# schemas.py
from typing import List
from pydantic import BaseModel

class ItineraryDay(BaseModel):
    day: str
    attractions: List[str]
    dining: List[str]
    activities: List[str]
    hotels: List[str]
    estimated_cost: float
    cost_breakdown: dict[str, float]  # New field
    travel_cost: float
    travel_distance: float
    local_travel_distance: float  # New field

class ItineraryResponse(BaseModel):
    destination: str
    duration: int
    days: List[ItineraryDay]
    total_budget: float
    budget_breakdown: dict[str, float]  # New field