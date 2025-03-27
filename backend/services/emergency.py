import requests
import os

RED_CROSS_KEY = os.getenv("RED_CROSS_KEY")

def get_alerts(latitude: float, longitude: float):
    response = requests.get(
        f"https://api.redcross.org/v1/alerts?lat={latitude}&lng={longitude}",
        headers={"Authorization": f"Bearer {RED_CROSS_KEY}"}
    )
    return response.json().get('alerts', [])