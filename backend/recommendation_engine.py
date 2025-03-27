import numpy as np
from sklearn.neighbors import NearestNeighbors
from typing import List, Dict
import pickle

class TravelRecommender:
    def __init__(self):
        self.locations = self._load_sample_data()
        self.model = self._train_model()

    def _load_sample_data(self):
        return [
            {"name": "Rohtang Pass", "type": "adventure", "cost": 1000, "duration": 6},
            {"name": "Hidimba Temple", "type": "cultural", "cost": 200, "duration": 2},
            {"name": "Solang Valley", "type": "adventure", "cost": 1500, "duration": 4}
        ]

    def _train_model(self):
        features = []
        for loc in self.locations:
            vec = [
                1 if loc["type"] == "adventure" else 0,
                1 if loc["type"] == "cultural" else 0,
                loc["cost"] / 2000,
                loc["duration"] / 8
            ]
            features.append(vec)
        
        model = NearestNeighbors(n_neighbors=2, algorithm='ball_tree')
        model.fit(features)
        return model

    def recommend(self, user_prefs: Dict) -> List[Dict]:
        query = [
            1 if "adventure" in user_prefs.get("interests", []) else 0,
            1 if "cultural" in user_prefs.get("interests", []) else 0,
            user_prefs.get("budget", 5000) / 2000,
            user_prefs.get("max_duration", 8) / 8
        ]
        distances, indices = self.model.kneighbors([query])
        return [self.locations[i] for i in indices[0]]