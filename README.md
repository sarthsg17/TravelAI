# ✈️ TravelAI - Intelligent Travel Planning Platform

**TravelAI revolutionizes trip planning by combining artificial intelligence with real-time travel data to create perfectly tailored itineraries.** Our system analyzes your preferences, budget, and travel dates to generate comprehensive day-by-day plans complete with attractions, dining options, and logistical routing.

![TravelAI Interface Demo](static/demo.gif)

## 🌟 Why TravelAI?

Planning the perfect trip is complex and time-consuming. TravelAI solves this by:

- **Saving hours of research** by automatically generating optimized itineraries
- **Eliminating decision fatigue** with smart, personalized recommendations
- **Preventing budget surprises** with accurate cost estimations
- **Discovering hidden gems** through our advanced location algorithms

## 🚀 Key Features

| Feature | Description |
|---------|-------------|
| **Smart Itinerary Generation** | Our AI engine crafts personalized plans based on your interests (adventure, relaxation, culture etc.), group size, and travel style |
| **Dynamic Budgeting** | Get real-time cost estimates with breakdowns for accommodations, dining, activities, and transportation |
| **Seamless Logistics** | Automatically optimized routes with travel times between locations and smart scheduling |
| **Local Insights** | Curated recommendations from locals and travel experts through our Foursquare integration |
| **Multi-Device Access** | Your itineraries sync across devices and are available offline |

## 🛠️ Technology Stack

**Backend Intelligence**:
- **Python 3.9+**: Core application logic and data processing
- **FastAPI**: High-performance web framework for building APIs
- **SQLAlchemy 2.0**: Modern ORM for database interactions
- **Uvicorn**: Lightning-fast ASGI server implementation

**Frontend Experience**:
- **Jinja2 Templates**: Dynamic HTML rendering with clean separation of concerns
- **Tailwind CSS**: Utility-first CSS framework for responsive designs
- **Vanilla JavaScript**: Lightweight interactivity without framework overhead

**Data Ecosystem**:
- **Google Maps API**: Precise geolocation services and route optimization
- **Foursquare Places API**: Comprehensive database of points-of-interest
- **PostgreSQL**: Robust relational database for production environments

## ⚡ Getting Started

### Prerequisites
- Python 3.9 or higher
- Google Maps API key
- Foursquare API credentials

### Installation Guide

```bash
# Clone the repository
git clone https://github.com/Diksha333/TravelAI.git
cd TravelAI

# Create virtual environment
python -m venv .venv

# Activate environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env file with your API keys

# Initialize database
python create_tables.py

# Launch application
uvicorn main:app --reload
