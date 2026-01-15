"""
Smart Food Ordering System - Clean Database Schema
==================================================

Simplified database schema with only essential tables:
- restaurants: Restaurant information
- menu_items: Menu items for each restaurant

Author: Cleaned Implementation
Date: January 2026
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# =============================================================================
# RESTAURANT TABLES (Cleaned Schema)
# =============================================================================

class Restaurant(db.Model):
    """Restaurant information"""
    __tablename__ = 'restaurants'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    rating = db.Column(db.Float)
    cuisine_type = db.Column(db.String(100))
    delivery_available = db.Column(db.Boolean, default=True)
    estimated_delivery_time = db.Column(db.Integer)  # in minutes
    delivery_fee = db.Column(db.Float, default=0.0)
    minimum_order = db.Column(db.Float, default=0.0)

    # Relationship to menu items
    menu_items = db.relationship('MenuItem', backref='restaurant', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'rating': self.rating,
            'cuisine_type': self.cuisine_type,
            'delivery_available': self.delivery_available,
            'estimated_delivery_time': self.estimated_delivery_time,
            'delivery_fee': self.delivery_fee,
            'minimum_order': self.minimum_order
        }


class MenuItem(db.Model):
    """Menu item for a restaurant"""
    __tablename__ = 'menu_items'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100))  # e.g., 'Main Course', 'Beverage', 'Dessert'

    def to_dict(self):
        return {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'name': self.name,
            'price': self.price,
            'category': self.category
        }


# =============================================================================
# LEGACY USER MODEL (For Authentication - if needed)
# =============================================================================

class User(db.Model):
    """Basic user model for authentication"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
            'address': self.address
        }