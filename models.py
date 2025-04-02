from sqlalchemy import Column, Integer, String
from config import Base

class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    budget = Column(Integer, nullable=False) 
    interests = Column(String, nullable=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "destination": self.destination,
            "duration": self.duration,
            "budget": self.budget,
            "interests": self.interests
        }