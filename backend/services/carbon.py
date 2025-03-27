import requests

CLOVERLY_KEY = os.getenv("CLOVERLY_KEY")

def calculate_emissions(distance_km: float, transport_mode: str):
    response = requests.post(
        "https://api.cloverly.com/estimates",
        json={
            "distance": {"value": distance_km, "units": "km"},
            "transport": transport_mode
        },
        headers={"Authorization": f"Bearer {CLOVERLY_KEY}"}
    )
    return response.json()