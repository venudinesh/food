"""
Smart Food Customization and Ordering System - Flask Backend
Complete REST API server for the Android food ordering application
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
import json
import sys
import logging

# Add ML recommendation engine path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ml_recommendation_engine'))

try:
    from recommendation_api import RecommendationService
    ML_AVAILABLE = True
except ImportError as e:
    print(f"Warning: ML recommendation engine not available: {e}")
    ML_AVAILABLE = False
    RecommendationService = None

# Import real data services
from real_data_services import (
    LocationService, RestaurantService, MenuCustomizationService,
    DeliveryTrackingService, FeedbackService
)

# Import all models
from models import (
    db, User, UserPreference, Ingredient, FoodItem, CustomizationOption,
    Order, OrderItem, Rating, CookingSession, CookingSessionParticipant,
    Restaurant, MenuItem, MenuItemCustomization, UserLocation,
    DeliveryTracking, Feedback
)

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['JWT_SECRET_KEY'] = 'jwt-secret-key-here'
app.config['JWT_ACCESS_TOKEN_EXPIRE_MINUTES'] = 30
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///food_ordering.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
CORS(app, origins="*", supports_credentials=True)
jwt = JWTManager(app)
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize ML Recommendation Service
recommendation_service = None
if ML_AVAILABLE and RecommendationService:
    try:
        recommendation_service = RecommendationService()
        recommendation_service.initialize()
        print("✅ ML Recommendation service initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize ML recommendation service: {e}")
        recommendation_service = None
else:
    print("⚠️ ML Recommendation service not available")

# Initialize Real Data Services
location_service = LocationService()
restaurant_service = RestaurantService()
customization_service = MenuCustomizationService()
delivery_service = DeliveryTrackingService()
feedback_service = FeedbackService()

print("✅ Real data services initialized successfully")

# Models are defined in `models.py` and are imported above.
# Avoid redefining SQLAlchemy models here to prevent Duplicate Table errors.

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({"message": "Preflight OK"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response

# API Routes
@app.route('/')
def root():
    return jsonify({
        'message': 'Smart Food Customization and Ordering System API',
        'version': '1.0.0',
        'status': 'running'
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

    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()

    if user and user.check_password(data['password']):
        # Create JWT token (simplified for demo)
        token = f"jwt_token_for_user_{user.id}"
        return jsonify({
            'access_token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name
            }
        })

    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'phone': user.phone,
        'address': user.address
    })

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

@app.route('/api/food/<int:food_id>', methods=['GET'])
def get_food_item(food_id):
    item = FoodItem.query.get_or_404(food_id)

    # Get customization options
    customizations = CustomizationOption.query.filter_by(food_item_id=food_id).all()

    return jsonify({
        'id': item.id,
        'name': item.name,
        'description': item.description,
        'price': item.price,
        'image_url': item.image_url,
        'category': item.category,
        'preparation_time': item.preparation_time,
        'customizations': [{
            'id': c.id,
            'name': c.name,
            'type': c.type,
            'required': c.required,
            'options': json.loads(c.options) if c.options else []
        } for c in customizations]
    })

# Order endpoints consolidated below (advanced order management handles creations, listing, and tracking).

@app.route('/api/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    user_id = get_jwt_identity()
    order = Order.query.filter_by(id=order_id, user_id=user_id).first_or_404()

    items = OrderItem.query.filter_by(order_id=order_id).all()

    return jsonify({
        'id': order.id,
        'total_amount': order.total_amount,
        'status': order.status,
        'delivery_address': order.delivery_address,
        'payment_method': order.payment_method,
        'created_at': order.created_at.isoformat(),
        'updated_at': order.updated_at.isoformat(),
        'items': [{
            'id': item.id,
            'food_item_id': item.food_item_id,
            'quantity': item.quantity,
            'price': item.price,
            'customizations': json.loads(item.customizations) if item.customizations else {}
        } for item in items]
    })

# Update order status (handled by consolidated order management endpoints below).

@app.route('/api/ratings', methods=['POST'])
@jwt_required()
def create_rating():
    user_id = get_jwt_identity()
    data = request.get_json()

    # Check if user already rated this order item
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

@app.route('/api/food/<int:food_id>/ratings', methods=['GET'])
def get_food_ratings(food_id):
    ratings = Rating.query.filter_by(food_item_id=food_id).order_by(Rating.created_at.desc()).all()

    return jsonify([{
        'id': rating.id,
        'rating': rating.rating,
        'comment': rating.comment,
        'created_at': rating.created_at.isoformat(),
        'user': User.query.get(rating.user_id).username
    } for rating in ratings])

# ML Recommendation Endpoints
@app.route('/api/recommendations', methods=['GET'])
# @jwt_required()  # Temporarily disabled for testing
def get_recommendations():
    """
    Get personalized food recommendations for the authenticated user
    Uses ML recommendation engine with user profile and order history
    """
    try:
        # user_id = get_jwt_identity()
        user_id = request.args.get('user_id', default=1, type=int)  # For testing

        # Get query parameters
        top_n = request.args.get('top_n', default=5, type=int)
        if top_n < 1 or top_n > 20:
            return jsonify({'error': 'top_n must be between 1 and 20'}), 400

        # Check if ML service is available
        if not recommendation_service or not ML_AVAILABLE:
            return jsonify({
                'error': 'Recommendation service not available',
                'fallback': 'popular_items'
            }), 503

        # Get user's order history for better recommendations
        food_history = []
        try:
            user_orders = Order.query.filter_by(user_id=user_id).all()
            for order in user_orders:
                order_items = OrderItem.query.filter_by(order_id=order.id).all()
                for item in order_items:
                    food_history.append(item.food_item_id)
            # Remove duplicates and limit history to recent items
            food_history = list(set(food_history))[:10]  # Last 10 unique items
        except Exception as e:
            print(f"Database query failed, using empty history: {e}")
            food_history = None

        # Get recommendations from ML engine
        result = recommendation_service.get_user_recommendations(
            user_id=user_id,
            food_history=food_history if food_history else None,
            top_n=top_n
        )

        if result['status'] == 'error':
            return jsonify({
                'error': 'Failed to generate recommendations',
                'details': result.get('message', 'Unknown error')
            }), 500

        # Enhance recommendations with food details from database (fallback to ML data)
        enhanced_recommendations = []
        for rec in result['recommendations']:
            # Try to get additional details from database
            food_item = FoodItem.query.get(rec['food_id'])
            if food_item:
                enhanced_rec = {
                    'food_id': rec['food_id'],
                    'name': food_item.name or rec.get('name', 'Unknown'),
                    'description': food_item.description or rec.get('description', ''),
                    'price': food_item.price or rec.get('price', 0),
                    'category': food_item.category or rec.get('category', ''),
                    'image_url': food_item.image_url,
                    'preparation_time': food_item.preparation_time,
                    'score': rec['recommendation_score'],
                    'reason': rec.get('reason', 'Recommended based on your preferences')
                }
            else:
                # Use data from ML engine if not in database
                enhanced_rec = {
                    'food_id': rec['food_id'],
                    'name': rec.get('name', 'Unknown'),
                    'description': rec.get('description', ''),
                    'price': rec.get('price', 0),
                    'category': rec.get('category', ''),
                    'image_url': None,
                    'preparation_time': None,
                    'score': rec['recommendation_score'],
                    'reason': rec.get('reason', 'Recommended based on your preferences')
                }
            enhanced_recommendations.append(enhanced_rec)

        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'recommendations': enhanced_recommendations,
            'total_recommendations': len(enhanced_recommendations),
            'algorithm': 'hybrid_ml',
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"Error in get_recommendations: {e}")
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/api/recommendations/similar/<int:food_id>', methods=['GET'])
def get_similar_foods(food_id):
    """
    Get similar food items based on content features
    Uses ML content-based filtering
    """
    try:
        top_n = request.args.get('top_n', default=5, type=int)
        if top_n < 1 or top_n > 10:
            return jsonify({'error': 'top_n must be between 1 and 10'}), 400

        # Check if food exists
        food_item = FoodItem.query.get(food_id)
        if not food_item:
            return jsonify({'error': 'Food item not found'}), 404

        # Check if ML service is available
        if not recommendation_service or not ML_AVAILABLE:
            return jsonify({
                'error': 'Recommendation service not available'
            }), 503

        # Get similar foods from ML engine
        result = recommendation_service.api.get_similar_foods(food_id, top_n)

        if result['status'] == 'error':
            return jsonify({
                'error': 'Failed to find similar foods',
                'details': result.get('message', 'Unknown error')
            }), 500

        # Enhance with food details
        enhanced_similar = []
        for food_id_sim, score in result['similar_items']:
            similar_food = FoodItem.query.get(food_id_sim)
            if similar_food:
                enhanced_similar.append({
                    'food_id': food_id_sim,
                    'name': similar_food.name,
                    'description': similar_food.description,
                    'price': similar_food.price,
                    'category': similar_food.category,
                    'image_url': similar_food.image_url,
                    'preparation_time': similar_food.preparation_time,
                    'similarity_score': score
                })

        return jsonify({
            'status': 'success',
            'original_food': {
                'id': food_item.id,
                'name': food_item.name,
                'category': food_item.category
            },
            'similar_foods': enhanced_similar,
            'total_similar': len(enhanced_similar),
            'algorithm': 'content_based',
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"Error in get_similar_foods: {e}")
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/api/recommendations/status', methods=['GET'])
def get_recommendation_status():
    """
    Get the status of the ML recommendation service
    Useful for debugging and monitoring
    """
    status_info = {
        'ml_available': ML_AVAILABLE,
        'service_initialized': recommendation_service is not None and recommendation_service.is_initialized if recommendation_service else False,
        'timestamp': datetime.utcnow().isoformat()
    }

    if recommendation_service and recommendation_service.is_initialized:
        status_info.update({
            'status': 'operational',
            'algorithms': ['content_based', 'collaborative', 'hybrid'],
            'model_version': '1.0.0'
        })
    else:
        status_info.update({
            'status': 'unavailable',
            'reason': 'ML service not initialized or not available'
        })

    return jsonify(status_info)

# =============================================================================
# REAL DELIVERY SYSTEM API ENDPOINTS
# =============================================================================

# Location Services
@app.route('/api/location/detect', methods=['GET'])
def detect_location():
    """Detect user location from IP address"""
    try:
        location = location_service.get_location_from_ip()
        if location:
            return jsonify({
                'success': True,
                'location': location
            })
        return jsonify({'success': False, 'error': 'Could not detect location'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/location/geocode', methods=['POST'])
def geocode_address():
    """Geocode an address to coordinates"""
    try:
        data = request.get_json()
        address = data.get('address')
        if not address:
            return jsonify({'success': False, 'error': 'Address required'}), 400

        location = location_service.get_location_from_address(address)
        if location:
            return jsonify({
                'success': True,
                'location': location
            })
        return jsonify({'success': False, 'error': 'Could not geocode address'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Restaurant Services
@app.route('/api/restaurants/nearby', methods=['GET'])
def get_restaurants_nearby():
    """Get restaurants near a location"""
    try:
        lat = float(request.args.get('lat', 0))
        lng = float(request.args.get('lng', 0))
        radius = int(request.args.get('radius', 5000))

        if not lat or not lng:
            return jsonify({'success': False, 'error': 'Latitude and longitude required'}), 400

        restaurants = restaurant_service.search_restaurants_nearby(lat, lng, radius)

        return jsonify({
            'success': True,
            'restaurants': restaurants,
            'count': len(restaurants)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/restaurants/<place_id>', methods=['GET'])
def get_restaurant_details(place_id):
    """Get detailed information about a restaurant"""
    try:
        details = restaurant_service.get_restaurant_details(place_id)
        if details:
            return jsonify({
                'success': True,
                'restaurant': details
            })
        return jsonify({'success': False, 'error': 'Restaurant not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/restaurants/<int:restaurant_id>/menu', methods=['GET'])
def get_restaurant_menu(restaurant_id):
    """Get menu items for a restaurant"""
    try:
        # Get restaurant from database
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            return jsonify({'success': False, 'error': 'Restaurant not found'}), 404

        # Get menu items from database or fetch from API
        menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()

        # If no menu items in database, try to fetch from external API
        if not menu_items:
            menu_data = restaurant_service.get_restaurant_menu(restaurant.name, restaurant.address or "")
            # In a real implementation, you'd save these to the database
            menu_items = [MenuItem(
                restaurant_id=restaurant_id,
                name=item['name'],
                description=item.get('description', ''),
                price=item['price'],
                category=item['category'],
                is_available=True
            ) for item in menu_data]

            # Save to database
            for item in menu_items:
                db.session.add(item)
            db.session.commit()

        return jsonify({
            'success': True,
            'restaurant': restaurant.to_dict(),
            'menu_items': [item.to_dict() for item in menu_items]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/restaurants/<place_id>/menu', methods=['GET'])
def get_restaurant_menu_by_place_id(place_id):
    """Get menu items for a restaurant by place_id"""
    try:
        # Get restaurant name from query parameters
        restaurant_name = request.args.get('name', '')
        cuisine_type = request.args.get('cuisine', 'american')

        if not restaurant_name:
            return jsonify({'success': False, 'error': 'Restaurant name is required'}), 400

        # Get menu data from the restaurant service
        menu_data = restaurant_service.get_restaurant_menu(restaurant_name, cuisine_type)

        # Convert to the expected format
        menu_items = []
        for item in menu_data:
            menu_items.append({
                'id': hash(f"{place_id}_{item['name']}") % 10000,  # Generate a consistent ID
                'name': item['name'],
                'description': item.get('description', ''),
                'price': item['price'],
                'category': item['category'],
                'image_url': item.get('image_url'),
                'is_available': True,
                'customizations': []
            })

        return jsonify({
            'success': True,
            'restaurant': {
                'place_id': place_id,
                'name': restaurant_name,
                'cuisine': cuisine_type
            },
            'menu_items': menu_items
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Menu Customization
@app.route('/api/menu-items/<int:item_id>/customizations', methods=['GET'])
def get_menu_item_customizations(item_id):
    """Get available customizations for a menu item"""
    try:
        menu_item = MenuItem.query.get(item_id)
        if not menu_item:
            return jsonify({'success': False, 'error': 'Menu item not found'}), 404

        # Get customizations from database or generate based on category
        customizations = MenuItemCustomization.query.filter_by(menu_item_id=item_id).all()

        if not customizations:
            # Generate default customizations based on category
            category_options = customization_service.get_customization_options(menu_item.category)
            customizations = []
            for cust_type, options in category_options.items():
                for option in options:
                    if isinstance(option, str):
                        customization = MenuItemCustomization(
                            menu_item_id=item_id,
                            customization_type=cust_type,
                            option_name=option,
                            additional_price=0.0,
                            is_default=False
                        )
                        customizations.append(customization)
                        db.session.add(customization)
            db.session.commit()

        return jsonify({
            'success': True,
            'menu_item': menu_item.to_dict(),
            'customizations': [c.to_dict() for c in customizations]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Order Management with Customizations
@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create a new order with customizations"""
    try:
        # Try to get current user, but allow guest orders
        try:
            current_user_id = get_jwt_identity()
        except:
            current_user_id = None  # Guest order

        data = request.get_json()

        items = data.get('items', [])
        delivery_address = data.get('delivery_address', 'Default Address')
        total_amount = data.get('total_amount', 0)
        payment_method = data.get('payment_method', 'Cash on Delivery')

        if not items:
            return jsonify({'success': False, 'error': 'Items required'}), 400

        # For guest orders, create a simple order record
        order_number = f"ORDER-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Create a simple order object
        order_data = {
            'id': hash(order_number) % 10000,
            'order_number': order_number,
            'user_id': current_user_id,
            'status': 'confirmed',
            'total': total_amount,
            'delivery_address': delivery_address,
            'payment_method': payment_method,
            'items': items,
            'created_at': datetime.utcnow().isoformat()
        }

        return jsonify({
            'success': True,
            'order_id': order_data['id'],
            'order': order_data,
            'message': 'Order created successfully!'
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders', methods=['GET'])
@jwt_required()
def get_user_orders():
    """Get user's order history"""
    try:
        current_user_id = get_jwt_identity()
        orders = Order.query.filter_by(user_id=current_user_id).order_by(Order.created_at.desc()).all()

        return jsonify({
            'success': True,
            'orders': [order.to_dict() for order in orders]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order_details(order_id):
    """Get detailed order information"""
    try:
        current_user_id = get_jwt_identity()
        order = Order.query.filter_by(id=order_id, user_id=current_user_id).first()

        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        return jsonify({
            'success': True,
            'order': order.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Delivery Tracking
@app.route('/api/orders/<int:order_id>/tracking', methods=['GET'])
@jwt_required()
def get_delivery_tracking(order_id):
    """Get delivery tracking information"""
    try:
        current_user_id = get_jwt_identity()
        order = Order.query.filter_by(id=order_id, user_id=current_user_id).first()

        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        tracking = order.delivery_tracking
        if not tracking:
            return jsonify({'success': False, 'error': 'Tracking information not available'}), 404

        return jsonify({
            'success': True,
            'tracking': tracking.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
@jwt_required()
def update_order_status(order_id):
    """Update order status (for restaurant/driver use)"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        message = data.get('message', '')

        if not new_status:
            return jsonify({'success': False, 'error': 'Status required'}), 400

        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        # Update order status
        order.status = new_status
        if new_status == 'delivered':
            order.actual_delivery_time = datetime.utcnow()

        # Update delivery tracking
        if order.delivery_tracking:
            delivery_service.update_delivery_status(order.delivery_tracking, new_status, message)

        db.session.commit()

        return jsonify({
            'success': True,
            'order': order.to_dict(),
            'message': f'Order status updated to {new_status}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Feedback System
@app.route('/api/feedback/restaurant', methods=['POST'])
@jwt_required()
def submit_restaurant_feedback():
    """Submit feedback for a restaurant"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()

        order_id = data.get('order_id')
        restaurant_id = data.get('restaurant_id')
        rating = data.get('rating')
        comments = data.get('comments', '')
        categories = data.get('categories', [])

        if not order_id or not restaurant_id or not rating:
            return jsonify({'success': False, 'error': 'Order ID, restaurant ID, and rating required'}), 400

        feedback = Feedback(
            user_id=current_user_id,
            order_id=order_id,
            restaurant_id=restaurant_id,
            feedback_type='restaurant',
            rating=rating,
            comments=comments,
            categories=json.dumps(categories)
        )

        db.session.add(feedback)
        db.session.commit()

        return jsonify({
            'success': True,
            'feedback': feedback.to_dict(),
            'message': 'Restaurant feedback submitted successfully'
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/feedback/app', methods=['POST'])
@jwt_required()
def submit_app_feedback():
    """Submit feedback for the app"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()

        rating = data.get('rating')
        comments = data.get('comments', '')
        categories = data.get('categories', [])

        if not rating:
            return jsonify({'success': False, 'error': 'Rating required'}), 400

        feedback = Feedback(
            user_id=current_user_id,
            feedback_type='app',
            rating=rating,
            comments=comments,
            categories=json.dumps(categories)
        )

        db.session.add(feedback)
        db.session.commit()

        return jsonify({
            'success': True,
            'feedback': feedback.to_dict(),
            'message': 'App feedback submitted successfully'
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/feedback/restaurant/<int:restaurant_id>', methods=['GET'])
def get_restaurant_feedback(restaurant_id):
    """Get feedback for a restaurant"""
    try:
        feedback_list = Feedback.query.filter_by(
            restaurant_id=restaurant_id,
            feedback_type='restaurant'
        ).order_by(Feedback.created_at.desc()).limit(10).all()

        return jsonify({
            'success': True,
            'feedback': [f.to_dict() for f in feedback_list]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()

        # Database initialized without sample data

# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('connected', {'status': 'success'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")

@socketio.on('join_stream')
def handle_join_stream(data):
    """Handle joining a cooking stream"""
    try:
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        user_type = data.get('user_type', 'viewer')  # 'chef' or 'viewer'

        if not room_id:
            emit('error', {'message': 'Room ID required'})
            return

        join_room(room_id)
        emit('joined_stream', {
            'room_id': room_id,
            'user_id': user_id,
            'user_type': user_type,
            'timestamp': datetime.utcnow().isoformat()
        })

        # Notify others in the room
        emit('user_joined', {
            'user_id': user_id,
            'user_type': user_type,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room_id, skip_sid=request.sid)

    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('leave_stream')
def handle_leave_stream(data):
    """Handle leaving a cooking stream"""
    try:
        room_id = data.get('room_id')
        user_id = data.get('user_id')

        if room_id:
            leave_room(room_id)
            emit('left_stream', {
                'room_id': room_id,
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat()
            })

            # Notify others in the room
            emit('user_left', {
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room_id, skip_sid=request.sid)

    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('webrtc_offer')
def handle_webrtc_offer(data):
    """Handle WebRTC offer for video streaming"""
    try:
        room_id = data.get('room_id')
        offer = data.get('offer')

        if not room_id or not offer:
            emit('error', {'message': 'Room ID and offer required'})
            return

        # Forward offer to other participants in the room
        emit('webrtc_offer', {
            'offer': offer,
            'from': request.sid
        }, room=room_id, skip_sid=request.sid)

    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('webrtc_answer')
def handle_webrtc_answer(data):
    """Handle WebRTC answer"""
    try:
        room_id = data.get('room_id')
        answer = data.get('answer')

        if not room_id or not answer:
            emit('error', {'message': 'Room ID and answer required'})
            return

        # Forward answer to the specific recipient
        emit('webrtc_answer', {
            'answer': answer,
            'from': request.sid
        }, room=room_id, skip_sid=request.sid)

    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('webrtc_ice_candidate')
def handle_ice_candidate(data):
    """Handle ICE candidate exchange"""
    try:
        room_id = data.get('room_id')
        candidate = data.get('candidate')

        if not room_id or not candidate:
            emit('error', {'message': 'Room ID and candidate required'})
            return

        # Forward ICE candidate to other participants
        emit('webrtc_ice_candidate', {
            'candidate': candidate,
            'from': request.sid
        }, room=room_id, skip_sid=request.sid)

    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle real-time chat messages"""
    try:
        room_id = data.get('room_id')
        message = data.get('message')
        user_id = data.get('user_id')
        username = data.get('username')

        if not room_id or not message:
            emit('error', {'message': 'Room ID and message required'})
            return

        # Broadcast message to all participants in the room
        emit('chat_message', {
            'message': message,
            'user_id': user_id,
            'username': username,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room_id)

    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('stream_status_update')
def handle_stream_status_update(data):
    """Handle stream status updates (start, pause, end)"""
    try:
        room_id = data.get('room_id')
        status = data.get('status')  # 'started', 'paused', 'ended'
        user_id = data.get('user_id')

        if not room_id or not status:
            emit('error', {'message': 'Room ID and status required'})
            return

        # Broadcast status update to all participants
        emit('stream_status_update', {
            'status': status,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room_id)

    except Exception as e:
        emit('error', {'message': str(e)})

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=8000)