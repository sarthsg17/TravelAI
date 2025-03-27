import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import pickle

class PricingPredictor:
    def __init__(self):
        self.model = self.build_model()
        self.scaler = pickle.load(open('scaler.pkl', 'rb'))
        
    def build_model(self):
        model = Sequential([
            LSTM(64, return_sequences=True, input_shape=(30, 1)),
            LSTM(64),
            Dense(32, activation='relu'),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model
        
    def predict(self, distance):
        input_data = np.array([[distance / 1000]])  # Convert meters to km
        scaled = self.scaler.transform(input_data)
        return self.model.predict(scaled)[0][0]