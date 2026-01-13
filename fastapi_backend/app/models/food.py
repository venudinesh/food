"""
Food catalog data models and database schemas
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from app.core.database import Base

# Database Models

class Restaurant(Base):
    """Restaurant database model"""
    __tablename__ = "restaurants"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    image_url = Column(String(500))
    cover_image_url = Column(String(500))
    phone = Column(String(20))
    email = Column(String(255))
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20))
    latitude = Column(Float)
    longitude = Column(Float)
    cuisine_types = Column(JSON, default=list)  # ["italian", "chinese", "indian"]
    price_range = Column(String(10), default="$$")  # $, $$, $$$, $$$$
    rating = Column(Float, default=0.0)
    total_ratings = Column(Integer, default=0)
    delivery_time_min = Column(Integer, default=30)
    delivery_time_max = Column(Integer, default=60)
    delivery_fee = Column(Float, default=0.0)
    minimum_order = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    is_open = Column(Boolean, default=True)
    opening_hours = Column(JSON)  # Complex hours structure
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    food_items = relationship("FoodItem", back_populates="restaurant", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="restaurant")

class Category(Base):
    """Food category database model"""
    __tablename__ = "categories"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    image_url = Column(String(500))
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    food_items = relationship("FoodItem", back_populates="category")

class Ingredient(Base):
    """Ingredient database model"""
    __tablename__ = "ingredients"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    image_url = Column(String(500))
    category = Column(String(50))  # "vegetable", "protein", "dairy", etc.
    is_vegetarian = Column(Boolean, default=True)
    is_vegan = Column(Boolean, default=True)
    is_gluten_free = Column(Boolean, default=True)
    allergens = Column(JSON, default=list)  # ["nuts", "dairy", "gluten", etc.]
    nutritional_info = Column(JSON)  # calories, protein, carbs, fat per 100g
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CookingMethod(Base):
    """Cooking method database model"""
    __tablename__ = "cooking_methods"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    image_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CustomizationOption(Base):
    """Customization option database model"""
    __tablename__ = "customization_options"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    option_type = Column(String(20), nullable=False)  # "single", "multiple", "quantity"
    is_required = Column(Boolean, default=False)
    max_selections = Column(Integer, default=1)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    choices = relationship("CustomizationChoice", back_populates="option", cascade="all, delete-orphan")

class CustomizationChoice(Base):
    """Customization choice database model"""
    __tablename__ = "customization_choices"

    id = Column(String(50), primary_key=True, index=True)
    option_id = Column(String(50), ForeignKey("customization_options.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price_modifier = Column(Float, default=0.0)
    is_default = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    option = relationship("CustomizationOption", back_populates="choices")

class FoodItem(Base):
    """Food item database model"""
    __tablename__ = "food_items"

    id = Column(String(50), primary_key=True, index=True)
    restaurant_id = Column(String(50), ForeignKey("restaurants.id"), nullable=False)
    category_id = Column(String(50), ForeignKey("categories.id"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    image_url = Column(String(500))
    price = Column(Float, nullable=False)
    original_price = Column(Float)  # For discounts
    is_available = Column(Boolean, default=True)
    is_vegetarian = Column(Boolean, default=True)
    is_vegan = Column(Boolean, default=True)
    is_gluten_free = Column(Boolean, default=True)
    spice_level = Column(String(20), default="medium")  # mild, medium, hot, very_hot
    preparation_time = Column(Integer, default=15)  # minutes
    calories = Column(Integer)
    rating = Column(Float, default=0.0)
    total_ratings = Column(Integer, default=0)
    popularity_score = Column(Float, default=0.0)
    tags = Column(JSON, default=list)  # ["popular", "chef_special", "healthy", etc.]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="food_items")
    category = relationship("Category", back_populates="food_items")
    customizations = relationship("FoodItemCustomization", back_populates="food_item", cascade="all, delete-orphan")
    ingredients = relationship("FoodItemIngredient", back_populates="food_item", cascade="all, delete-orphan")
    cooking_methods = relationship("FoodItemCookingMethod", back_populates="food_item", cascade="all, delete-orphan")

class FoodItemCustomization(Base):
    """Food item customization mapping"""
    __tablename__ = "food_item_customizations"

    id = Column(String(50), primary_key=True, index=True)
    food_item_id = Column(String(50), ForeignKey("food_items.id"), nullable=False)
    customization_id = Column(String(50), ForeignKey("customization_options.id"), nullable=False)
    display_order = Column(Integer, default=0)

    # Relationships
    food_item = relationship("FoodItem", back_populates="customizations")
    customization = relationship("CustomizationOption")

class FoodItemIngredient(Base):
    """Food item ingredient mapping"""
    __tablename__ = "food_item_ingredients"

    id = Column(String(50), primary_key=True, index=True)
    food_item_id = Column(String(50), ForeignKey("food_items.id"), nullable=False)
    ingredient_id = Column(String(50), ForeignKey("ingredients.id"), nullable=False)
    quantity = Column(String(50))  # "100g", "2 pieces", etc.
    is_removable = Column(Boolean, default=False)

    # Relationships
    food_item = relationship("FoodItem", back_populates="ingredients")
    ingredient = relationship("Ingredient")

class FoodItemCookingMethod(Base):
    """Food item cooking method mapping"""
    __tablename__ = "food_item_cooking_methods"

    id = Column(String(50), primary_key=True, index=True)
    food_item_id = Column(String(50), ForeignKey("food_items.id"), nullable=False)
    cooking_method_id = Column(String(50), ForeignKey("cooking_methods.id"), nullable=False)

    # Relationships
    food_item = relationship("FoodItem", back_populates="cooking_methods")
    cooking_method = relationship("CookingMethod")

# Pydantic Models for API

class CustomizationChoiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    price_modifier: float = 0.0
    is_default: bool = False

class CustomizationChoice(CustomizationChoiceBase):
    id: str
    option_id: str

    class Config:
        from_attributes = True

class CustomizationOptionBase(BaseModel):
    name: str
    description: Optional[str] = None
    option_type: str
    is_required: bool = False
    max_selections: int = 1

class CustomizationOption(CustomizationOptionBase):
    id: str
    choices: List[CustomizationChoice] = []

    class Config:
        from_attributes = True

class IngredientBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    is_vegetarian: bool = True
    is_vegan: bool = True
    is_gluten_free: bool = True
    allergens: List[str] = []

class Ingredient(IngredientBase):
    id: str
    image_url: Optional[str] = None
    nutritional_info: Optional[dict] = None

    class Config:
        from_attributes = True

class CookingMethodBase(BaseModel):
    name: str
    description: Optional[str] = None

class CookingMethod(CookingMethodBase):
    id: str
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

class RestaurantBase(BaseModel):
    name: str
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: str
    city: str
    state: str
    cuisine_types: List[str] = []

class Restaurant(RestaurantBase):
    id: str
    image_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price_range: str = "$$"
    rating: float = 0.0
    total_ratings: int = 0
    delivery_time_min: int = 30
    delivery_time_max: int = 60
    delivery_fee: float = 0.0
    minimum_order: float = 0.0
    is_active: bool = True
    is_open: bool = True

    class Config:
        from_attributes = True

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class Category(CategoryBase):
    id: str
    image_url: Optional[str] = None
    display_order: int = 0

    class Config:
        from_attributes = True

class FoodItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    is_available: bool = True

class FoodItemSummary(FoodItemBase):
    id: str
    restaurant_id: str
    image_url: Optional[str] = None
    rating: float = 0.0
    total_ratings: int = 0
    preparation_time: int = 15
    tags: List[str] = []

    class Config:
        from_attributes = True

class FoodItemDetail(FoodItemSummary):
    restaurant: Restaurant
    category: Optional[Category] = None
    customizations: List[CustomizationOption] = []
    ingredients: List[dict] = []  # With quantity info
    cooking_methods: List[CookingMethod] = []
    is_vegetarian: bool = True
    is_vegan: bool = True
    is_gluten_free: bool = True
    spice_level: str = "medium"
    calories: Optional[int] = None
    original_price: Optional[float] = None

    class Config:
        from_attributes = True

# Search and Filter Models

class FoodSearchRequest(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    restaurant_id: Optional[str] = None
    cuisine_type: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    is_vegetarian: Optional[bool] = None
    is_vegan: Optional[bool] = None
    spice_level: Optional[str] = None
    sort_by: str = "popularity"  # popularity, rating, price, distance
    sort_order: str = "desc"  # asc, desc
    page: int = 1
    limit: int = 20

class RestaurantSearchRequest(BaseModel):
    query: Optional[str] = None
    cuisine_type: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[float] = None  # in kilometers
    price_range: Optional[str] = None
    min_rating: Optional[float] = None
    sort_by: str = "distance"  # distance, rating, delivery_time
    sort_order: str = "asc"
    page: int = 1
    limit: int = 20

# Response Models

class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    pages: int
    limit: int

class FoodCatalogResponse(BaseModel):
    categories: List[Category]
    popular_items: List[FoodItemSummary]
    featured_restaurants: List[Restaurant]