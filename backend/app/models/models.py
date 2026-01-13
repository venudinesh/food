from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    orders = db.relationship('Order', backref='user', lazy=True)
    feedbacks = db.relationship('Feedback', backref='user', lazy=True)
    locations = db.relationship('UserLocation', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20))
    website = db.Column(db.String(255))
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    rating = db.Column(db.Float)
    price_level = db.Column(db.Integer)
    cuisine_type = db.Column(db.String(100))
    is_open = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    menu_items = db.relationship('MenuItem', backref='restaurant', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='restaurant', lazy=True)
    feedbacks = db.relationship('Feedback', backref='restaurant', lazy=True)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(500))
    is_available = db.Column(db.Boolean, default=True)
    preparation_time = db.Column(db.Integer)  # in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    customizations = db.relationship('MenuItemCustomization', backref='menu_item', lazy=True, cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='menu_item', lazy=True)

class MenuItemCustomization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)  # e.g., "Spice Level", "Extra Toppings"
    customization_type = db.Column(db.String(50), nullable=False)  # 'radio', 'checkbox', 'text'
    is_required = db.Column(db.Boolean, default=False)
    max_selections = db.Column(db.Integer, default=1)  # for checkbox types

    # Relationships
    options = db.relationship('CustomizationOption', backref='customization', lazy=True, cascade='all, delete-orphan')

class CustomizationOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customization_id = db.Column(db.Integer, db.ForeignKey('menu_item_customization.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)  # e.g., "Mild", "Extra Cheese"
    price = db.Column(db.Float, default=0.0)
    is_default = db.Column(db.Boolean, default=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'))
    status = db.Column(db.String(50), default='confirmed')  # confirmed, preparing, ready, picked_up, delivered, cancelled
    total_amount = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.String(50), default='card')
    payment_status = db.Column(db.String(50), default='pending')
    special_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    estimated_delivery = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    tracking = db.relationship('DeliveryTracking', backref='order', lazy=True, uselist=False, cascade='all, delete-orphan')
    feedback = db.relationship('Feedback', backref='order', lazy=True, uselist=False)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    customizations = db.Column(db.Text)  # JSON string of selected customizations
    customization_price = db.Column(db.Float, default=0.0)

class DeliveryTracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    location = db.Column(db.Text)  # JSON string with lat/lng
    estimated_time = db.Column(db.String(100))  # e.g., "15-20 minutes"
    driver_name = db.Column(db.String(255))
    driver_phone = db.Column(db.String(20))
    notes = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    is_current = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'))
    restaurant_rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    delivery_rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    food_quality_rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comments = db.Column(db.Text)
    would_recommend = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Additional feedback categories
    value_rating = db.Column(db.Integer)  # Value for money
    packaging_rating = db.Column(db.Integer)  # Food packaging quality
    app_experience_rating = db.Column(db.Integer)  # App usability