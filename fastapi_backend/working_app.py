"""
Working Flask Backend for Smart Food Ordering System
A complete REST API server that the Android app can consume
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import json

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///food_ordering.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
CORS(app)
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
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

class FoodItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200))
    category = db.Column(db.String(50))
    is_available = db.Column(db.Boolean, default=True)
    preparation_time = db.Column(db.Integer)  # in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    delivery_address = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    food_item_id = db.Column(db.Integer, db.ForeignKey('food_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    customizations = db.Column(db.Text)  # JSON string of customizations

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    food_item_id = db.Column(db.Integer, db.ForeignKey('food_item.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Simple authentication (no JWT for simplicity)
def authenticate_user(email, password):
    """Simple authentication function"""
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        return user
    return None

# API Routes
@app.route('/')
def root():
    return jsonify({
        'message': 'Smart Food Customization and Ordering System API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': [
            'POST /api/auth/register',
            'POST /api/auth/login',
            'GET /api/food',
            'POST /api/orders',
            'GET /api/orders',
            'POST /api/ratings'
        ]
    })

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken'}), 400

    user = User(
        username=data['username'],
        email=data['email'],
        full_name=data.get('full_name'),
        phone=data.get('phone'),
        address=data.get('address')
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'message': 'User registered successfully',
        'user_id': user.id
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = authenticate_user(data['email'], data['password'])

    if user:
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name
            },
            'token': f"user_{user.id}_token"  # Simple token for demo
        })

    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/food', methods=['GET'])
def get_food_items():
    category = request.args.get('category')
    search = request.args.get('search')

    query = FoodItem.query.filter_by(is_available=True)

    if category:
        query = query.filter_by(category=category)

    if search:
        query = query.filter(FoodItem.name.contains(search))

    food_items = query.all()

    return jsonify([{
        'id': item.id,
        'name': item.name,
        'description': item.description,
        'price': item.price,
        'image_url': item.image_url,
        'category': item.category,
        'preparation_time': item.preparation_time
    } for item in food_items])

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()

    # Simple authentication check (in real app, use proper auth)
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authentication required'}), 401

    token = auth_header.replace('Bearer ', '')
    if not token.startswith('user_') or not token.endswith('_token'):
        return jsonify({'error': 'Invalid token'}), 401

    user_id = int(token.replace('user_', '').replace('_token', ''))

    order = Order(
        user_id=user_id,
        total_amount=data['total_amount'],
        delivery_address=data['delivery_address'],
        payment_method=data['payment_method']
    )

    db.session.add(order)
    db.session.flush()

    for item_data in data['items']:
        order_item = OrderItem(
            order_id=order.id,
            food_item_id=item_data['food_item_id'],
            quantity=item_data['quantity'],
            price=item_data['price'],
            customizations=json.dumps(item_data.get('customizations', {}))
        )
        db.session.add(order_item)

    db.session.commit()

    return jsonify({
        'order_id': order.id,
        'message': 'Order created successfully',
        'status': 'pending'
    }), 201

@app.route('/api/orders', methods=['GET'])
def get_orders():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authentication required'}), 401

    token = auth_header.replace('Bearer ', '')
    if not token.startswith('user_') or not token.endswith('_token'):
        return jsonify({'error': 'Invalid token'}), 401

    user_id = int(token.replace('user_', '').replace('_token', ''))

    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()

    return jsonify([{
        'id': order.id,
        'total_amount': order.total_amount,
        'status': order.status,
        'delivery_address': order.delivery_address,
        'created_at': order.created_at.isoformat(),
        'updated_at': order.updated_at.isoformat()
    } for order in orders])

@app.route('/api/ratings', methods=['POST'])
def create_rating():
    data = request.get_json()

    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authentication required'}), 401

    token = auth_header.replace('Bearer ', '')
    if not token.startswith('user_') or not token.endswith('_token'):
        return jsonify({'error': 'Invalid token'}), 401

    user_id = int(token.replace('user_', '').replace('_token', ''))

    existing = Rating.query.filter_by(
        user_id=user_id,
        order_id=data['order_id'],
        food_item_id=data['food_item_id']
    ).first()

    if existing:
        return jsonify({'error': 'Already rated this item'}), 400

    rating = Rating(
        user_id=user_id,
        order_id=data['order_id'],
        food_item_id=data['food_item_id'],
        rating=data['rating'],
        comment=data.get('comment')
    )

    db.session.add(rating)
    db.session.commit()

    return jsonify({'message': 'Rating submitted successfully'}), 201

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
        print("Database initialized without sample data")

if __name__ == '__main__':
    init_db()
    print("🚀 Smart Food Ordering API starting...")
    app.run(debug=True, host='0.0.0.0', port=8000)