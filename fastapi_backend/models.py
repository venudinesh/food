"""
Smart Food Customization and Ordering System - Database Schema
================================================================

Comprehensive database schema for the food ordering system including:
- Users and Preferences
- Food Items and Ingredients
- Orders and Ratings
- Live Cooking Sessions

Author: B.Tech Project Implementation
Date: December 2025
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

# =============================================================================
# USER MANAGEMENT TABLES
# =============================================================================

class User(db.Model):
    """User account and profile information"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))  # 'male', 'female', 'other'
    profile_image_url = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    preferences = db.relationship('UserPreference', backref='user', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='user', lazy=True)
    ratings = db.relationship('Rating', backref='user', lazy=True)
    cooking_session_participants = db.relationship('CookingSessionParticipant', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'address': self.address,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'gender': self.gender,
            'profile_image_url': self.profile_image_url,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class UserPreference(db.Model):
    """User food preferences for personalized recommendations"""
    __tablename__ = 'user_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Preference categories
    favorite_cuisines = db.Column(db.Text)  # JSON array of cuisine types
    favorite_categories = db.Column(db.Text)  # JSON array of food categories
    dietary_restrictions = db.Column(db.Text)  # JSON array: ['vegetarian', 'vegan', 'gluten_free', etc.]
    allergies = db.Column(db.Text)  # JSON array of allergens
    spice_level = db.Column(db.String(20))  # 'mild', 'medium', 'hot', 'very_hot'
    price_range = db.Column(db.String(20))  # 'budget', 'moderate', 'premium'

    # Behavioral preferences
    preferred_meal_times = db.Column(db.Text)  # JSON array: ['breakfast', 'lunch', 'dinner', 'snacks']
    order_frequency = db.Column(db.String(20))  # 'daily', 'weekly', 'monthly', 'occasional'

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'favorite_cuisines': json.loads(self.favorite_cuisines) if self.favorite_cuisines else [],
            'favorite_categories': json.loads(self.favorite_categories) if self.favorite_categories else [],
            'dietary_restrictions': json.loads(self.dietary_restrictions) if self.dietary_restrictions else [],
            'allergies': json.loads(self.allergies) if self.allergies else [],
            'spice_level': self.spice_level,
            'price_range': self.price_range,
            'preferred_meal_times': json.loads(self.preferred_meal_times) if self.preferred_meal_times else [],
            'order_frequency': self.order_frequency
        }

# =============================================================================
# FOOD AND INGREDIENTS TABLES
# =============================================================================

class Ingredient(db.Model):
    """Ingredients used in food items"""
    __tablename__ = 'ingredients'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    category = db.Column(db.String(50))  # 'vegetable', 'protein', 'dairy', 'grain', 'spice', 'other'
    is_vegetarian = db.Column(db.Boolean, default=True)
    is_vegan = db.Column(db.Boolean, default=True)
    is_gluten_free = db.Column(db.Boolean, default=True)
    calories_per_100g = db.Column(db.Float)
    protein_per_100g = db.Column(db.Float)
    carbs_per_100g = db.Column(db.Float)
    fat_per_100g = db.Column(db.Float)
    allergens = db.Column(db.Text)  # JSON array of allergens
    image_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    food_ingredients = db.relationship('FoodIngredient', backref='ingredient', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'is_vegetarian': self.is_vegetarian,
            'is_vegan': self.is_vegan,
            'is_gluten_free': self.is_gluten_free,
            'calories_per_100g': self.calories_per_100g,
            'protein_per_100g': self.protein_per_100g,
            'carbs_per_100g': self.carbs_per_100g,
            'fat_per_100g': self.fat_per_100g,
            'allergens': json.loads(self.allergens) if self.allergens else [],
            'image_url': self.image_url
        }

class FoodItem(db.Model):
    """Food items in the catalog"""
    __tablename__ = 'food_items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200))
    category = db.Column(db.String(50))  # 'pizza', 'burger', 'pasta', 'salad', 'dessert', etc.
    cuisine = db.Column(db.String(50))  # 'italian', 'american', 'indian', 'chinese', etc.
    is_available = db.Column(db.Boolean, default=True)
    is_vegetarian = db.Column(db.Boolean, default=False)
    is_vegan = db.Column(db.Boolean, default=False)
    is_gluten_free = db.Column(db.Boolean, default=False)
    spice_level = db.Column(db.String(20))  # 'mild', 'medium', 'hot', 'very_hot'
    preparation_time = db.Column(db.Integer)  # in minutes
    calories = db.Column(db.Integer)
    protein = db.Column(db.Float)
    carbs = db.Column(db.Float)
    fat = db.Column(db.Float)
    allergens = db.Column(db.Text)  # JSON array of allergens
    tags = db.Column(db.Text)  # JSON array of tags for search
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ingredients = db.relationship('FoodIngredient', backref='food_item', lazy=True, cascade='all, delete-orphan')
    customizations = db.relationship('CustomizationOption', backref='food_item', lazy=True, cascade='all, delete-orphan')
    # order_items = db.relationship('OrderItem', backref='food_item', lazy=True)  # Removed - OrderItem references MenuItem
    ratings = db.relationship('Rating', backref='food_item', lazy=True)
    cooking_sessions = db.relationship('CookingSession', backref='food_item', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'image_url': self.image_url,
            'category': self.category,
            'cuisine': self.cuisine,
            'is_available': self.is_available,
            'is_vegetarian': self.is_vegetarian,
            'is_vegan': self.is_vegan,
            'is_gluten_free': self.is_gluten_free,
            'spice_level': self.spice_level,
            'preparation_time': self.preparation_time,
            'calories': self.calories,
            'protein': self.protein,
            'carbs': self.carbs,
            'fat': self.fat,
            'allergens': json.loads(self.allergens) if self.allergens else [],
            'tags': json.loads(self.tags) if self.tags else []
        }

class FoodIngredient(db.Model):
    """Junction table for food items and their ingredients"""
    __tablename__ = 'food_ingredients'

    id = db.Column(db.Integer, primary_key=True)
    food_item_id = db.Column(db.Integer, db.ForeignKey('food_items.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    quantity = db.Column(db.Float)  # in grams
    is_optional = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Ensure unique combination
    __table_args__ = (db.UniqueConstraint('food_item_id', 'ingredient_id', name='unique_food_ingredient'),)

    def to_dict(self):
        return {
            'id': self.id,
            'food_item_id': self.food_item_id,
            'ingredient_id': self.ingredient_id,
            'quantity': self.quantity,
            'is_optional': self.is_optional
        }

class CustomizationOption(db.Model):
    """Customization options for food items"""
    __tablename__ = 'customization_options'

    id = db.Column(db.Integer, primary_key=True)
    food_item_id = db.Column(db.Integer, db.ForeignKey('food_items.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # e.g., 'Size', 'Toppings', 'Sauce'
    type = db.Column(db.String(20), nullable=False)  # 'single', 'multiple', 'quantity'
    required = db.Column(db.Boolean, default=False)
    options = db.Column(db.Text, nullable=False)  # JSON string of options with prices
    max_selections = db.Column(db.Integer, default=1)  # For multiple selection type
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'food_item_id': self.food_item_id,
            'name': self.name,
            'type': self.type,
            'required': self.required,
            'options': json.loads(self.options) if self.options else [],
            'max_selections': self.max_selections
        }

# Order models consolidated below (enhanced Order/OrderItem definitions are used later in this file).
# Removed duplicate simpler Order/OrderItem definitions to avoid table re-definition.
# =============================================================================
# RATINGS AND REVIEWS TABLES
# =============================================================================

class Rating(db.Model):
    """User ratings and reviews for orders and food items"""
    __tablename__ = 'ratings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    food_item_id = db.Column(db.Integer, db.ForeignKey('food_items.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    delivery_rating = db.Column(db.Integer)  # 1-5 stars for delivery service
    food_quality_rating = db.Column(db.Integer)  # 1-5 stars for food quality
    value_rating = db.Column(db.Integer)  # 1-5 stars for value for money
    would_recommend = db.Column(db.Boolean)
    is_verified_purchase = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Ensure one rating per user per order per food item
    __table_args__ = (db.UniqueConstraint('user_id', 'order_id', 'food_item_id', name='unique_user_order_food_rating'),)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'order_id': self.order_id,
            'food_item_id': self.food_item_id,
            'rating': self.rating,
            'comment': self.comment,
            'delivery_rating': self.delivery_rating,
            'food_quality_rating': self.food_quality_rating,
            'value_rating': self.value_rating,
            'would_recommend': self.would_recommend,
            'is_verified_purchase': self.is_verified_purchase,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# =============================================================================
# LIVE COOKING SESSIONS TABLES
# =============================================================================

class CookingSession(db.Model):
    """Live cooking sessions for food items"""
    __tablename__ = 'cooking_sessions'

    id = db.Column(db.Integer, primary_key=True)
    food_item_id = db.Column(db.Integer, db.ForeignKey('food_items.id'), nullable=False)
    chef_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Chef conducting the session
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    max_participants = db.Column(db.Integer, default=100)
    current_participants = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='scheduled')  # 'scheduled', 'live', 'completed', 'cancelled'
    stream_url = db.Column(db.String(500))  # URL for live streaming
    recording_url = db.Column(db.String(500))  # URL for recorded session
    thumbnail_url = db.Column(db.String(200))
    tags = db.Column(db.Text)  # JSON array of session tags
    difficulty_level = db.Column(db.String(20))  # 'beginner', 'intermediate', 'advanced'
    ingredients_needed = db.Column(db.Text)  # JSON array of required ingredients
    equipment_needed = db.Column(db.Text)  # JSON array of required equipment
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    participants = db.relationship('CookingSessionParticipant', backref='cooking_session', lazy=True, cascade='all, delete-orphan')
    chef = db.relationship('User', foreign_keys=[chef_id])

    def to_dict(self):
        return {
            'id': self.id,
            'food_item_id': self.food_item_id,
            'chef_id': self.chef_id,
            'title': self.title,
            'description': self.description,
            'scheduled_time': self.scheduled_time.isoformat(),
            'duration_minutes': self.duration_minutes,
            'max_participants': self.max_participants,
            'current_participants': self.current_participants,
            'status': self.status,
            'stream_url': self.stream_url,
            'recording_url': self.recording_url,
            'thumbnail_url': self.thumbnail_url,
            'tags': json.loads(self.tags) if self.tags else [],
            'difficulty_level': self.difficulty_level,
            'ingredients_needed': json.loads(self.ingredients_needed) if self.ingredients_needed else [],
            'equipment_needed': json.loads(self.equipment_needed) if self.equipment_needed else []
        }

class CookingSessionParticipant(db.Model):
    """Participants in live cooking sessions"""
    __tablename__ = 'cooking_session_participants'

    id = db.Column(db.Integer, primary_key=True)
    cooking_session_id = db.Column(db.Integer, db.ForeignKey('cooking_sessions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    engagement_score = db.Column(db.Float, default=0.0)  # Based on interactions, questions asked, etc.

    # Ensure unique participation
    __table_args__ = (db.UniqueConstraint('cooking_session_id', 'user_id', name='unique_session_participant'),)

    def to_dict(self):
        return {
            'id': self.id,
            'cooking_session_id': self.cooking_session_id,
            'user_id': self.user_id,
            'joined_at': self.joined_at.isoformat(),
            'left_at': self.left_at.isoformat() if self.left_at else None,
            'is_active': self.is_active,
            'engagement_score': self.engagement_score
        }

# =============================================================================
# REAL DELIVERY SYSTEM TABLES
# =============================================================================

class Restaurant(db.Model):
    """Real restaurant information from external APIs"""
    __tablename__ = 'restaurants'

    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.String(100), unique=True)  # OpenStreetMap ID
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    website = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    rating = db.Column(db.Float)
    price_level = db.Column(db.Integer)  # 1-4 scale
    cuisine_type = db.Column(db.String(50))
    is_open = db.Column(db.Boolean, default=True)
    delivery_available = db.Column(db.Boolean, default=True)
    estimated_delivery_time = db.Column(db.Integer)  # minutes
    delivery_fee = db.Column(db.Float, default=0.0)
    minimum_order = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    menu_items = db.relationship('MenuItem', backref='restaurant', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='restaurant', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'place_id': self.place_id,
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'website': self.website,
            'location': {'lat': self.latitude, 'lng': self.longitude},
            'rating': self.rating,
            'price_level': self.price_level,
            'cuisine_type': self.cuisine_type,
            'is_open': self.is_open,
            'delivery_available': self.delivery_available,
            'estimated_delivery_time': self.estimated_delivery_time,
            'delivery_fee': self.delivery_fee,
            'minimum_order': self.minimum_order
        }


class MenuItem(db.Model):
    """Real menu items from restaurants"""
    __tablename__ = 'menu_items'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))  # Pizza, Burger, Pasta, etc.
    image_url = db.Column(db.String(300))
    is_available = db.Column(db.Boolean, default=True)
    preparation_time = db.Column(db.Integer)  # minutes
    calories = db.Column(db.Integer)
    is_vegetarian = db.Column(db.Boolean, default=False)
    is_vegan = db.Column(db.Boolean, default=False)
    is_gluten_free = db.Column(db.Boolean, default=False)
    spiciness_level = db.Column(db.Integer, default=1)  # 1-5 scale
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    customizations = db.relationship('MenuItemCustomization', backref='menu_item', lazy=True, cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='menu_item', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'image_url': self.image_url,
            'is_available': self.is_available,
            'preparation_time': self.preparation_time,
            'calories': self.calories,
            'is_vegetarian': self.is_vegetarian,
            'is_vegan': self.is_vegan,
            'is_gluten_free': self.is_gluten_free,
            'spiciness_level': self.spiciness_level,
            'customizations': [c.to_dict() for c in self.customizations]
        }


class MenuItemCustomization(db.Model):
    """Available customizations for menu items"""
    __tablename__ = 'menu_item_customizations'

    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    customization_type = db.Column(db.String(50))  # size, toppings, sauce, etc.
    option_name = db.Column(db.String(100))
    additional_price = db.Column(db.Float, default=0.0)
    is_default = db.Column(db.Boolean, default=False)
    is_available = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'customization_type': self.customization_type,
            'option_name': self.option_name,
            'additional_price': self.additional_price,
            'is_default': self.is_default,
            'is_available': self.is_available
        }


class UserLocation(db.Model):
    """User location tracking"""
    __tablename__ = 'user_locations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    zipcode = db.Column(db.String(20))
    country = db.Column(db.String(100))
    location_type = db.Column(db.String(20))  # home, work, other
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='locations')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'location': {'lat': self.latitude, 'lng': self.longitude},
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zipcode': self.zipcode,
            'country': self.country,
            'location_type': self.location_type,
            'is_default': self.is_default
        }


# Update Order model to include restaurant and delivery info
class Order(db.Model):
    """Enhanced order model with delivery tracking"""
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    order_number = db.Column(db.String(20), unique=True)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, preparing, ready, picked_up, delivered, cancelled
    order_type = db.Column(db.String(20), default='delivery')  # delivery, pickup
    subtotal = db.Column(db.Float, nullable=False)
    delivery_fee = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    tip = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, nullable=False)
    special_instructions = db.Column(db.Text)

    # Delivery information
    delivery_address = db.Column(db.Text)
    delivery_latitude = db.Column(db.Float)
    delivery_longitude = db.Column(db.Float)
    estimated_delivery_time = db.Column(db.DateTime)
    actual_delivery_time = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    delivery_tracking = db.relationship('DeliveryTracking', backref='order', uselist=False, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'restaurant_id': self.restaurant_id,
            'order_number': self.order_number,
            'status': self.status,
            'order_type': self.order_type,
            'subtotal': self.subtotal,
            'delivery_fee': self.delivery_fee,
            'tax': self.tax,
            'tip': self.tip,
            'total': self.total,
            'special_instructions': self.special_instructions,
            'delivery_address': self.delivery_address,
            'estimated_delivery_time': self.estimated_delivery_time.isoformat() if self.estimated_delivery_time else None,
            'actual_delivery_time': self.actual_delivery_time.isoformat() if self.actual_delivery_time else None,
            'items': [item.to_dict() for item in self.items],
            'created_at': self.created_at.isoformat()
        }


class OrderItem(db.Model):
    """Individual items in an order with customizations"""
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    special_instructions = db.Column(db.Text)

    # Customizations applied to this item
    customizations = db.Column(db.Text)  # JSON string of customizations

    def to_dict(self):
        return {
            'id': self.id,
            'menu_item_id': self.menu_item_id,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_price': self.total_price,
            'special_instructions': self.special_instructions,
            'customizations': json.loads(self.customizations) if self.customizations else {}
        }


class DeliveryTracking(db.Model):
    """Delivery tracking information"""
    __tablename__ = 'delivery_tracking'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    current_status = db.Column(db.String(50), default='Order Confirmed')
    status_history = db.Column(db.Text)  # JSON array of status updates

    # Driver information
    driver_name = db.Column(db.String(100))
    driver_phone = db.Column(db.String(20))
    driver_vehicle = db.Column(db.String(50))

    # Location tracking
    driver_latitude = db.Column(db.Float)
    driver_longitude = db.Column(db.Float)
    last_location_update = db.Column(db.DateTime)

    # Estimated times
    estimated_pickup_time = db.Column(db.DateTime)
    estimated_delivery_time = db.Column(db.DateTime)
    actual_pickup_time = db.Column(db.DateTime)
    actual_delivery_time = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'current_status': self.current_status,
            'status_history': json.loads(self.status_history) if self.status_history else [],
            'driver_info': {
                'name': self.driver_name,
                'phone': self.driver_phone,
                'vehicle': self.driver_vehicle
            } if self.driver_name else None,
            'driver_location': {
                'lat': self.driver_latitude,
                'lng': self.driver_longitude,
                'last_update': self.last_location_update.isoformat() if self.last_location_update else None
            } if self.driver_latitude else None,
            'estimated_pickup_time': self.estimated_pickup_time.isoformat() if self.estimated_pickup_time else None,
            'estimated_delivery_time': self.estimated_delivery_time.isoformat() if self.estimated_delivery_time else None,
            'actual_pickup_time': self.actual_pickup_time.isoformat() if self.actual_pickup_time else None,
            'actual_delivery_time': self.actual_delivery_time.isoformat() if self.actual_delivery_time else None
        }


class Feedback(db.Model):
    """User feedback for restaurants and app"""
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'))
    feedback_type = db.Column(db.String(20))  # 'restaurant' or 'app'
    rating = db.Column(db.Integer, nullable=False)  # 1-5 scale
    comments = db.Column(db.Text)
    categories = db.Column(db.Text)  # JSON array of feedback categories
    is_anonymous = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='feedback')
    order = db.relationship('Order', backref='feedback')
    restaurant = db.relationship('Restaurant', backref='feedback')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'order_id': self.order_id,
            'restaurant_id': self.restaurant_id,
            'feedback_type': self.feedback_type,
            'rating': self.rating,
            'comments': self.comments,
            'categories': json.loads(self.categories) if self.categories else [],
            'is_anonymous': self.is_anonymous,
            'created_at': self.created_at.isoformat()
        }