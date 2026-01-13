"""
Ratings and feedback data models and database schemas
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel

# Database Models

class Rating(Base):
    """Rating database model"""
    __tablename__ = "ratings"

    id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    order_id = Column(String(50), ForeignKey("orders.id"), nullable=False)
    restaurant_id = Column(String(50), ForeignKey("restaurants.id"), nullable=False)
    food_item_id = Column(String(50), ForeignKey("food_items.id"))

    # Rating details
    overall_rating = Column(Float, nullable=False)  # 1-5 stars
    food_quality_rating = Column(Float)  # 1-5 stars
    delivery_rating = Column(Float)  # 1-5 stars
    value_rating = Column(Float)  # 1-5 stars

    # Feedback
    review_title = Column(String(255))
    review_text = Column(Text)
    pros = Column(JSON, default=list)  # List of positive aspects
    cons = Column(JSON, default=list)  # List of negative aspects
    tags = Column(JSON, default=list)  # ["fast_delivery", "tasty_food", "good_packaging", etc.]

    # Additional info
    is_verified_purchase = Column(Boolean, default=True)
    is_recommended = Column(Boolean, default=True)
    would_order_again = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="ratings")
    order = relationship("Order", back_populates="ratings")
    restaurant = relationship("Restaurant")
    food_item = relationship("FoodItem")
    responses = relationship("RatingResponse", back_populates="rating", cascade="all, delete-orphan")
    images = relationship("RatingImage", back_populates="rating", cascade="all, delete-orphan")

class RatingResponse(Base):
    """Rating response from restaurant/chef"""
    __tablename__ = "rating_responses"

    id = Column(String(50), primary_key=True, index=True)
    rating_id = Column(String(50), ForeignKey("ratings.id"), nullable=False)
    responder_id = Column(String(50), nullable=False)  # User ID of restaurant owner/chef
    responder_type = Column(String(20), default="restaurant")  # "restaurant", "chef", "admin"

    response_text = Column(Text, nullable=False)
    is_helpful = Column(Boolean, default=False)
    helpful_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rating = relationship("Rating", back_populates="responses")

class RatingImage(Base):
    """Rating image database model"""
    __tablename__ = "rating_images"

    id = Column(String(50), primary_key=True, index=True)
    rating_id = Column(String(50), ForeignKey("ratings.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    image_type = Column(String(20), default="food")  # "food", "packaging", "other"
    caption = Column(String(255))
    display_order = Column(Integer, default=0)

    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rating = relationship("Rating", back_populates="images")

# Pydantic Models for API

class RatingImageBase(BaseModel):
    image_url: str
    image_type: str = "food"
    caption: Optional[str] = None

class RatingImage(RatingImageBase):
    id: str
    rating_id: str
    display_order: int = 0
    uploaded_at: datetime

    class Config:
        from_attributes = True

class RatingResponseBase(BaseModel):
    response_text: str

class RatingResponse(RatingResponseBase):
    id: str
    rating_id: str
    responder_id: str
    responder_type: str = "restaurant"
    is_helpful: bool = False
    helpful_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

class RatingBase(BaseModel):
    order_id: str
    restaurant_id: str
    overall_rating: float
    food_quality_rating: Optional[float] = None
    delivery_rating: Optional[float] = None
    value_rating: Optional[float] = None
    review_title: Optional[str] = None
    review_text: Optional[str] = None
    pros: List[str] = []
    cons: List[str] = []
    tags: List[str] = []
    is_recommended: bool = True
    would_order_again: bool = True

class RatingCreate(RatingBase):
    food_item_id: Optional[str] = None
    images: List[RatingImageBase] = []

class RatingUpdate(BaseModel):
    overall_rating: Optional[float] = None
    food_quality_rating: Optional[float] = None
    delivery_rating: Optional[float] = None
    value_rating: Optional[float] = None
    review_title: Optional[str] = None
    review_text: Optional[str] = None
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_recommended: Optional[bool] = None
    would_order_again: Optional[bool] = None

class Rating(RatingBase):
    id: str
    user_id: str
    food_item_id: Optional[str] = None
    is_verified_purchase: bool = True
    created_at: datetime
    updated_at: datetime
    responses: List[RatingResponse] = []
    images: List[RatingImage] = []

    class Config:
        from_attributes = True

class RatingSummary(BaseModel):
    id: str
    user_id: str
    order_id: str
    restaurant_id: str
    overall_rating: float
    review_title: Optional[str] = None
    review_text: Optional[str] = None
    tags: List[str] = []
    is_verified_purchase: bool = True
    created_at: datetime
    images: List[RatingImage] = []
    responses: List[RatingResponse] = []

# Statistics and Analytics Models

class RatingStats(BaseModel):
    total_ratings: int
    average_rating: float
    rating_distribution: dict  # {1: count, 2: count, 3: count, 4: count, 5: count}
    food_quality_avg: Optional[float] = None
    delivery_avg: Optional[float] = None
    value_avg: Optional[float] = None
    recommended_percentage: float
    would_order_again_percentage: float
    common_tags: List[dict]  # [{"tag": "tasty", "count": 10}, ...]
    recent_ratings: List[RatingSummary]

class RestaurantRatingStats(RatingStats):
    restaurant_id: str
    restaurant_name: str

class FoodItemRatingStats(RatingStats):
    food_item_id: str
    food_item_name: str

# Request/Response Models

class RatingSearchRequest(BaseModel):
    restaurant_id: Optional[str] = None
    food_item_id: Optional[str] = None
    user_id: Optional[str] = None
    min_rating: Optional[float] = None
    max_rating: Optional[float] = None
    has_review: Optional[bool] = None
    tags: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    page: int = 1
    limit: int = 20

class RatingResponseRequest(BaseModel):
    response_text: str

class MarkHelpfulRequest(BaseModel):
    is_helpful: bool

# Bulk Operations

class BulkRatingUpdate(BaseModel):
    rating_ids: List[str]
    updates: RatingUpdate

# Analytics Models

class RatingAnalytics(BaseModel):
    period: str  # "daily", "weekly", "monthly"
    start_date: datetime
    end_date: datetime
    total_ratings: int
    average_rating_trend: List[dict]  # [{"date": "2024-01-01", "average": 4.2}, ...]
    rating_distribution_trend: List[dict]
    common_issues: List[dict]  # [{"issue": "late_delivery", "count": 15}, ...]
    improvement_suggestions: List[str]

# Import Base from database
from app.core.database import Base