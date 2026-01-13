"""
Order management data models and database schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from pydantic import BaseModel
import enum

# Enums

class OrderStatus(str, enum.Enum):
    PLACED = "placed"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    COOKING = "cooking"
    READY = "ready"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    WALLET = "wallet"

# Database Models

class Order(Base):
    """Order database model"""
    __tablename__ = "orders"

    id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    restaurant_id = Column(String(50), ForeignKey("restaurants.id"), nullable=False)
    delivery_partner_id = Column(String(50), ForeignKey("delivery_partners.id"))

    # Order details
    order_number = Column(String(20), unique=True, index=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.PLACED)
    status_history = Column(JSON, default=list)  # List of status change events

    # Pricing
    subtotal = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0.0)
    delivery_fee = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)

    # Payment
    payment_method = Column(Enum(PaymentMethod))
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_id = Column(String(100))  # External payment gateway ID

    # Delivery details
    delivery_address = Column(JSON, nullable=False)  # Full address object
    delivery_instructions = Column(Text)
    estimated_delivery_time = Column(DateTime)
    actual_delivery_time = Column(DateTime)

    # Timestamps
    placed_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime)
    preparing_at = Column(DateTime)
    cooking_at = Column(DateTime)
    ready_at = Column(DateTime)
    out_for_delivery_at = Column(DateTime)
    delivered_at = Column(DateTime)
    cancelled_at = Column(DateTime)

    # Additional info
    special_requests = Column(Text)
    coupon_code = Column(String(50))
    is_priority = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="orders")
    restaurant = relationship("Restaurant", back_populates="orders")
    delivery_partner = relationship("DeliveryPartner", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    cooking_session = relationship("CookingSession", back_populates="order", uselist=False)
    ratings = relationship("Rating", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    """Order item database model"""
    __tablename__ = "order_items"

    id = Column(String(50), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.id"), nullable=False)
    food_item_id = Column(String(50), ForeignKey("food_items.id"), nullable=False)

    # Item details
    name = Column(String(255), nullable=False)
    description = Column(Text)
    image_url = Column(String(500))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    # Customizations
    customizations = Column(JSON, default=list)  # List of selected customization choices

    # Preparation details
    special_instructions = Column(Text)
    is_prepared = Column(Boolean, default=False)
    prepared_at = Column(DateTime)

    # Relationships
    order = relationship("Order", back_populates="items")
    food_item = relationship("FoodItem")

class DeliveryPartner(Base):
    """Delivery partner database model"""
    __tablename__ = "delivery_partners"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255))
    vehicle_type = Column(String(50))  # "bike", "car", "scooter"
    vehicle_number = Column(String(20))
    license_number = Column(String(50))
    profile_image_url = Column(String(500))
    rating = Column(Float, default=0.0)
    total_deliveries = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)

    # Location tracking
    current_latitude = Column(Float)
    current_longitude = Column(Float)
    last_location_update = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    orders = relationship("Order", back_populates="delivery_partner")

class CookingSession(Base):
    """Cooking session for live telecast"""
    __tablename__ = "cooking_sessions"

    id = Column(String(50), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.id"), nullable=False, unique=True)
    chef_id = Column(String(50), ForeignKey("chefs.id"), nullable=False)

    # Session details
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="scheduled")  # scheduled, live, completed, cancelled

    # Streaming details
    stream_url = Column(String(500))
    thumbnail_url = Column(String(500))
    is_live = Column(Boolean, default=False)

    # Timing
    scheduled_start_time = Column(DateTime)
    actual_start_time = Column(DateTime)
    end_time = Column(DateTime)
    estimated_duration = Column(Integer, default=30)  # minutes

    # Engagement
    viewer_count = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="cooking_session")
    chef = relationship("Chef", back_populates="cooking_sessions")
    notifications = relationship("TelecastNotification", back_populates="cooking_session", cascade="all, delete-orphan")

class Chef(Base):
    """Chef database model"""
    __tablename__ = "chefs"

    id = Column(String(50), primary_key=True, index=True)
    restaurant_id = Column(String(50), ForeignKey("restaurants.id"), nullable=False)
    user_id = Column(String(50), ForeignKey("users.id"))  # Link to user account if chef has login

    # Chef details
    name = Column(String(255), nullable=False)
    bio = Column(Text)
    profile_image_url = Column(String(500))
    specialties = Column(JSON, default=list)  # ["italian", "pasta", "pizza"]
    experience_years = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    total_sessions = Column(Integer, default=0)

    # Social media
    instagram_handle = Column(String(100))
    youtube_channel = Column(String(100))

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    restaurant = relationship("Restaurant")
    cooking_sessions = relationship("CookingSession", back_populates="chef")

class TelecastNotification(Base):
    """Telecast notification database model"""
    __tablename__ = "telecast_notifications"

    id = Column(String(50), primary_key=True, index=True)
    cooking_session_id = Column(String(50), ForeignKey("cooking_sessions.id"), nullable=False)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)

    # Notification details
    notification_type = Column(String(20), default="telecast_start")  # telecast_start, milestone, etc.
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    cooking_session = relationship("CookingSession", back_populates="notifications")
    user = relationship("User")

# Pydantic Models for API

class OrderItemBase(BaseModel):
    food_item_id: str
    quantity: int
    customizations: List[Dict[str, Any]] = []
    special_instructions: Optional[str] = None

class OrderItem(OrderItemBase):
    id: str
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    unit_price: float
    total_price: float
    is_prepared: bool = False

    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    restaurant_id: str
    items: List[OrderItemBase]
    delivery_address: Dict[str, Any]
    payment_method: PaymentMethod
    delivery_instructions: Optional[str] = None
    special_requests: Optional[str] = None
    coupon_code: Optional[str] = None

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    delivery_partner_id: Optional[str] = None
    estimated_delivery_time: Optional[datetime] = None
    special_requests: Optional[str] = None

class Order(OrderBase):
    id: str
    user_id: str
    order_number: str
    status: OrderStatus
    status_history: List[Dict[str, Any]] = []
    subtotal: float
    tax_amount: float
    delivery_fee: float
    discount_amount: float
    total_amount: float
    payment_status: PaymentStatus
    payment_id: Optional[str] = None
    estimated_delivery_time: Optional[datetime] = None
    actual_delivery_time: Optional[datetime] = None
    placed_at: datetime
    confirmed_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cooking_session: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class OrderSummary(BaseModel):
    id: str
    order_number: str
    restaurant_name: str
    status: OrderStatus
    total_amount: float
    placed_at: datetime
    estimated_delivery_time: Optional[datetime] = None
    items_count: int

class DeliveryPartnerBase(BaseModel):
    name: str
    phone: str
    vehicle_type: Optional[str] = None

class DeliveryPartner(DeliveryPartnerBase):
    id: str
    email: Optional[str] = None
    profile_image_url: Optional[str] = None
    rating: float = 0.0
    total_deliveries: int = 0
    is_available: bool = True
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None

    class Config:
        from_attributes = True

class CookingSessionBase(BaseModel):
    title: str
    description: Optional[str] = None

class CookingSession(CookingSessionBase):
    id: str
    order_id: str
    chef_id: str
    status: str
    stream_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_live: bool = False
    scheduled_start_time: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    estimated_duration: int = 30
    viewer_count: int = 0
    total_views: int = 0

    class Config:
        from_attributes = True

class ChefBase(BaseModel):
    name: str
    bio: Optional[str] = None
    specialties: List[str] = []

class Chef(ChefBase):
    id: str
    restaurant_id: str
    profile_image_url: Optional[str] = None
    experience_years: int = 0
    rating: float = 0.0
    total_sessions: int = 0

    class Config:
        from_attributes = True

class TelecastNotificationBase(BaseModel):
    notification_type: str
    title: str
    message: str

class TelecastNotification(TelecastNotificationBase):
    id: str
    cooking_session_id: str
    user_id: str
    is_read: bool = False
    sent_at: datetime

    class Config:
        from_attributes = True

# Request/Response Models

class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    notes: Optional[str] = None

class OrderTrackingInfo(BaseModel):
    order_id: str
    current_status: OrderStatus
    status_history: List[Dict[str, Any]]
    estimated_delivery_time: Optional[datetime] = None
    delivery_partner: Optional[DeliveryPartner] = None
    cooking_session: Optional[CookingSession] = None

class OrderStats(BaseModel):
    total_orders: int
    pending_orders: int
    completed_orders: int
    cancelled_orders: int
    total_revenue: float
    average_order_value: float

class OrderSearchRequest(BaseModel):
    status: Optional[OrderStatus] = None
    restaurant_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sort_by: str = "placed_at"
    sort_order: str = "desc"
    page: int = 1
    limit: int = 20

# Import Base from database
from app.core.database import Base