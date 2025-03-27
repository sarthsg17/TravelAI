import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import pickle
import yfinance as yf
from datetime import datetime, timedelta
import os

# Version compatibility check
if not tf.__version__.startswith('2.'):
    raise RuntimeError(f"TensorFlow 2.x required (found {tf.__version__})")

class TravelPricePredictor:
    def __init__(self):
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model = self._build_model()
        
        # Create models directory if not exists
        os.makedirs('models', exist_ok=True)

    def _build_model(self):
        """Build LSTM model with updated TensorFlow syntax"""
        model = Sequential([
            tf.keras.layers.LSTM(
                128, 
                return_sequences=True, 
                input_shape=(30, 5)
            ),
            Dropout(0.2),
            tf.keras.layers.LSTM(64),
            Dropout(0.2),
            Dense(32, activation='relu'),
            Dense(1)
        ])
        model.compile(
            optimizer=tf.keras.optimizers.Adam(),
            loss='mean_squared_error',
            metrics=['mae']
        )
        return model

    def _fetch_training_data(self):
        """Fetch real-world data for training using yfinance"""
        airlines = ['DAL', 'AAL', 'UAL']  # Delta, American, United airlines
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*3)  # 3 years of data
        
        try:
            import yfinance as yf
            data = yf.download(
                airlines, 
                start=start_date, 
                end=end_date,
                progress=False
            )['Adj Close']
            return data.interpolate().ffill().bfill()
        except ImportError:
            print("yfinance not available, using synthetic data")
            return self._generate_synthetic_data()
            # Fallback to synthetic data
            dates = pd.date_range(start_date, end_date)
            return pd.DataFrame(
                np.random.uniform(20, 200, (len(dates), len(airlines))),
                index=dates,
                columns=airlines
            )

    def _prepare_data(self, data, lookback=30):
        """Create time-series sequences with proper reshaping"""
        scaled_data = self.scaler.fit_transform(data)
        
        X, y = [], []
        for i in range(lookback, len(scaled_data)):
            X.append(scaled_data[i-lookback:i])
            y.append(scaled_data[i, 0])  # Predict first airline's price
        
        return np.array(X), np.array(y)

    def train(self, epochs=100, batch_size=32):
        """Train model with enhanced error handling"""
        try:
            raw_data = self._fetch_training_data()
            X, y = self._prepare_data(raw_data)
            
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, 
                test_size=0.2, 
                shuffle=False
            )
            
            print(f"Training on {len(X_train)} samples...")
            
            history = self.model.fit(
                X_train, y_train,
                validation_data=(X_test, y_test),
                epochs=epochs,
                batch_size=batch_size,
                verbose=1,
                callbacks=[
                    tf.keras.callbacks.EarlyStopping(patience=10),
                    tf.keras.callbacks.ModelCheckpoint(
                        'models/best_model.h5',
                        save_best_only=True
                    )
                ]
            )
            
            # Save final model and artifacts
            self.model.save('models/travel_price_predictor.h5')
            with open('models/scaler.pkl', 'wb') as f:
                pickle.dump(self.scaler, f)
                
            return history
        
        except Exception as e:
            print(f"Training failed: {e}")
            return None

    def evaluate(self, test_data=None):
        """Evaluate model with optional test data"""
        if test_data is None:
            test_data = self._fetch_training_data()
            _, X_test, _, y_test = train_test_split(
                *self._prepare_data(test_data),
                test_size=0.2,
                shuffle=False
            )
        return self.model.evaluate(X_test, y_test, verbose=0)
    def _generate_synthetic_data(self):
        dates = pd.date_range(end=datetime.now(), periods=365*3)
        return pd.DataFrame(
            np.random.uniform(20, 200, (len(dates), 3)),
            columns=['DAL', 'AAL', 'UAL'],
            index=dates
    )

if __name__ == "__main__":
    print("Initializing Travel Price Predictor...")
    predictor = TravelPricePredictor()
    
    print("Starting training process...")
    history = predictor.train(epochs=150)
    
    if history:
        print("\nTraining completed successfully!")
        print("Saving training metrics...")
        pd.DataFrame(history.history).to_csv(
            'models/training_metrics.csv', 
            index=False
        )
        
        # Evaluate final model
        loss, mae = predictor.evaluate()
        print(f"\nModel Evaluation:")
        print(f"Mean Absolute Error: ${mae:.2f}")
        print(f"Loss: {loss:.4f}")
        
        print("\nArtifacts saved in 'models/' directory:")
        print("- travel_price_predictor.h5 (model weights)")
        print("- best_model.h5 (best validation model)")
        print("- scaler.pkl (data scaler)")
        print("- training_metrics.csv (history)")
    else:
        print("Training failed. Please check error messages.")