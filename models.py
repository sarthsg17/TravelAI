from sqlalchemy import Column, Integer, String, Boolean, Date
from database import Base

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    interests = Column(String, nullable=False)
    travel_date = Column(String, nullable=True)
