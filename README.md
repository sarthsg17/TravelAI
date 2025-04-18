# 🌐 TravelAI - Intelligent Travel Itinerary Planner

## ✨ Features
- **Personalized Itinerary Generation** based on user preferences
- **Budget Estimation** with detailed cost breakdowns
- **Day-by-Day Planning** including:
  - 🏨 Accommodation options
  - 🍽️ Restaurant recommendations
  - 🏛️ Attraction suggestions
  - 🚗 Transportation routes
- **Interactive Web Interface** with responsive design

## 🛠 Tech Stack
**Backend**:
- Python 3.9+
- FastAPI (Web Framework)
- SQLAlchemy (ORM)
- Uvicorn (ASGI Server)

**Frontend**:
- HTML5, CSS3
- Jinja2 Templates
- Vanilla JavaScript

**Database**:
- SQLite (Development)
- PostgreSQL (Production-ready)

## 📥 Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/Diksha333/TravelAI.git
   cd TravelAI
Create and activate virtual environment:

python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
Install dependencies:

pip install -r requirements.txt
⚙️ Configuration
Rename .env.example to .env

Add your API keys:
GOOGLE_API_KEY=your_google_maps_key
FOURSQUARE_API_KEY=your_foursquare_key
For production, update config.py with your database URI

🚀 Usage
Start development server:

uvicorn main:app --reload
Access the web interface at:
http://localhost:8000
🔌 API Integrations
Google Maps API for geolocation and routes

Foursquare API for point-of-interest data
