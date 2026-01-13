"""
User data models and database schemas
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr
from app.core.database import Base

# Database Models

class User(Base):
    """User database model"""
    __tablename__ = "users"

    id = Column(String(50), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(String(20), default="customer")  # customer, restaurant_owner, delivery_partner, admin
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Profile information
    avatar_url = Column(String(500))
    date_of_birth = Column(DateTime)
    gender = Column(String(10))

    # Preferences
    dietary_restrictions = Column(JSON, default=list)  # ["vegetarian", "vegan", "gluten_free", etc.]
    favorite_cuisines = Column(JSON, default=list)  # ["italian", "chinese", "indian", etc.]
    spice_level = Column(String(20), default="medium")  # mild, medium, hot, very_hot

    # Relationships
    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="user", cascade="all, delete-orphan")

class Address(Base):
    """User address database model"""
    __tablename__ = "addresses"

    id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    label = Column(String(50), nullable=False)  # "Home", "Work", "Other"
    street_address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), default="India")
    latitude = Column(Float)
    longitude = Column(Float)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="addresses")

# Pydantic Models for API

class AddressBase(BaseModel):
    label: str
    street_address: str
    city: str
    state: str
    postal_code: str
    country: str = "India"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: bool = False

class AddressCreate(AddressBase):
    pass

class AddressUpdate(AddressBase):
    pass

class Address(AddressBase):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr
    phone: str
    full_name: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    dietary_restrictions: Optional[List[str]] = None
    favorite_cuisines: Optional[List[str]] = None
    spice_level: Optional[str] = None

class User(UserBase):
    id: str
    is_active: bool
    is_verified: bool
    role: str
    created_at: datetime
    updated_at: datetime
    avatar_url: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    dietary_restrictions: List[str] = []
    favorite_cuisines: List[str] = []
    spice_level: str = "medium"
    addresses: List[Address] = []

    class Config:
        from_attributes = True

class UserProfile(BaseModel):
    """User profile response"""
    id: str
    email: EmailStr
    phone: str
    full_name: str
    avatar_url: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    dietary_restrictions: List[str] = []
    favorite_cuisines: List[str] = []
    spice_level: str = "medium"
    addresses: List[Address] = []
    total_orders: int = 0
    favorite_restaurants: List[dict] = []

# Authentication Models

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    phone: str
    full_name: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str