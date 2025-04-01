from sqlalchemy import Column, Integer, String, Float
from database import Base

class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    destination = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    budget = Column(Float, nullable=False)
    interests = Column(String, nullable=False)
