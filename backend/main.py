from fastapi import FastAPI, WebSocket, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from typing import List, Dict
import googlemaps
from datetime import datetime
from auth import get_current_user  # ← Direct import from same directory
from services.emergency import get_emergency_alerts
from services.carbon import calculate_emissions
from ai_services.nlp_chatbot import TravelChatbot
from pricing_predictor import PricingPredictor
from recommendation_engine import TravelRecommender
import tensorflow as tf
from tensorflow.keras import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

# Add version check at top:
assert tf.__version__.startswith("2.15."), f"Requires TensorFlow 2.15, found {tf.__version__}"
assert np.__version__ == "1.23.5", f"Requires NumPy 1.23.5, found {np.__version__}"

load_dotenv()

app = FastAPI()
chatbot = TravelChatbot()
pricer = PricingPredictor()
recommender = TravelRecommender()
gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_KEY"))

# Authentication Setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class TripRequest(BaseModel):
    origin: str
    destination: str
    dates: List[str]
    budget: float
    preferences: Dict[str, List[str]]

@app.post("/api/plan-trip")
async def plan_trip(request: TripRequest, token: str = Depends(oauth2_scheme)):
    try:
        # 1. Get Directions
        directions = gmaps.directions(
            request.origin,
            request.destination,
            mode="driving",
            departure_time=datetime.now()
        )

        # 2. Get Recommendations
        recommendations = recommender.recommend({
            "interests": request.preferences.get("activities", []),
            "budget": request.budget
        })

        # 3. Price Prediction
        distance = directions[0]['legs'][0]['distance']['value']  # meters
        best_price = pricer.predict(distance / 1000)  # convert to km

        # 4. Carbon Calculation
        carbon_data = calculate_emissions(distance / 1000, "car")

        return {
            "itinerary": directions,
            "recommendations": recommendations,
            "price_prediction": best_price,
            "carbon_footprint": carbon_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/trip/{trip_id}")
async def websocket_endpoint(websocket: WebSocket, trip_id: str):
    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        # Broadcast to all connected clients
        await websocket.send_json({
            "type": "update",
            "data": f"Modified itinerary for trip {trip_id}"
        })

@app.post("/api/chat")
async def chat_endpoint(query: str):
    return {"response": chatbot.respond(query)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)