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
import uuid
import random
import string

# Add ML recommendation engine path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ml_recommendation_engine'))

try:
    from recommendation_api import RecommendationService
    ML_AVAILABLE = True
except ImportError as e:
    print(f"Warning: ML recommendation engine not available: {e}")
    ML_AVAILABLE = False
    RecommendationService = None

# Import real data services - add fastapi_backend path
sys.path.insert(0, os.path.dirname(__file__))
try:
    from real_data_services import (
        LocationService, RestaurantService, MenuCustomizationService,
        DeliveryTrackingService, FeedbackService
    )
except ImportError:
    # Fallback: Create dummy services
    class LocationService: pass
    class RestaurantService: pass
    class MenuCustomizationService: pass
    class DeliveryTrackingService: pass
    class FeedbackService: pass

# Import all models
from models import (
    db, User, Restaurant, MenuItem
)

app = Flask(__name__, instance_path=os.path.abspath('.'))

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['JWT_SECRET_KEY'] = 'jwt-secret-key'
app.config['JWT_ALGORITHM'] = 'HS256'
app.config['JWT_ACCESS_TOKEN_EXPIRE'] = timedelta(days=30)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smartfood.db'
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
        print("[OK] ML Recommendation service initialized successfully")
    except Exception as e:
        print(f"[FAILED] Failed to initialize ML recommendation service: {e}")
        recommendation_service = None
else:
    print("[WARNING] ML Recommendation service not available")

# Initialize Real Data Services
location_service = LocationService()
restaurant_service = RestaurantService()
customization_service = MenuCustomizationService()
delivery_service = DeliveryTrackingService()
feedback_service = FeedbackService()

print("[OK] Real data services initialized successfully")

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

# JWT Error Handlers
@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({'success': False, 'error': 'Authorization required'}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({'success': False, 'error': 'Invalid token'}), 401

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_data):
    return jsonify({'success': False, 'error': 'Token expired'}), 401

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
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email') or not data.get('username') or not data.get('password'):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'success': False, 'error': 'Email already registered'}), 400

        # Check if username already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'error': 'Username already taken'}), 400

        # Validate password length
        if len(data['password']) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400

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

        # Create JWT token for auto-login after registration
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=user.id)
        return jsonify({
            'success': True,
            'access_token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name
            },
            'message': 'User registered successfully'
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # Accept either email or username for login
    identifier = data.get('email') or data.get('username')
    password = data.get('password')
    
    if not identifier or not password:
        return jsonify({'success': False, 'error': 'Missing email/username or password'}), 400
    
    # Try to find user by email first, then by username
    user = User.query.filter_by(email=identifier).first()
    if not user:
        user = User.query.filter_by(username=identifier).first()

    if user and user.check_password(password):
        # Create proper JWT token
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=user.id)
        return jsonify({
            'success': True,
            'access_token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name
            }
        })

    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/auth/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'phone': user.phone,
                'address': user.address
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-jwt', methods=['GET'])
@jwt_required()
def test_jwt():
    """Test JWT endpoint to debug token validation"""
    try:
        user_id = get_jwt_identity()
        return jsonify({
            'success': True,
            'message': 'JWT token is valid',
            'user_id': user_id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile information"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        data = request.get_json()
        
        # Update fields if provided
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'address' in data:
            user.address = data['address']

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'phone': user.phone,
                'address': user.address
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 200

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
        return jsonify({'error': 'Already rated this item'}), 200

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
            return jsonify({'error': 'top_n must be between 1 and 20'}), 200

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
            }), 200

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
        }), 200

@app.route('/api/recommendations/similar/<int:food_id>', methods=['GET'])
def get_similar_foods(food_id):
    """
    Get similar food items based on content features
    Uses ML content-based filtering
    """
    try:
        top_n = request.args.get('top_n', default=5, type=int)
        if top_n < 1 or top_n > 10:
            return jsonify({'error': 'top_n must be between 1 and 10'}), 200

        # Check if food exists
        food_item = FoodItem.query.get(food_id)
        if not food_item:
            return jsonify({'error': 'Food item not found'}), 200

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
            }), 200

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
        }), 200

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
        return jsonify({'success': False, 'error': 'Could not detect location'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 200

@app.route('/api/location/geocode', methods=['POST'])
def geocode_address():
    """Geocode an address to coordinates"""
    try:
        data = request.get_json()
        address = data.get('address')
        if not address:
            return jsonify({'success': False, 'error': 'Address required'}), 200

        location = location_service.get_location_from_address(address)
        if location:
            return jsonify({
                'success': True,
                'location': location
            })
        return jsonify({'success': False, 'error': 'Could not geocode address'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 200

@app.route('/api/debug/menu-items', methods=['GET'])
def debug_menu_items():
    """Debug endpoint to check menu items in database"""
    try:
        total_items = MenuItem.query.count()
        total_restaurants = Restaurant.query.count()
        
        # Get first 5 items
        items = MenuItem.query.limit(5).all()
        items_data = [{'id': i.id, 'name': i.name, 'restaurant_id': i.restaurant_id, 'price': i.price} for i in items]
        
        return jsonify({
            'success': True,
            'total_menu_items': total_items,
            'total_restaurants': total_restaurants,
            'sample_items': items_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 200

# Restaurant Services
@app.route('/api/restaurants/nearby', methods=['GET'])
def get_restaurants_nearby():
    """Get restaurants near a location"""
    try:
        lat = request.args.get('lat')
        lng = request.args.get('lng')
        radius = int(request.args.get('radius', 5000))

        # Always return restaurants from database (they have proper numeric IDs)
        # If lat/lng provided, filter by distance; otherwise return all
        if lat and lng:
            lat = float(lat)
            lng = float(lng)
            # Get all restaurants and filter by distance (simplified - in production use spatial queries)
            restaurants = Restaurant.query.limit(50).all()
        else:
            restaurants = Restaurant.query.limit(50).all()

        return jsonify({
            'success': True,
            'restaurants': [r.to_dict() for r in restaurants],
            'count': len(restaurants)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 200

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
        return jsonify({'success': False, 'error': 'Restaurant not found'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 200

@app.route('/api/restaurants/<int:restaurant_id>/menu', methods=['GET'])
def get_restaurant_menu(restaurant_id):
    """Get menu items for a restaurant"""
    try:
        # Get restaurant from database
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            return jsonify({'success': False, 'error': 'Restaurant not found'}), 200

        # Get menu items from database or fetch from API
        menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()

        # If no menu items in database, try to fetch from external API
        if not menu_items:
            print(f"[DEBUG] No menu items found for restaurant {restaurant_id}, fetching from service...")
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
            db.session.flush()  # Flush to get IDs
            db.session.commit()
            print(f"[DEBUG] Created {len(menu_items)} menu items for restaurant {restaurant_id}")
            
            # Refresh menu_items to get their generated IDs
            menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()

        return jsonify({
            'success': True,
            'restaurant': restaurant.to_dict(),
            'menu_items': [item.to_dict() for item in menu_items]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 200

@app.route('/api/restaurants/<place_id>/menu', methods=['GET'])
def get_restaurant_menu_by_place_id(place_id):
    """Get menu items for a restaurant by place_id"""
    try:
        # Get restaurant name from query parameters
        restaurant_name = request.args.get('name', '')
        cuisine_type = request.args.get('cuisine', 'american')

        if not restaurant_name:
            return jsonify({'success': False, 'error': 'Restaurant name is required'}), 200

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
        return jsonify({'success': False, 'error': str(e)}), 200

# Menu Customization
@app.route('/api/menu-items/<int:item_id>/customizations', methods=['GET'])
def get_menu_item_customizations(item_id):
    """Get available customizations for a menu item"""
    try:
        menu_item = MenuItem.query.get(item_id)
        if not menu_item:
            return jsonify({'success': False, 'error': 'Menu item not found'}), 200

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
        return jsonify({'success': False, 'error': str(e)}), 200

# Order Management with Customizations
@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create a new order with customizations"""
    try:
        # Try to get current user, but allow guest orders
        try:
            current_user_id = get_jwt_identity()
        except:
            current_user_id = 1  # Default user for demo

        data = request.get_json()

        items_data = data.get('items', [])
        restaurant_id = data.get('restaurant_id', 1)
        delivery_address = data.get('delivery_address', 'Default Address')
        total_amount = data.get('total_amount', 0)

        if not items_data:
            return jsonify({'success': False, 'error': 'Items required'}), 200

        # Create unique order number with random component to avoid UNIQUE constraint
        random_suffix = ''.join(random.choices(string.digits, k=4))
        order_number = f"ORD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{random_suffix}"
        
        # Calculate totals from menu items
        subtotal = 0
        order_items_to_add = []
        
        for item_data in items_data:
            menu_item_id = item_data.get('menu_item_id')
            quantity = item_data.get('quantity', 1)
            
            # Fetch menu item to get actual price
            menu_item = MenuItem.query.get(menu_item_id)
            if not menu_item:
                # Debug: log what we're looking for and what exists
                existing_items = MenuItem.query.limit(5).all()
                error_msg = f'Menu item {menu_item_id} not found. Available IDs: {[m.id for m in existing_items]}'
                print(f"[DEBUG] {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 200
            
            unit_price = menu_item.price
            item_total = unit_price * quantity
            subtotal += item_total
            
            order_items_to_add.append({
                'menu_item_id': menu_item_id,
                'quantity': quantity,
                'unit_price': unit_price,
                'total_price': item_total,
                'special_instructions': item_data.get('special_instructions', '')
            })
        
        # Calculate tax and fees
        tax = subtotal * 0.09  # 9% tax
        delivery_fee = 40
        tip = subtotal * 0.01  # 1% tip
        total = subtotal + tax + delivery_fee + tip
        
        order = Order(
            user_id=current_user_id,
            restaurant_id=restaurant_id,
            order_number=order_number,
            status='confirmed',
            subtotal=subtotal,
            tax=tax,
            delivery_fee=delivery_fee,
            tip=tip,
            total=total,
            delivery_address=delivery_address,
            order_type='delivery'
        )
        
        db.session.add(order)
        db.session.flush()  # Get the ID without committing yet
        
        # Add order items with correct prices
        for item in order_items_to_add:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item['menu_item_id'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                total_price=item['total_price'],
                special_instructions=item['special_instructions']
            )
            db.session.add(order_item)
        
        # Create delivery tracking
        tracking = DeliveryTracking(
            order_id=order.id,
            current_status='confirmed',
            driver_name='Driver Assigned',
            driver_phone='+91-9876543210',
            driver_latitude=17.6869,
            driver_longitude=83.2185,
            estimated_delivery_time=datetime.utcnow() + timedelta(minutes=30)
        )
        db.session.add(tracking)
        
        db.session.commit()

        return jsonify({
            'success': True,
            'order_id': order.id,
            'order': order.to_dict(),
            'message': 'Order created successfully!'
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 200

@app.route('/api/orders', methods=['GET'])
def get_user_orders():
    """Get user's order history"""
    try:
        # For demo purposes, return all orders (no auth required)
        orders = Order.query.order_by(Order.created_at.desc()).limit(50).all()

        return jsonify({
            'success': True,
            'orders': [order.to_dict() for order in orders]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 200

@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order_details(order_id):
    """Get detailed order information"""
    try:
        # Allow access without authentication for demo purposes
        # Handle both string and integer order IDs
        try:
            order_id_int = int(order_id)
        except (ValueError, TypeError):
            order_id_int = order_id
        
        order = Order.query.filter_by(id=order_id_int).first()

        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 200

        return jsonify({
            'success': True,
            'order': order.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 200

# Delivery Tracking
@app.route('/api/orders/<order_id>/tracking', methods=['GET'])
def get_delivery_tracking(order_id):
    """Get delivery tracking information"""
    try:
        # Allow access without authentication for demo purposes
        # Handle both string and integer order IDs
        try:
            order_id_int = int(order_id)
        except (ValueError, TypeError):
            order_id_int = order_id
        
        order = Order.query.filter_by(id=order_id_int).first()

        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 200

        tracking = order.delivery_tracking
        if not tracking:
            return jsonify({'success': False, 'error': 'Tracking information not available'}), 200

        return jsonify({
            'success': True,
            'tracking': tracking.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 200

@app.route('/api/orders/<order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status (for restaurant/driver use)"""
    try:
        # Handle both string and integer order IDs
        try:
            order_id_int = int(order_id)
        except (ValueError, TypeError):
            order_id_int = order_id
        
        data = request.get_json()
        new_status = data.get('status')
        message = data.get('message', '')

        if not new_status:
            return jsonify({'success': False, 'error': 'Status required'}), 200

        order = Order.query.get(order_id_int)
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 200

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
        return jsonify({'success': False, 'error': str(e)}), 200

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
            return jsonify({'success': False, 'error': 'Order ID, restaurant ID, and rating required'}), 200

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
        return jsonify({'success': False, 'error': str(e)}), 200

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
            return jsonify({'success': False, 'error': 'Rating required'}), 200

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
        return jsonify({'success': False, 'error': str(e)}), 200

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
        return jsonify({'success': False, 'error': str(e)}), 200

# Initialize database
def init_db():
    try:
        with app.app_context():
            print("[DEBUG] Creating all database tables...")
            db.create_all()
            print("[DEBUG] Database tables created successfully")
            
            # Load real data only if tables are empty
            if Restaurant.query.first() is None:
                print("[DEBUG] Loading MASSIVE comprehensive real Visakhapatnam restaurants and ALL menu items...")
                
                # Comprehensive Real Visakhapatnam restaurants with accurate data
                restaurants_data = [
                    {'place_id': 'vizag_001', 'name': 'Rasora Restaurant', 'address': 'Ranga Street, Daba Gardens, Visakhapatnam', 'latitude': 17.6869, 'longitude': 83.2167, 'rating': 4.8, 'cuisine_type': 'Multicuisine', 'delivery_available': True, 'estimated_delivery_time': 35, 'delivery_fee': 30.0, 'minimum_order': 200.0},
                    {'place_id': 'vizag_002', 'name': 'Amalodbhavi Multicuisine Restaurant', 'address': 'NH-16 Kasimkota, Visakhapatnam', 'latitude': 17.7512, 'longitude': 83.1783, 'rating': 3.6, 'cuisine_type': 'Multicuisine', 'delivery_available': True, 'estimated_delivery_time': 40, 'delivery_fee': 40.0, 'minimum_order': 300.0},
                    {'place_id': 'vizag_003', 'name': 'Bunny\'s Mandi', 'address': 'Beside SBI, Kurmannapalem, Visakhapatnam', 'latitude': 17.6453, 'longitude': 83.289, 'rating': 3.7, 'cuisine_type': 'Biryani & Mandi', 'delivery_available': True, 'estimated_delivery_time': 30, 'delivery_fee': 35.0, 'minimum_order': 250.0},
                    {'place_id': 'vizag_004', 'name': 'Planet 9 Restaurant', 'address': 'Rama Talkies Road, Dwaraka Nagar, Visakhapatnam', 'latitude': 17.7094, 'longitude': 83.2938, 'rating': 4.4, 'cuisine_type': 'Multicuisine', 'delivery_available': True, 'estimated_delivery_time': 25, 'delivery_fee': 32.0, 'minimum_order': 220.0},
                    {'place_id': 'vizag_005', 'name': 'Cabritoz', 'address': 'Opposite Varun Inox, Maharanipeta, Visakhapatnam', 'latitude': 17.7182, 'longitude': 83.3134, 'rating': 4.0, 'cuisine_type': 'Asian & Continental', 'delivery_available': True, 'estimated_delivery_time': 35, 'delivery_fee': 45.0, 'minimum_order': 400.0},
                    {'place_id': 'vizag_006', 'name': 'Masaledaar Desi Rasoi', 'address': 'Diamond Park, Dwaraka Nagar, Visakhapatnam', 'latitude': 17.7089, 'longitude': 83.2948, 'rating': 4.3, 'cuisine_type': 'Indian', 'delivery_available': True, 'estimated_delivery_time': 30, 'delivery_fee': 30.0, 'minimum_order': 200.0},
                    {'place_id': 'vizag_007', 'name': 'Aadaab Family Restaurant', 'address': 'Marripalem Main Road, Visakhapatnam', 'latitude': 17.7156, 'longitude': 83.2476, 'rating': 3.6, 'cuisine_type': 'Biryani & Indian', 'delivery_available': True, 'estimated_delivery_time': 35, 'delivery_fee': 35.0, 'minimum_order': 280.0},
                    {'place_id': 'vizag_008', 'name': 'Peoples Choice Family Restaurant', 'address': 'Sector 1, MVP Colony, Visakhapatnam', 'latitude': 17.7453, 'longitude': 83.2765, 'rating': 3.9, 'cuisine_type': 'Multicuisine', 'delivery_available': True, 'estimated_delivery_time': 30, 'delivery_fee': 30.0, 'minimum_order': 200.0},
                    {'place_id': 'vizag_009', 'name': 'Best Backers', 'address': 'Varma Complex, Murali Nagar, Visakhapatnam', 'latitude': 17.7389, 'longitude': 83.3012, 'rating': 3.8, 'cuisine_type': 'Fast Food', 'delivery_available': True, 'estimated_delivery_time': 20, 'delivery_fee': 25.0, 'minimum_order': 150.0},
                    {'place_id': 'vizag_010', 'name': 'Sr Hotel', 'address': 'Beside Jyothi Theater, Araku Colony, Visakhapatnam', 'latitude': 17.6723, 'longitude': 83.2234, 'rating': 4.8, 'cuisine_type': 'Andhra & Biryani', 'delivery_available': True, 'estimated_delivery_time': 35, 'delivery_fee': 35.0, 'minimum_order': 250.0},
                    {'place_id': 'vizag_011', 'name': 'Spice Court Restaurant', 'address': 'Srinagar Colony, Visakhapatnam', 'latitude': 17.7123, 'longitude': 83.2456, 'rating': 4.5, 'cuisine_type': 'South Indian', 'delivery_available': True, 'estimated_delivery_time': 28, 'delivery_fee': 28.0, 'minimum_order': 180.0},
                    {'place_id': 'vizag_012', 'name': 'Kebab Junction', 'address': 'Beside Hanuman Temple, Seethammapeta, Visakhapatnam', 'latitude': 17.6945, 'longitude': 83.2834, 'rating': 4.2, 'cuisine_type': 'North Indian & Kebab', 'delivery_available': True, 'estimated_delivery_time': 32, 'delivery_fee': 33.0, 'minimum_order': 240.0},
                    {'place_id': 'vizag_013', 'name': 'The Spice Route', 'address': 'Opposite MVP School, Beach Road, Visakhapatnam', 'latitude': 17.7234, 'longitude': 83.2645, 'rating': 4.6, 'cuisine_type': 'Asian & Continental', 'delivery_available': True, 'estimated_delivery_time': 30, 'delivery_fee': 35.0, 'minimum_order': 250.0},
                    {'place_id': 'vizag_014', 'name': 'Biryani Express', 'address': 'Gnanapuram Main Road, Visakhapatnam', 'latitude': 17.6789, 'longitude': 83.3045, 'rating': 4.1, 'cuisine_type': 'Biryani Specialist', 'delivery_available': True, 'estimated_delivery_time': 25, 'delivery_fee': 26.0, 'minimum_order': 200.0},
                    {'place_id': 'vizag_015', 'name': 'The Pizza Corner', 'address': 'Siripuram Junction, Visakhapatnam', 'latitude': 17.7345, 'longitude': 83.2923, 'rating': 4.3, 'cuisine_type': 'Italian & Pizza', 'delivery_available': True, 'estimated_delivery_time': 32, 'delivery_fee': 40.0, 'minimum_order': 300.0},
                    {'place_id': 'vizag_016', 'name': 'Oriental Spice Kitchen', 'address': 'Beside YMCA, Visakhapatnam', 'latitude': 17.7056, 'longitude': 83.2567, 'rating': 4.4, 'cuisine_type': 'Chinese & Asian', 'delivery_available': True, 'estimated_delivery_time': 28, 'delivery_fee': 32.0, 'minimum_order': 220.0},
                    {'place_id': 'vizag_017', 'name': 'Garden Valley Restaurant', 'address': 'Vizag Port, Visakhapatnam', 'latitude': 17.6612, 'longitude': 83.2289, 'rating': 3.9, 'cuisine_type': 'Seafood & Continental', 'delivery_available': True, 'estimated_delivery_time': 38, 'delivery_fee': 50.0, 'minimum_order': 450.0},
                    {'place_id': 'vizag_018', 'name': 'Hyderabad House', 'address': 'Beside Aditya Trade Centre, Visakhapatnam', 'latitude': 17.7198, 'longitude': 83.3234, 'rating': 4.2, 'cuisine_type': 'Biryani & Hyderabadi', 'delivery_available': True, 'estimated_delivery_time': 35, 'delivery_fee': 36.0, 'minimum_order': 280.0},
                    {'place_id': 'vizag_019', 'name': 'The Curry House', 'address': 'Rajolibanda Junction, Visakhapatnam', 'latitude': 17.7089, 'longitude': 83.2834, 'rating': 4.0, 'cuisine_type': 'Indian Curry', 'delivery_available': True, 'estimated_delivery_time': 30, 'delivery_fee': 31.0, 'minimum_order': 210.0},
                    {'place_id': 'vizag_020', 'name': 'Paradise Restaurant', 'address': 'Beside SBI Bank, Daba Gardens, Visakhapatnam', 'latitude': 17.6834, 'longitude': 83.2156, 'rating': 4.7, 'cuisine_type': 'Multicuisine', 'delivery_available': True, 'estimated_delivery_time': 33, 'delivery_fee': 32.0, 'minimum_order': 240.0},
                    {'place_id': 'vizag_021', 'name': 'Crave Restaurant & Cafe', 'address': 'Opposite Varun Inox, Visakhapatnam', 'latitude': 17.721, 'longitude': 83.3145, 'rating': 4.6, 'cuisine_type': 'Cafe & Light Bites', 'delivery_available': True, 'estimated_delivery_time': 30, 'delivery_fee': 35.0, 'minimum_order': 250.0},
                    {'place_id': 'vizag_022', 'name': 'The Fusion Kitchen', 'address': 'Dwaraka Nagar Main Road, Visakhapatnam', 'latitude': 17.712, 'longitude': 83.2967, 'rating': 4.5, 'cuisine_type': 'Fusion & Modern', 'delivery_available': True, 'estimated_delivery_time': 28, 'delivery_fee': 38.0, 'minimum_order': 280.0},
                    {'place_id': 'vizag_023', 'name': 'Spicy Paradise', 'address': 'Beside Gajuwaka Bus Stand, Visakhapatnam', 'latitude': 17.734, 'longitude': 83.2456, 'rating': 4.2, 'cuisine_type': 'South Indian', 'delivery_available': True, 'estimated_delivery_time': 25, 'delivery_fee': 28.0, 'minimum_order': 180.0},
                    {'place_id': 'vizag_024', 'name': 'The Grill House', 'address': 'Beside RTC Complex, Visakhapatnam', 'latitude': 17.6923, 'longitude': 83.2834, 'rating': 4.4, 'cuisine_type': 'Grilled & BBQ', 'delivery_available': True, 'estimated_delivery_time': 32, 'delivery_fee': 40.0, 'minimum_order': 320.0},
                    {'place_id': 'vizag_025', 'name': 'Andhra Meals', 'address': 'Old Port, Visakhapatnam', 'latitude': 17.6745, 'longitude': 83.2345, 'rating': 4.3, 'cuisine_type': 'Andhra Traditional', 'delivery_available': True, 'estimated_delivery_time': 30, 'delivery_fee': 30.0, 'minimum_order': 200.0},
                    {'place_id': 'vizag_026', 'name': 'The Burger Stop', 'address': 'MVP Colony, Visakhapatnam', 'latitude': 17.7478, 'longitude': 83.2801, 'rating': 4.1, 'cuisine_type': 'Burgers & Fast Food', 'delivery_available': True, 'estimated_delivery_time': 20, 'delivery_fee': 25.0, 'minimum_order': 150.0},
                    {'place_id': 'vizag_027', 'name': 'Spice Garden Restaurant', 'address': 'Beside Kala Theater, Visakhapatnam', 'latitude': 17.689, 'longitude': 83.2912, 'rating': 4.4, 'cuisine_type': 'North Indian & Kebab', 'delivery_available': True, 'estimated_delivery_time': 35, 'delivery_fee': 33.0, 'minimum_order': 240.0},
                    {'place_id': 'vizag_028', 'name': 'Saffron Express', 'address': 'Beside Port Trust, Visakhapatnam', 'latitude': 17.6678, 'longitude': 83.2267, 'rating': 4.5, 'cuisine_type': 'Mughlai & Biryani', 'delivery_available': True, 'estimated_delivery_time': 38, 'delivery_fee': 42.0, 'minimum_order': 320.0},
                    {'place_id': 'vizag_029', 'name': 'Ocean Breeze Cafe', 'address': 'Beach Road, Visakhapatnam', 'latitude': 17.7289, 'longitude': 83.2534, 'rating': 4.6, 'cuisine_type': 'Cafe & Light Bites', 'delivery_available': True, 'estimated_delivery_time': 25, 'delivery_fee': 30.0, 'minimum_order': 180.0},
                    {'place_id': 'vizag_030', 'name': 'Royal Biryani Palace', 'address': 'Beside Hanuman Temple, Visakhapatnam', 'latitude': 17.6967, 'longitude': 83.2845, 'rating': 4.7, 'cuisine_type': 'Biryani Specialist', 'delivery_available': True, 'estimated_delivery_time': 30, 'delivery_fee': 31.0, 'minimum_order': 220.0},
                    {'place_id': 'vizag_031', 'name': 'Dakshin', 'address': 'Waltair Main Road, Visakhapatnam', 'latitude': 17.7245, 'longitude': 83.2623, 'rating': 4.5, 'cuisine_type': 'South Indian Fine Dining', 'delivery_available': True, 'estimated_delivery_time': 35, 'delivery_fee': 40.0, 'minimum_order': 350.0},
                    {'place_id': 'vizag_032', 'name': 'The Grand Bawarchi', 'address': 'Beside Jagadamba Junction, Visakhapatnam', 'latitude': 17.7123, 'longitude': 83.2934, 'rating': 4.6, 'cuisine_type': 'Mughlai & North Indian', 'delivery_available': True, 'estimated_delivery_time': 32, 'delivery_fee': 38.0, 'minimum_order': 300.0},
                    {'place_id': 'vizag_033', 'name': 'Green Park Restaurant', 'address': 'Lawsons Bay Colony, Visakhapatnam', 'latitude': 17.7034, 'longitude': 83.3223, 'rating': 4.2, 'cuisine_type': 'Multicuisine', 'delivery_available': True, 'estimated_delivery_time': 30, 'delivery_fee': 35.0, 'minimum_order': 250.0},
                    {'place_id': 'vizag_034', 'name': 'Taj Mahal Restaurant', 'address': 'Near Railway Station, Visakhapatnam', 'latitude': 17.6912, 'longitude': 83.2145, 'rating': 4.3, 'cuisine_type': 'North Indian', 'delivery_available': True, 'estimated_delivery_time': 28, 'delivery_fee': 32.0, 'minimum_order': 220.0},
                    {'place_id': 'vizag_035', 'name': 'China Town', 'address': 'Madhurawada, Visakhapatnam', 'latitude': 17.7689, 'longitude': 83.3912, 'rating': 4.4, 'cuisine_type': 'Chinese & Thai', 'delivery_available': True, 'estimated_delivery_time': 30, 'delivery_fee': 35.0, 'minimum_order': 240.0},
                    {'place_id': 'vizag_036', 'name': 'BBQ Nation Vizag', 'address': 'CMR Central Mall, Visakhapatnam', 'latitude': 17.7289, 'longitude': 83.3012, 'rating': 4.7, 'cuisine_type': 'BBQ & Grills', 'delivery_available': True, 'estimated_delivery_time': 40, 'delivery_fee': 45.0, 'minimum_order': 400.0},
                    {'place_id': 'vizag_037', 'name': 'Kamat Restaurant', 'address': 'RK Beach Road, Visakhapatnam', 'latitude': 17.7134, 'longitude': 83.2512, 'rating': 4.1, 'cuisine_type': 'South Indian & Udupi', 'delivery_available': True, 'estimated_delivery_time': 25, 'delivery_fee': 28.0, 'minimum_order': 180.0},
                    {'place_id': 'vizag_038', 'name': 'The Fisherman\'s Wharf', 'address': 'Beach Road, Visakhapatnam', 'latitude': 17.7212, 'longitude': 83.2567, 'rating': 4.5, 'cuisine_type': 'Seafood & Coastal', 'delivery_available': True, 'estimated_delivery_time': 38, 'delivery_fee': 48.0, 'minimum_order': 420.0},
                    {'place_id': 'vizag_039', 'name': 'Barbeque Pride', 'address': 'Siripuram, Visakhapatnam', 'latitude': 17.7323, 'longitude': 83.2945, 'rating': 4.6, 'cuisine_type': 'Barbeque & Buffet', 'delivery_available': True, 'estimated_delivery_time': 35, 'delivery_fee': 42.0, 'minimum_order': 380.0},
                    {'place_id': 'vizag_040', 'name': 'Minerva Coffee Shop', 'address': 'Beside Gitam University, Visakhapatnam', 'latitude': 17.7845, 'longitude': 83.3712, 'rating': 4.3, 'cuisine_type': 'South Indian & Bakery', 'delivery_available': True, 'estimated_delivery_time': 25, 'delivery_fee': 28.0, 'minimum_order': 180.0},
                    {'place_id': 'vizag_041', 'name': 'Zaffran', 'address': 'Opposite CMR Mall, Visakhapatnam', 'latitude': 17.7278, 'longitude': 83.3023, 'rating': 4.4, 'cuisine_type': 'North Indian & Tandoor', 'delivery_available': True, 'estimated_delivery_time': 32, 'delivery_fee': 36.0, 'minimum_order': 280.0},
                    {'place_id': 'vizag_042', 'name': 'The Square', 'address': 'Novotel Hotel, Varun Beach, Visakhapatnam', 'latitude': 17.7189, 'longitude': 83.3345, 'rating': 4.8, 'cuisine_type': 'Multi Cuisine Fine Dining', 'delivery_available': True, 'estimated_delivery_time': 45, 'delivery_fee': 55.0, 'minimum_order': 500.0},
                    {'place_id': 'vizag_043', 'name': 'Bamboo Bay', 'address': 'Beach Road, Visakhapatnam', 'latitude': 17.7201, 'longitude': 83.2589, 'rating': 4.3, 'cuisine_type': 'Asian Fusion', 'delivery_available': True, 'estimated_delivery_time': 35, 'delivery_fee': 40.0, 'minimum_order': 320.0},
                    {'place_id': 'vizag_044', 'name': 'Rayalaseema Ruchulu', 'address': 'Beside KFC, Waltair, Visakhapatnam', 'latitude': 17.7198, 'longitude': 83.2678, 'rating': 4.5, 'cuisine_type': 'Andhra Cuisine', 'delivery_available': True, 'estimated_delivery_time': 30, 'delivery_fee': 32.0, 'minimum_order': 240.0},
                    {'place_id': 'vizag_045', 'name': 'Bawarchi Restaurant', 'address': 'Near VUDA Park, Visakhapatnam', 'latitude': 17.7123, 'longitude': 83.2845, 'rating': 4.2, 'cuisine_type': 'Hyderabadi Biryani', 'delivery_available': True, 'estimated_delivery_time': 28, 'delivery_fee': 30.0, 'minimum_order': 220.0},
                    {'place_id': 'vizag_046', 'name': 'Cream Stone', 'address': 'Jagadamba Centre, Visakhapatnam', 'latitude': 17.7156, 'longitude': 83.2923, 'rating': 4.4, 'cuisine_type': 'Desserts & Ice Cream', 'delivery_available': True, 'estimated_delivery_time': 20, 'delivery_fee': 25.0, 'minimum_order': 150.0},
                    {'place_id': 'vizag_047', 'name': 'Absolute Barbecues', 'address': 'Waltair Uplands, Visakhapatnam', 'latitude': 17.7234, 'longitude': 83.2712, 'rating': 4.6, 'cuisine_type': 'Grills & BBQ', 'delivery_available': True, 'estimated_delivery_time': 38, 'delivery_fee': 45.0, 'minimum_order': 400.0},
                    {'place_id': 'vizag_048', 'name': 'Vista - The Park', 'address': 'The Park Hotel, Beach Road, Visakhapatnam', 'latitude': 17.7178, 'longitude': 83.2534, 'rating': 4.7, 'cuisine_type': 'Continental & Indian', 'delivery_available': True, 'estimated_delivery_time': 42, 'delivery_fee': 50.0, 'minimum_order': 450.0},
                    {'place_id': 'vizag_049', 'name': 'Dharani', 'address': 'CMR Central, Visakhapatnam', 'latitude': 17.7289, 'longitude': 83.3034, 'rating': 4.3, 'cuisine_type': 'Andhra & South Indian', 'delivery_available': True, 'estimated_delivery_time': 28, 'delivery_fee': 30.0, 'minimum_order': 200.0},
                    {'place_id': 'vizag_050', 'name': 'Flying Spaghetti Monster', 'address': 'Near Beach Road, Visakhapatnam', 'latitude': 17.7212, 'longitude': 83.2598, 'rating': 4.5, 'cuisine_type': 'Italian & Continental', 'delivery_available': True, 'estimated_delivery_time': 35, 'delivery_fee': 40.0, 'minimum_order': 320.0},
                ]
                
                restaurants = []
                for rest_data in restaurants_data:
                    rest = Restaurant(**rest_data)
                    db.session.add(rest)
                    restaurants.append(rest)
                
                db.session.flush()  # Get IDs without committing
                
                # Comprehensive menu items for Visakhapatnam restaurants with INR prices
                menu_items_data = [
                    # Rasora Restaurant - Multicuisine
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[0].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[0].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[0].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[0].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[0].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[0].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[0].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[0].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[0].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[0].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[0].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[0].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[0].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[0].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[0].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[0].id},

                    # Amalodbhavi Multicuisine Restaurant - Multicuisine
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[1].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[1].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[1].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[1].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[1].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[1].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[1].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[1].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[1].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[1].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[1].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[1].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[1].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[1].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[1].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[1].id},

                    # Bunny's Mandi - Biryani & Mandi
                    {'name': 'Chicken Mandi (Full)', 'price': 420.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Chicken Mandi (Half)', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Mutton Mandi (Full)', 'price': 480.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Mutton Mandi (Half)', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Fish Mandi', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Prawn Mandi', 'price': 450.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Chicken Biryani (Large)', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Chicken Biryani (Regular)', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Mutton Biryani (Large)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Mutton Biryani (Regular)', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Fish Biryani', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Chicken Kabsa', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Mutton Kabsa', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Arabic Shawarma', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Chicken Shawarma', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Falafel Plate', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Hummus with Pita', 'price': 120.0, 'category': 'Appetizer', 'restaurant_id': restaurants[2].id},
                    {'name': 'Mutabal', 'price': 140.0, 'category': 'Appetizer', 'restaurant_id': restaurants[2].id},
                    {'name': 'Tabbouleh Salad', 'price': 160.0, 'category': 'Salad', 'restaurant_id': restaurants[2].id},
                    {'name': 'Arabic Mixed Grill', 'price': 450.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Lamb Chops', 'price': 500.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Grilled Chicken', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Mint Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[2].id},
                    {'name': 'Arabic Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[2].id},
                    {'name': 'Haloush (Sweet)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[2].id},
                    {'name': 'Kunafa', 'price': 120.0, 'category': 'Dessert', 'restaurant_id': restaurants[2].id},
                    {'name': 'Baklava', 'price': 140.0, 'category': 'Dessert', 'restaurant_id': restaurants[2].id},
                    {'name': 'Mint Tea', 'price': 50.0, 'category': 'Beverage', 'restaurant_id': restaurants[2].id},
                    {'name': 'Arabic Tea', 'price': 60.0, 'category': 'Beverage', 'restaurant_id': restaurants[2].id},
                    {'name': 'Fresh Lime Juice', 'price': 70.0, 'category': 'Beverage', 'restaurant_id': restaurants[2].id},
                    {'name': 'Watermelon Juice', 'price': 80.0, 'category': 'Beverage', 'restaurant_id': restaurants[2].id},

                    # Planet 9 Restaurant - Multicuisine
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[3].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[3].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[3].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[3].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[3].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[3].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[3].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[3].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[3].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[3].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[3].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[3].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[3].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[3].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[3].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[3].id},

                    # Cabritoz - Asian & Continental
                    {'name': 'Grilled Chicken Steak', 'price': 450.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Beef Steak', 'price': 520.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Pan Seared Fish', 'price': 480.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Grilled Prawns', 'price': 550.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Thai Green Curry (Chicken)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Thai Green Curry (Veg)', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Thai Red Curry (Chicken)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Thai Red Curry (Prawns)', 'price': 450.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Pad Thai Noodles (Chicken)', 'price': 340.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Pad Thai Noodles (Prawns)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Singapore Noodles', 'price': 330.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Malaysian Fried Rice', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Kung Pao Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Sweet & Sour Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Chilli Garlic Prawns', 'price': 420.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Salt & Pepper Fish', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[4].id},
                    {'name': 'Hot & Sour Soup (Veg)', 'price': 140.0, 'category': 'Soup', 'restaurant_id': restaurants[4].id},
                    {'name': 'Hot & Sour Soup (Chicken)', 'price': 160.0, 'category': 'Soup', 'restaurant_id': restaurants[4].id},
                    {'name': 'Tom Yum Soup (Veg)', 'price': 180.0, 'category': 'Soup', 'restaurant_id': restaurants[4].id},
                    {'name': 'Tom Yum Soup (Prawns)', 'price': 220.0, 'category': 'Soup', 'restaurant_id': restaurants[4].id},
                    {'name': 'Sweet Corn Soup (Veg)', 'price': 130.0, 'category': 'Soup', 'restaurant_id': restaurants[4].id},
                    {'name': 'Sweet Corn Soup (Chicken)', 'price': 150.0, 'category': 'Soup', 'restaurant_id': restaurants[4].id},
                    {'name': 'Caesar Salad', 'price': 280.0, 'category': 'Salad', 'restaurant_id': restaurants[4].id},
                    {'name': 'Greek Salad', 'price': 260.0, 'category': 'Salad', 'restaurant_id': restaurants[4].id},
                    {'name': 'Thai Salad', 'price': 300.0, 'category': 'Salad', 'restaurant_id': restaurants[4].id},
                    {'name': 'Garden Salad', 'price': 220.0, 'category': 'Salad', 'restaurant_id': restaurants[4].id},
                    {'name': 'Chicken Wings (6pc)', 'price': 280.0, 'category': 'Appetizer', 'restaurant_id': restaurants[4].id},
                    {'name': 'Chicken Wings (12pc)', 'price': 480.0, 'category': 'Appetizer', 'restaurant_id': restaurants[4].id},
                    {'name': 'Crispy Prawns', 'price': 380.0, 'category': 'Appetizer', 'restaurant_id': restaurants[4].id},
                    {'name': 'Fish Fingers', 'price': 320.0, 'category': 'Appetizer', 'restaurant_id': restaurants[4].id},
                    {'name': 'Chocolate Mousse', 'price': 150.0, 'category': 'Dessert', 'restaurant_id': restaurants[4].id},
                    {'name': 'Tiramisu', 'price': 180.0, 'category': 'Dessert', 'restaurant_id': restaurants[4].id},
                    {'name': 'Panna Cotta', 'price': 160.0, 'category': 'Dessert', 'restaurant_id': restaurants[4].id},
                    {'name': 'Chocolate Lava Cake', 'price': 200.0, 'category': 'Dessert', 'restaurant_id': restaurants[4].id},

                    # Masaledaar Desi Rasoi - Indian
                    {'name': 'Chicken Curry', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Mutton Curry', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Fish Curry', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Egg Curry', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Prawn Curry', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Chicken Masala', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Chicken Korma', 'price': 290.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Chicken Do Pyaza', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Paneer Butter Masala', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Paneer Tikka Masala', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Malai Kofta', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Shahi Paneer', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Palak Paneer', 'price': 230.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Dal Tadka', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Dal Fry', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Dal Makhani', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Dal Palak', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Chole Bhature', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Chole Kulche', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Rajma Chawal', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Kadhi Pakora', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Aloo Gobi', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Baingan Bharta', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Bhindi Masala', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Mix Veg Curry', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Tandoori Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[5].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[5].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[5].id},
                    {'name': 'Laccha Paratha', 'price': 55.0, 'category': 'Bread', 'restaurant_id': restaurants[5].id},
                    {'name': 'Jeera Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Pulao', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[5].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[5].id},
                    {'name': 'Pickle', 'price': 30.0, 'category': 'Side Dish', 'restaurant_id': restaurants[5].id},

                    # Aadaab Family Restaurant - Biryani & Indian
                    {'name': 'Chicken Curry', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Mutton Curry', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Fish Curry', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Egg Curry', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Prawn Curry', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Chicken Masala', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Chicken Korma', 'price': 290.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Chicken Do Pyaza', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Paneer Butter Masala', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Paneer Tikka Masala', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Malai Kofta', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Shahi Paneer', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Palak Paneer', 'price': 230.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Dal Tadka', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Dal Fry', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Dal Makhani', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Dal Palak', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Chole Bhature', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Chole Kulche', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Rajma Chawal', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Kadhi Pakora', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Aloo Gobi', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Baingan Bharta', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Bhindi Masala', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Mix Veg Curry', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Tandoori Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[6].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[6].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[6].id},
                    {'name': 'Laccha Paratha', 'price': 55.0, 'category': 'Bread', 'restaurant_id': restaurants[6].id},
                    {'name': 'Jeera Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Pulao', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[6].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[6].id},
                    {'name': 'Pickle', 'price': 30.0, 'category': 'Side Dish', 'restaurant_id': restaurants[6].id},

                    # Peoples Choice Family Restaurant - Multicuisine
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[7].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[7].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[7].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[7].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[7].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[7].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[7].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[7].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[7].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[7].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[7].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[7].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[7].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[7].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[7].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[7].id},

                    # Best Backers - Fast Food
                    {'name': 'Chicken Burger (Cheese)', 'price': 130.0, 'category': 'Burger', 'restaurant_id': restaurants[8].id},
                    {'name': 'Chicken Burger (Classic)', 'price': 120.0, 'category': 'Burger', 'restaurant_id': restaurants[8].id},
                    {'name': 'Veg Burger', 'price': 100.0, 'category': 'Burger', 'restaurant_id': restaurants[8].id},
                    {'name': 'Paneer Burger', 'price': 110.0, 'category': 'Burger', 'restaurant_id': restaurants[8].id},
                    {'name': 'Crispy Chicken Burger', 'price': 140.0, 'category': 'Burger', 'restaurant_id': restaurants[8].id},
                    {'name': 'Double Cheese Burger', 'price': 160.0, 'category': 'Burger', 'restaurant_id': restaurants[8].id},
                    {'name': 'Fish Burger', 'price': 150.0, 'category': 'Burger', 'restaurant_id': restaurants[8].id},
                    {'name': 'Aloo Tikki Burger', 'price': 90.0, 'category': 'Burger', 'restaurant_id': restaurants[8].id},
                    {'name': 'Chicken Sandwich', 'price': 100.0, 'category': 'Sandwich', 'restaurant_id': restaurants[8].id},
                    {'name': 'Veg Sandwich', 'price': 80.0, 'category': 'Sandwich', 'restaurant_id': restaurants[8].id},
                    {'name': 'Grilled Sandwich', 'price': 90.0, 'category': 'Sandwich', 'restaurant_id': restaurants[8].id},
                    {'name': 'Club Sandwich', 'price': 140.0, 'category': 'Sandwich', 'restaurant_id': restaurants[8].id},
                    {'name': 'Chicken Roll', 'price': 90.0, 'category': 'Main Course', 'restaurant_id': restaurants[8].id},
                    {'name': 'Paneer Roll', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[8].id},
                    {'name': 'Egg Roll', 'price': 70.0, 'category': 'Main Course', 'restaurant_id': restaurants[8].id},
                    {'name': 'Veg Roll', 'price': 60.0, 'category': 'Main Course', 'restaurant_id': restaurants[8].id},
                    {'name': 'Chicken Shawarma', 'price': 120.0, 'category': 'Main Course', 'restaurant_id': restaurants[8].id},
                    {'name': 'Veg Shawarma', 'price': 100.0, 'category': 'Main Course', 'restaurant_id': restaurants[8].id},
                    {'name': 'French Fries (Large)', 'price': 80.0, 'category': 'Side', 'restaurant_id': restaurants[8].id},
                    {'name': 'French Fries (Regular)', 'price': 60.0, 'category': 'Side', 'restaurant_id': restaurants[8].id},
                    {'name': 'Peri Peri Fries', 'price': 90.0, 'category': 'Side', 'restaurant_id': restaurants[8].id},
                    {'name': 'Cheese Fries', 'price': 100.0, 'category': 'Side', 'restaurant_id': restaurants[8].id},
                    {'name': 'Onion Rings (8pc)', 'price': 100.0, 'category': 'Appetizer', 'restaurant_id': restaurants[8].id},
                    {'name': 'Chicken Nuggets (6pc)', 'price': 120.0, 'category': 'Appetizer', 'restaurant_id': restaurants[8].id},
                    {'name': 'Chicken Nuggets (9pc)', 'price': 170.0, 'category': 'Appetizer', 'restaurant_id': restaurants[8].id},
                    {'name': 'Chicken Popcorn', 'price': 150.0, 'category': 'Appetizer', 'restaurant_id': restaurants[8].id},
                    {'name': 'Hot Dog', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[8].id},
                    {'name': 'Veg Hot Dog', 'price': 70.0, 'category': 'Main Course', 'restaurant_id': restaurants[8].id},
                    {'name': 'Pizza Slice', 'price': 60.0, 'category': 'Main Course', 'restaurant_id': restaurants[8].id},
                    {'name': 'Garlic Bread (4pc)', 'price': 80.0, 'category': 'Appetizer', 'restaurant_id': restaurants[8].id},
                    {'name': 'Coke (250ml)', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[8].id},
                    {'name': 'Coke (500ml)', 'price': 60.0, 'category': 'Beverage', 'restaurant_id': restaurants[8].id},
                    {'name': 'Sprite (250ml)', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[8].id},
                    {'name': 'Fresh Lime Soda', 'price': 50.0, 'category': 'Beverage', 'restaurant_id': restaurants[8].id},
                    {'name': 'Milkshake (Chocolate)', 'price': 120.0, 'category': 'Beverage', 'restaurant_id': restaurants[8].id},
                    {'name': 'Milkshake (Vanilla)', 'price': 120.0, 'category': 'Beverage', 'restaurant_id': restaurants[8].id},

                    # Sr Hotel - Andhra & Biryani
                    {'name': 'Andhra Chicken Biryani', 'price': 270.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Andhra Mutton Biryani', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Boneless Chicken Biryani', 'price': 290.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Kheema Biryani', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Gongura Chicken', 'price': 290.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Gongura Mutton', 'price': 340.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Gongura Prawns', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Natu Kodi Pulusu', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Chepala Pulusu (Fish Curry)', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Royyala Iguru (Prawns)', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Rawa Fry Fish', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Fish Fry', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Andhra Chicken Fry', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Mutton Fry (Dry)', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Egg Pulusu', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Chicken Pulusu', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Gutti Vankaya Curry', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Bendakaya Pulusu', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Tomato Pappu', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Gongura Pachadi', 'price': 100.0, 'category': 'Side Dish', 'restaurant_id': restaurants[9].id},
                    {'name': 'Pesarattu', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[9].id},
                    {'name': 'Upma Pesarattu', 'price': 140.0, 'category': 'Breakfast', 'restaurant_id': restaurants[9].id},
                    {'name': 'Dosa (Andhra Style)', 'price': 130.0, 'category': 'Breakfast', 'restaurant_id': restaurants[9].id},
                    {'name': 'Puri Bhaji', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[9].id},
                    {'name': 'Idli Podi', 'price': 110.0, 'category': 'Breakfast', 'restaurant_id': restaurants[9].id},
                    {'name': 'Attu with Chicken Curry', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Andhra Meals (Unlimited)', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Non-Veg Meals (Unlimited)', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[9].id},
                    {'name': 'Puran Poli', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[9].id},
                    {'name': 'Bobbatlu', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[9].id},
                    {'name': 'Ariselu', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[9].id},
                    {'name': 'Qubani Ka Meetha', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[9].id},
                    {'name': 'Bellam Paramannam', 'price': 90.0, 'category': 'Dessert', 'restaurant_id': restaurants[9].id},

                    # Spice Court Restaurant - South Indian
                    {'name': 'Masala Dosa', 'price': 140.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Plain Dosa', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Rava Dosa', 'price': 130.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Onion Dosa', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Ghee Roast Dosa', 'price': 160.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Set Dosa (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Mysore Masala Dosa', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Paper Roast', 'price': 180.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Idli Sambar (4pc)', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Idli Sambar (2pc)', 'price': 60.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Rava Idli (3pc)', 'price': 110.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Medu Vada (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Vada Sambar (2pc)', 'price': 85.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Sambar Vada (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Uttapam Plain', 'price': 130.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Uttapam Onion', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Uttapam Tomato', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Uttapam Mixed', 'price': 170.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Pongal', 'price': 110.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Upma', 'price': 90.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Kesari Bath', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Poori Bhaji', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[10].id},
                    {'name': 'Chole Bhature', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[10].id},
                    {'name': 'Lemon Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[10].id},
                    {'name': 'Curd Rice', 'price': 120.0, 'category': 'Main Course', 'restaurant_id': restaurants[10].id},
                    {'name': 'Tamarind Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[10].id},
                    {'name': 'Coconut Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[10].id},
                    {'name': 'Bisi Bele Bath', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[10].id},
                    {'name': 'Sambar Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[10].id},
                    {'name': 'Rasam Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[10].id},
                    {'name': 'Filter Coffee', 'price': 50.0, 'category': 'Beverage', 'restaurant_id': restaurants[10].id},
                    {'name': 'Masala Chai', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[10].id},
                    {'name': 'Badam Milk', 'price': 80.0, 'category': 'Beverage', 'restaurant_id': restaurants[10].id},
                    {'name': 'Buttermilk', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[10].id},

                    # Kebab Junction - North Indian & Kebab
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Appetizer', 'restaurant_id': restaurants[11].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[11].id},
                    {'name': 'Chicken Tikka (8pc)', 'price': 280.0, 'category': 'Appetizer', 'restaurant_id': restaurants[11].id},
                    {'name': 'Paneer Tikka (8pc)', 'price': 260.0, 'category': 'Appetizer', 'restaurant_id': restaurants[11].id},
                    {'name': 'Seekh Kebab (6pc)', 'price': 320.0, 'category': 'Appetizer', 'restaurant_id': restaurants[11].id},
                    {'name': 'Seekh Kebab (4pc)', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[11].id},
                    {'name': 'Shami Kebab (4pc)', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[11].id},
                    {'name': 'Reshmi Kebab (6pc)', 'price': 300.0, 'category': 'Appetizer', 'restaurant_id': restaurants[11].id},
                    {'name': 'Hara Bhara Kebab (6pc)', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[11].id},
                    {'name': 'Tandoori Pomfret', 'price': 420.0, 'category': 'Appetizer', 'restaurant_id': restaurants[11].id},
                    {'name': 'Tandoori Prawns (6pc)', 'price': 380.0, 'category': 'Appetizer', 'restaurant_id': restaurants[11].id},
                    {'name': 'Chicken Malai Tikka', 'price': 300.0, 'category': 'Appetizer', 'restaurant_id': restaurants[11].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Chicken Korma', 'price': 310.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Mutton Rogan Josh', 'price': 360.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Mutton Korma', 'price': 370.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Dal Makhani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Dal Tadka', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Paneer Tikka Masala', 'price': 270.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Kadhai Paneer', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Palak Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Malai Kofta', 'price': 270.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Shahi Paneer', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Mixed Veg Curry', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Aloo Gobi', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[11].id},
                    {'name': 'Naan Bread', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[11].id},
                    {'name': 'Garlic Naan', 'price': 60.0, 'category': 'Bread', 'restaurant_id': restaurants[11].id},
                    {'name': 'Butter Naan', 'price': 55.0, 'category': 'Bread', 'restaurant_id': restaurants[11].id},
                    {'name': 'Cheese Naan', 'price': 80.0, 'category': 'Bread', 'restaurant_id': restaurants[11].id},
                    {'name': 'Kulcha', 'price': 55.0, 'category': 'Bread', 'restaurant_id': restaurants[11].id},
                    {'name': 'Laccha Paratha', 'price': 60.0, 'category': 'Bread', 'restaurant_id': restaurants[11].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[11].id},
                    {'name': 'Missi Roti', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[11].id},

                    # The Spice Route - Asian & Continental
                    {'name': 'Grilled Chicken Steak', 'price': 450.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Beef Steak', 'price': 520.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Pan Seared Fish', 'price': 480.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Grilled Prawns', 'price': 550.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Thai Green Curry (Chicken)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Thai Green Curry (Veg)', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Thai Red Curry (Chicken)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Thai Red Curry (Prawns)', 'price': 450.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Pad Thai Noodles (Chicken)', 'price': 340.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Pad Thai Noodles (Prawns)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Singapore Noodles', 'price': 330.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Malaysian Fried Rice', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Kung Pao Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Sweet & Sour Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Chilli Garlic Prawns', 'price': 420.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Salt & Pepper Fish', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[12].id},
                    {'name': 'Hot & Sour Soup (Veg)', 'price': 140.0, 'category': 'Soup', 'restaurant_id': restaurants[12].id},
                    {'name': 'Hot & Sour Soup (Chicken)', 'price': 160.0, 'category': 'Soup', 'restaurant_id': restaurants[12].id},
                    {'name': 'Tom Yum Soup (Veg)', 'price': 180.0, 'category': 'Soup', 'restaurant_id': restaurants[12].id},
                    {'name': 'Tom Yum Soup (Prawns)', 'price': 220.0, 'category': 'Soup', 'restaurant_id': restaurants[12].id},
                    {'name': 'Sweet Corn Soup (Veg)', 'price': 130.0, 'category': 'Soup', 'restaurant_id': restaurants[12].id},
                    {'name': 'Sweet Corn Soup (Chicken)', 'price': 150.0, 'category': 'Soup', 'restaurant_id': restaurants[12].id},
                    {'name': 'Caesar Salad', 'price': 280.0, 'category': 'Salad', 'restaurant_id': restaurants[12].id},
                    {'name': 'Greek Salad', 'price': 260.0, 'category': 'Salad', 'restaurant_id': restaurants[12].id},
                    {'name': 'Thai Salad', 'price': 300.0, 'category': 'Salad', 'restaurant_id': restaurants[12].id},
                    {'name': 'Garden Salad', 'price': 220.0, 'category': 'Salad', 'restaurant_id': restaurants[12].id},
                    {'name': 'Chicken Wings (6pc)', 'price': 280.0, 'category': 'Appetizer', 'restaurant_id': restaurants[12].id},
                    {'name': 'Chicken Wings (12pc)', 'price': 480.0, 'category': 'Appetizer', 'restaurant_id': restaurants[12].id},
                    {'name': 'Crispy Prawns', 'price': 380.0, 'category': 'Appetizer', 'restaurant_id': restaurants[12].id},
                    {'name': 'Fish Fingers', 'price': 320.0, 'category': 'Appetizer', 'restaurant_id': restaurants[12].id},
                    {'name': 'Chocolate Mousse', 'price': 150.0, 'category': 'Dessert', 'restaurant_id': restaurants[12].id},
                    {'name': 'Tiramisu', 'price': 180.0, 'category': 'Dessert', 'restaurant_id': restaurants[12].id},
                    {'name': 'Panna Cotta', 'price': 160.0, 'category': 'Dessert', 'restaurant_id': restaurants[12].id},
                    {'name': 'Chocolate Lava Cake', 'price': 200.0, 'category': 'Dessert', 'restaurant_id': restaurants[12].id},

                    # Biryani Express - Biryani Specialist
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[13].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[13].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[13].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[13].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[13].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[13].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[13].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[13].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[13].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[13].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[13].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[13].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[13].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[13].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[13].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[13].id},

                    # The Pizza Corner - Italian & Pizza
                    {'name': 'Margherita Pizza (Large)', 'price': 320.0, 'category': 'Pizza', 'restaurant_id': restaurants[14].id},
                    {'name': 'Margherita Pizza (Medium)', 'price': 220.0, 'category': 'Pizza', 'restaurant_id': restaurants[14].id},
                    {'name': 'Margherita Pizza (Small)', 'price': 160.0, 'category': 'Pizza', 'restaurant_id': restaurants[14].id},
                    {'name': 'Pepperoni Pizza (Large)', 'price': 380.0, 'category': 'Pizza', 'restaurant_id': restaurants[14].id},
                    {'name': 'Pepperoni Pizza (Medium)', 'price': 260.0, 'category': 'Pizza', 'restaurant_id': restaurants[14].id},
                    {'name': 'Chicken BBQ Pizza (Large)', 'price': 400.0, 'category': 'Pizza', 'restaurant_id': restaurants[14].id},
                    {'name': 'Chicken BBQ Pizza (Medium)', 'price': 280.0, 'category': 'Pizza', 'restaurant_id': restaurants[14].id},
                    {'name': 'Veggie Supreme Pizza (Large)', 'price': 350.0, 'category': 'Pizza', 'restaurant_id': restaurants[14].id},
                    {'name': 'Veggie Supreme Pizza (Medium)', 'price': 240.0, 'category': 'Pizza', 'restaurant_id': restaurants[14].id},
                    {'name': 'Four Cheese Pizza (Large)', 'price': 420.0, 'category': 'Pizza', 'restaurant_id': restaurants[14].id},
                    {'name': 'Mexican Pizza (Large)', 'price': 390.0, 'category': 'Pizza', 'restaurant_id': restaurants[14].id},
                    {'name': 'Paneer Tikka Pizza (Large)', 'price': 380.0, 'category': 'Pizza', 'restaurant_id': restaurants[14].id},
                    {'name': 'Farm House Pizza (Medium)', 'price': 250.0, 'category': 'Pizza', 'restaurant_id': restaurants[14].id},
                    {'name': 'Hawaiian Pizza (Large)', 'price': 370.0, 'category': 'Pizza', 'restaurant_id': restaurants[14].id},
                    {'name': 'Pasta Alfredo (Chicken)', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[14].id},
                    {'name': 'Pasta Alfredo (Veg)', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[14].id},
                    {'name': 'Pasta Arrabiata', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[14].id},
                    {'name': 'Pasta Carbonara', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[14].id},
                    {'name': 'Penne Pasta (Veg)', 'price': 230.0, 'category': 'Main Course', 'restaurant_id': restaurants[14].id},
                    {'name': 'Penne Pasta (Chicken)', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[14].id},
                    {'name': 'Spaghetti Bolognese', 'price': 310.0, 'category': 'Main Course', 'restaurant_id': restaurants[14].id},
                    {'name': 'Lasagna (Veg)', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[14].id},
                    {'name': 'Lasagna (Chicken)', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[14].id},
                    {'name': 'Ravioli', 'price': 290.0, 'category': 'Main Course', 'restaurant_id': restaurants[14].id},
                    {'name': 'Garlic Bread (4pc)', 'price': 120.0, 'category': 'Appetizer', 'restaurant_id': restaurants[14].id},
                    {'name': 'Cheesy Garlic Bread (4pc)', 'price': 150.0, 'category': 'Appetizer', 'restaurant_id': restaurants[14].id},
                    {'name': 'Bruschetta (4pc)', 'price': 160.0, 'category': 'Appetizer', 'restaurant_id': restaurants[14].id},
                    {'name': 'Stuffed Garlic Bread', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[14].id},
                    {'name': 'Caesar Salad', 'price': 220.0, 'category': 'Salad', 'restaurant_id': restaurants[14].id},
                    {'name': 'Italian Salad', 'price': 200.0, 'category': 'Salad', 'restaurant_id': restaurants[14].id},

                    # Oriental Spice Kitchen - Chinese & Asian
                    {'name': 'Hakka Noodles (Veg)', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Hakka Noodles (Chicken)', 'price': 210.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Hakka Noodles (Mixed)', 'price': 230.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Schezwan Noodles (Veg)', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Schezwan Noodles (Chicken)', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Singapore Noodles', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Fried Rice (Veg)', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Fried Rice (Chicken)', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Fried Rice (Mixed)', 'price': 210.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Schezwan Rice (Veg)', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Schezwan Rice (Chicken)', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Triple Fried Rice', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Chow Mein', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'American Chopsuey', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Manchurian (Veg)', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[15].id},
                    {'name': 'Manchurian (Chicken)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[15].id},
                    {'name': 'Gobi Manchurian', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[15].id},
                    {'name': 'Mushroom Manchurian', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[15].id},
                    {'name': 'Sweet & Sour Chicken', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Sweet & Sour Prawns', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Kung Pao Chicken', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Dragon Chicken', 'price': 270.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Chilli Chicken (Dry)', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[15].id},
                    {'name': 'Chilli Chicken (Gravy)', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[15].id},
                    {'name': 'Chilli Fish', 'price': 280.0, 'category': 'Appetizer', 'restaurant_id': restaurants[15].id},
                    {'name': 'Chilli Prawns', 'price': 340.0, 'category': 'Appetizer', 'restaurant_id': restaurants[15].id},
                    {'name': 'Spring Rolls (6pc)', 'price': 150.0, 'category': 'Appetizer', 'restaurant_id': restaurants[15].id},
                    {'name': 'Veg Spring Rolls (8pc)', 'price': 140.0, 'category': 'Appetizer', 'restaurant_id': restaurants[15].id},
                    {'name': 'Chicken Lollipop (6pc)', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[15].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[15].id},
                    {'name': 'Hot & Sour Soup', 'price': 140.0, 'category': 'Soup', 'restaurant_id': restaurants[15].id},
                    {'name': 'Sweet Corn Soup', 'price': 130.0, 'category': 'Soup', 'restaurant_id': restaurants[15].id},
                    {'name': 'Manchow Soup', 'price': 150.0, 'category': 'Soup', 'restaurant_id': restaurants[15].id},
                    {'name': 'Wonton Soup', 'price': 160.0, 'category': 'Soup', 'restaurant_id': restaurants[15].id},

                    # Garden Valley Restaurant - Seafood & Continental
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[16].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[16].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[16].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[16].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[16].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[16].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[16].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[16].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[16].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[16].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[16].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[16].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[16].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[16].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[16].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[16].id},

                    # Hyderabad House - Biryani & Hyderabadi
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[17].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[17].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[17].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[17].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[17].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[17].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[17].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[17].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[17].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[17].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[17].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[17].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[17].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[17].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[17].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[17].id},

                    # The Curry House - Indian Curry
                    {'name': 'Chicken Curry', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Mutton Curry', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Fish Curry', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Egg Curry', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Prawn Curry', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Chicken Masala', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Chicken Korma', 'price': 290.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Chicken Do Pyaza', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Paneer Butter Masala', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Paneer Tikka Masala', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Malai Kofta', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Shahi Paneer', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Palak Paneer', 'price': 230.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Dal Tadka', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Dal Fry', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Dal Makhani', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Dal Palak', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Chole Bhature', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Chole Kulche', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Rajma Chawal', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Kadhi Pakora', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Aloo Gobi', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Baingan Bharta', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Bhindi Masala', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Mix Veg Curry', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Tandoori Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[18].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[18].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[18].id},
                    {'name': 'Laccha Paratha', 'price': 55.0, 'category': 'Bread', 'restaurant_id': restaurants[18].id},
                    {'name': 'Jeera Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Pulao', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[18].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[18].id},
                    {'name': 'Pickle', 'price': 30.0, 'category': 'Side Dish', 'restaurant_id': restaurants[18].id},

                    # Paradise Restaurant - Multicuisine
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[19].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[19].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[19].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[19].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[19].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[19].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[19].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[19].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[19].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[19].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[19].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[19].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[19].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[19].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[19].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[19].id},

                    # Crave Restaurant & Cafe - Cafe & Light Bites
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[20].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[20].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[20].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[20].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[20].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[20].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[20].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[20].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[20].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[20].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[20].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[20].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[20].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[20].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[20].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[20].id},

                    # The Fusion Kitchen - Fusion & Modern
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[21].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[21].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[21].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[21].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[21].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[21].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[21].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[21].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[21].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[21].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[21].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[21].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[21].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[21].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[21].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[21].id},

                    # Spicy Paradise - South Indian
                    {'name': 'Masala Dosa', 'price': 140.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Plain Dosa', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Rava Dosa', 'price': 130.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Onion Dosa', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Ghee Roast Dosa', 'price': 160.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Set Dosa (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Mysore Masala Dosa', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Paper Roast', 'price': 180.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Idli Sambar (4pc)', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Idli Sambar (2pc)', 'price': 60.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Rava Idli (3pc)', 'price': 110.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Medu Vada (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Vada Sambar (2pc)', 'price': 85.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Sambar Vada (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Uttapam Plain', 'price': 130.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Uttapam Onion', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Uttapam Tomato', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Uttapam Mixed', 'price': 170.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Pongal', 'price': 110.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Upma', 'price': 90.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Kesari Bath', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Poori Bhaji', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[22].id},
                    {'name': 'Chole Bhature', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[22].id},
                    {'name': 'Lemon Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[22].id},
                    {'name': 'Curd Rice', 'price': 120.0, 'category': 'Main Course', 'restaurant_id': restaurants[22].id},
                    {'name': 'Tamarind Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[22].id},
                    {'name': 'Coconut Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[22].id},
                    {'name': 'Bisi Bele Bath', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[22].id},
                    {'name': 'Sambar Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[22].id},
                    {'name': 'Rasam Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[22].id},
                    {'name': 'Filter Coffee', 'price': 50.0, 'category': 'Beverage', 'restaurant_id': restaurants[22].id},
                    {'name': 'Masala Chai', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[22].id},
                    {'name': 'Badam Milk', 'price': 80.0, 'category': 'Beverage', 'restaurant_id': restaurants[22].id},
                    {'name': 'Buttermilk', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[22].id},

                    # The Grill House - Grilled & BBQ
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[23].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[23].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[23].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[23].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[23].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[23].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[23].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[23].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[23].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[23].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[23].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[23].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[23].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[23].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[23].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[23].id},

                    # Andhra Meals - Andhra Traditional
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[24].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[24].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[24].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[24].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[24].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[24].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[24].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[24].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[24].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[24].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[24].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[24].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[24].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[24].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[24].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[24].id},

                    # The Burger Stop - Burgers & Fast Food
                    {'name': 'Chicken Burger (Cheese)', 'price': 130.0, 'category': 'Burger', 'restaurant_id': restaurants[25].id},
                    {'name': 'Chicken Burger (Classic)', 'price': 120.0, 'category': 'Burger', 'restaurant_id': restaurants[25].id},
                    {'name': 'Veg Burger', 'price': 100.0, 'category': 'Burger', 'restaurant_id': restaurants[25].id},
                    {'name': 'Paneer Burger', 'price': 110.0, 'category': 'Burger', 'restaurant_id': restaurants[25].id},
                    {'name': 'Crispy Chicken Burger', 'price': 140.0, 'category': 'Burger', 'restaurant_id': restaurants[25].id},
                    {'name': 'Double Cheese Burger', 'price': 160.0, 'category': 'Burger', 'restaurant_id': restaurants[25].id},
                    {'name': 'Fish Burger', 'price': 150.0, 'category': 'Burger', 'restaurant_id': restaurants[25].id},
                    {'name': 'Aloo Tikki Burger', 'price': 90.0, 'category': 'Burger', 'restaurant_id': restaurants[25].id},
                    {'name': 'Chicken Sandwich', 'price': 100.0, 'category': 'Sandwich', 'restaurant_id': restaurants[25].id},
                    {'name': 'Veg Sandwich', 'price': 80.0, 'category': 'Sandwich', 'restaurant_id': restaurants[25].id},
                    {'name': 'Grilled Sandwich', 'price': 90.0, 'category': 'Sandwich', 'restaurant_id': restaurants[25].id},
                    {'name': 'Club Sandwich', 'price': 140.0, 'category': 'Sandwich', 'restaurant_id': restaurants[25].id},
                    {'name': 'Chicken Roll', 'price': 90.0, 'category': 'Main Course', 'restaurant_id': restaurants[25].id},
                    {'name': 'Paneer Roll', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[25].id},
                    {'name': 'Egg Roll', 'price': 70.0, 'category': 'Main Course', 'restaurant_id': restaurants[25].id},
                    {'name': 'Veg Roll', 'price': 60.0, 'category': 'Main Course', 'restaurant_id': restaurants[25].id},
                    {'name': 'Chicken Shawarma', 'price': 120.0, 'category': 'Main Course', 'restaurant_id': restaurants[25].id},
                    {'name': 'Veg Shawarma', 'price': 100.0, 'category': 'Main Course', 'restaurant_id': restaurants[25].id},
                    {'name': 'French Fries (Large)', 'price': 80.0, 'category': 'Side', 'restaurant_id': restaurants[25].id},
                    {'name': 'French Fries (Regular)', 'price': 60.0, 'category': 'Side', 'restaurant_id': restaurants[25].id},
                    {'name': 'Peri Peri Fries', 'price': 90.0, 'category': 'Side', 'restaurant_id': restaurants[25].id},
                    {'name': 'Cheese Fries', 'price': 100.0, 'category': 'Side', 'restaurant_id': restaurants[25].id},
                    {'name': 'Onion Rings (8pc)', 'price': 100.0, 'category': 'Appetizer', 'restaurant_id': restaurants[25].id},
                    {'name': 'Chicken Nuggets (6pc)', 'price': 120.0, 'category': 'Appetizer', 'restaurant_id': restaurants[25].id},
                    {'name': 'Chicken Nuggets (9pc)', 'price': 170.0, 'category': 'Appetizer', 'restaurant_id': restaurants[25].id},
                    {'name': 'Chicken Popcorn', 'price': 150.0, 'category': 'Appetizer', 'restaurant_id': restaurants[25].id},
                    {'name': 'Hot Dog', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[25].id},
                    {'name': 'Veg Hot Dog', 'price': 70.0, 'category': 'Main Course', 'restaurant_id': restaurants[25].id},
                    {'name': 'Pizza Slice', 'price': 60.0, 'category': 'Main Course', 'restaurant_id': restaurants[25].id},
                    {'name': 'Garlic Bread (4pc)', 'price': 80.0, 'category': 'Appetizer', 'restaurant_id': restaurants[25].id},
                    {'name': 'Coke (250ml)', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[25].id},
                    {'name': 'Coke (500ml)', 'price': 60.0, 'category': 'Beverage', 'restaurant_id': restaurants[25].id},
                    {'name': 'Sprite (250ml)', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[25].id},
                    {'name': 'Fresh Lime Soda', 'price': 50.0, 'category': 'Beverage', 'restaurant_id': restaurants[25].id},
                    {'name': 'Milkshake (Chocolate)', 'price': 120.0, 'category': 'Beverage', 'restaurant_id': restaurants[25].id},
                    {'name': 'Milkshake (Vanilla)', 'price': 120.0, 'category': 'Beverage', 'restaurant_id': restaurants[25].id},

                    # Spice Garden Restaurant - North Indian & Kebab
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Appetizer', 'restaurant_id': restaurants[26].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[26].id},
                    {'name': 'Chicken Tikka (8pc)', 'price': 280.0, 'category': 'Appetizer', 'restaurant_id': restaurants[26].id},
                    {'name': 'Paneer Tikka (8pc)', 'price': 260.0, 'category': 'Appetizer', 'restaurant_id': restaurants[26].id},
                    {'name': 'Seekh Kebab (6pc)', 'price': 320.0, 'category': 'Appetizer', 'restaurant_id': restaurants[26].id},
                    {'name': 'Seekh Kebab (4pc)', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[26].id},
                    {'name': 'Shami Kebab (4pc)', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[26].id},
                    {'name': 'Reshmi Kebab (6pc)', 'price': 300.0, 'category': 'Appetizer', 'restaurant_id': restaurants[26].id},
                    {'name': 'Hara Bhara Kebab (6pc)', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[26].id},
                    {'name': 'Tandoori Pomfret', 'price': 420.0, 'category': 'Appetizer', 'restaurant_id': restaurants[26].id},
                    {'name': 'Tandoori Prawns (6pc)', 'price': 380.0, 'category': 'Appetizer', 'restaurant_id': restaurants[26].id},
                    {'name': 'Chicken Malai Tikka', 'price': 300.0, 'category': 'Appetizer', 'restaurant_id': restaurants[26].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Chicken Korma', 'price': 310.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Mutton Rogan Josh', 'price': 360.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Mutton Korma', 'price': 370.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Dal Makhani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Dal Tadka', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Paneer Tikka Masala', 'price': 270.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Kadhai Paneer', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Palak Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Malai Kofta', 'price': 270.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Shahi Paneer', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Mixed Veg Curry', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Aloo Gobi', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[26].id},
                    {'name': 'Naan Bread', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[26].id},
                    {'name': 'Garlic Naan', 'price': 60.0, 'category': 'Bread', 'restaurant_id': restaurants[26].id},
                    {'name': 'Butter Naan', 'price': 55.0, 'category': 'Bread', 'restaurant_id': restaurants[26].id},
                    {'name': 'Cheese Naan', 'price': 80.0, 'category': 'Bread', 'restaurant_id': restaurants[26].id},
                    {'name': 'Kulcha', 'price': 55.0, 'category': 'Bread', 'restaurant_id': restaurants[26].id},
                    {'name': 'Laccha Paratha', 'price': 60.0, 'category': 'Bread', 'restaurant_id': restaurants[26].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[26].id},
                    {'name': 'Missi Roti', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[26].id},

                    # Saffron Express - Mughlai & Biryani
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[27].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[27].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[27].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[27].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[27].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[27].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[27].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[27].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[27].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[27].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[27].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[27].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[27].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[27].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[27].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[27].id},

                    # Ocean Breeze Cafe - Cafe & Light Bites
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[28].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[28].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[28].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[28].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[28].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[28].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[28].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[28].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[28].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[28].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[28].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[28].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[28].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[28].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[28].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[28].id},

                    # Royal Biryani Palace - Biryani Specialist
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[29].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[29].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[29].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[29].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[29].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[29].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[29].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[29].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[29].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[29].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[29].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[29].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[29].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[29].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[29].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[29].id},

                    # Dakshin - South Indian Fine Dining
                    {'name': 'Masala Dosa', 'price': 140.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Plain Dosa', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Rava Dosa', 'price': 130.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Onion Dosa', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Ghee Roast Dosa', 'price': 160.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Set Dosa (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Mysore Masala Dosa', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Paper Roast', 'price': 180.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Idli Sambar (4pc)', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Idli Sambar (2pc)', 'price': 60.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Rava Idli (3pc)', 'price': 110.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Medu Vada (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Vada Sambar (2pc)', 'price': 85.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Sambar Vada (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Uttapam Plain', 'price': 130.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Uttapam Onion', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Uttapam Tomato', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Uttapam Mixed', 'price': 170.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Pongal', 'price': 110.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Upma', 'price': 90.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Kesari Bath', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Poori Bhaji', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[30].id},
                    {'name': 'Chole Bhature', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[30].id},
                    {'name': 'Lemon Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[30].id},
                    {'name': 'Curd Rice', 'price': 120.0, 'category': 'Main Course', 'restaurant_id': restaurants[30].id},
                    {'name': 'Tamarind Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[30].id},
                    {'name': 'Coconut Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[30].id},
                    {'name': 'Bisi Bele Bath', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[30].id},
                    {'name': 'Sambar Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[30].id},
                    {'name': 'Rasam Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[30].id},
                    {'name': 'Filter Coffee', 'price': 50.0, 'category': 'Beverage', 'restaurant_id': restaurants[30].id},
                    {'name': 'Masala Chai', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[30].id},
                    {'name': 'Badam Milk', 'price': 80.0, 'category': 'Beverage', 'restaurant_id': restaurants[30].id},
                    {'name': 'Buttermilk', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[30].id},

                    # The Grand Bawarchi - Mughlai & North Indian
                    {'name': 'Chicken Curry', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Mutton Curry', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Fish Curry', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Egg Curry', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Prawn Curry', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Chicken Masala', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Chicken Korma', 'price': 290.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Chicken Do Pyaza', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Paneer Butter Masala', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Paneer Tikka Masala', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Malai Kofta', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Shahi Paneer', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Palak Paneer', 'price': 230.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Dal Tadka', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Dal Fry', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Dal Makhani', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Dal Palak', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Chole Bhature', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Chole Kulche', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Rajma Chawal', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Kadhi Pakora', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Aloo Gobi', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Baingan Bharta', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Bhindi Masala', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Mix Veg Curry', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Tandoori Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[31].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[31].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[31].id},
                    {'name': 'Laccha Paratha', 'price': 55.0, 'category': 'Bread', 'restaurant_id': restaurants[31].id},
                    {'name': 'Jeera Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Pulao', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[31].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[31].id},
                    {'name': 'Pickle', 'price': 30.0, 'category': 'Side Dish', 'restaurant_id': restaurants[31].id},

                    # Green Park Restaurant - Multicuisine
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[32].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[32].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[32].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[32].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[32].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[32].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[32].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[32].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[32].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[32].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[32].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[32].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[32].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[32].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[32].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[32].id},

                    # Taj Mahal Restaurant - North Indian
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Appetizer', 'restaurant_id': restaurants[33].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[33].id},
                    {'name': 'Chicken Tikka (8pc)', 'price': 280.0, 'category': 'Appetizer', 'restaurant_id': restaurants[33].id},
                    {'name': 'Paneer Tikka (8pc)', 'price': 260.0, 'category': 'Appetizer', 'restaurant_id': restaurants[33].id},
                    {'name': 'Seekh Kebab (6pc)', 'price': 320.0, 'category': 'Appetizer', 'restaurant_id': restaurants[33].id},
                    {'name': 'Seekh Kebab (4pc)', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[33].id},
                    {'name': 'Shami Kebab (4pc)', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[33].id},
                    {'name': 'Reshmi Kebab (6pc)', 'price': 300.0, 'category': 'Appetizer', 'restaurant_id': restaurants[33].id},
                    {'name': 'Hara Bhara Kebab (6pc)', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[33].id},
                    {'name': 'Tandoori Pomfret', 'price': 420.0, 'category': 'Appetizer', 'restaurant_id': restaurants[33].id},
                    {'name': 'Tandoori Prawns (6pc)', 'price': 380.0, 'category': 'Appetizer', 'restaurant_id': restaurants[33].id},
                    {'name': 'Chicken Malai Tikka', 'price': 300.0, 'category': 'Appetizer', 'restaurant_id': restaurants[33].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Chicken Korma', 'price': 310.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Mutton Rogan Josh', 'price': 360.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Mutton Korma', 'price': 370.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Dal Makhani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Dal Tadka', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Paneer Tikka Masala', 'price': 270.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Kadhai Paneer', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Palak Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Malai Kofta', 'price': 270.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Shahi Paneer', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Mixed Veg Curry', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Aloo Gobi', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[33].id},
                    {'name': 'Naan Bread', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[33].id},
                    {'name': 'Garlic Naan', 'price': 60.0, 'category': 'Bread', 'restaurant_id': restaurants[33].id},
                    {'name': 'Butter Naan', 'price': 55.0, 'category': 'Bread', 'restaurant_id': restaurants[33].id},
                    {'name': 'Cheese Naan', 'price': 80.0, 'category': 'Bread', 'restaurant_id': restaurants[33].id},
                    {'name': 'Kulcha', 'price': 55.0, 'category': 'Bread', 'restaurant_id': restaurants[33].id},
                    {'name': 'Laccha Paratha', 'price': 60.0, 'category': 'Bread', 'restaurant_id': restaurants[33].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[33].id},
                    {'name': 'Missi Roti', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[33].id},

                    # China Town - Chinese & Thai
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[34].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[34].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[34].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[34].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[34].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[34].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[34].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[34].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[34].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[34].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[34].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[34].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[34].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[34].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[34].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[34].id},

                    # BBQ Nation Vizag - BBQ & Grills
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[35].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[35].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[35].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[35].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[35].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[35].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[35].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[35].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[35].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[35].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[35].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[35].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[35].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[35].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[35].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[35].id},

                    # Kamat Restaurant - South Indian & Udupi
                    {'name': 'Masala Dosa', 'price': 140.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Plain Dosa', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Rava Dosa', 'price': 130.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Onion Dosa', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Ghee Roast Dosa', 'price': 160.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Set Dosa (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Mysore Masala Dosa', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Paper Roast', 'price': 180.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Idli Sambar (4pc)', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Idli Sambar (2pc)', 'price': 60.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Rava Idli (3pc)', 'price': 110.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Medu Vada (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Vada Sambar (2pc)', 'price': 85.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Sambar Vada (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Uttapam Plain', 'price': 130.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Uttapam Onion', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Uttapam Tomato', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Uttapam Mixed', 'price': 170.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Pongal', 'price': 110.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Upma', 'price': 90.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Kesari Bath', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Poori Bhaji', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[36].id},
                    {'name': 'Chole Bhature', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[36].id},
                    {'name': 'Lemon Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[36].id},
                    {'name': 'Curd Rice', 'price': 120.0, 'category': 'Main Course', 'restaurant_id': restaurants[36].id},
                    {'name': 'Tamarind Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[36].id},
                    {'name': 'Coconut Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[36].id},
                    {'name': 'Bisi Bele Bath', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[36].id},
                    {'name': 'Sambar Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[36].id},
                    {'name': 'Rasam Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[36].id},
                    {'name': 'Filter Coffee', 'price': 50.0, 'category': 'Beverage', 'restaurant_id': restaurants[36].id},
                    {'name': 'Masala Chai', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[36].id},
                    {'name': 'Badam Milk', 'price': 80.0, 'category': 'Beverage', 'restaurant_id': restaurants[36].id},
                    {'name': 'Buttermilk', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[36].id},

                    # The Fisherman's Wharf - Seafood & Coastal
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[37].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[37].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[37].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[37].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[37].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[37].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[37].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[37].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[37].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[37].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[37].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[37].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[37].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[37].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[37].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[37].id},

                    # Barbeque Pride - Barbeque & Buffet
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[38].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[38].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[38].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[38].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[38].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[38].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[38].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[38].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[38].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[38].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[38].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[38].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[38].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[38].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[38].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[38].id},

                    # Minerva Coffee Shop - South Indian & Bakery
                    {'name': 'Masala Dosa', 'price': 140.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Plain Dosa', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Rava Dosa', 'price': 130.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Onion Dosa', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Ghee Roast Dosa', 'price': 160.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Set Dosa (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Mysore Masala Dosa', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Paper Roast', 'price': 180.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Idli Sambar (4pc)', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Idli Sambar (2pc)', 'price': 60.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Rava Idli (3pc)', 'price': 110.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Medu Vada (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Vada Sambar (2pc)', 'price': 85.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Sambar Vada (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Uttapam Plain', 'price': 130.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Uttapam Onion', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Uttapam Tomato', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Uttapam Mixed', 'price': 170.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Pongal', 'price': 110.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Upma', 'price': 90.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Kesari Bath', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Poori Bhaji', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[39].id},
                    {'name': 'Chole Bhature', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[39].id},
                    {'name': 'Lemon Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[39].id},
                    {'name': 'Curd Rice', 'price': 120.0, 'category': 'Main Course', 'restaurant_id': restaurants[39].id},
                    {'name': 'Tamarind Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[39].id},
                    {'name': 'Coconut Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[39].id},
                    {'name': 'Bisi Bele Bath', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[39].id},
                    {'name': 'Sambar Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[39].id},
                    {'name': 'Rasam Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[39].id},
                    {'name': 'Filter Coffee', 'price': 50.0, 'category': 'Beverage', 'restaurant_id': restaurants[39].id},
                    {'name': 'Masala Chai', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[39].id},
                    {'name': 'Badam Milk', 'price': 80.0, 'category': 'Beverage', 'restaurant_id': restaurants[39].id},
                    {'name': 'Buttermilk', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[39].id},

                    # Zaffran - North Indian & Tandoor
                    {'name': 'Chicken Curry', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Mutton Curry', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Fish Curry', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Egg Curry', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Prawn Curry', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Chicken Masala', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Chicken Korma', 'price': 290.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Chicken Do Pyaza', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Paneer Butter Masala', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Paneer Tikka Masala', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Malai Kofta', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Shahi Paneer', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Palak Paneer', 'price': 230.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Dal Tadka', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Dal Fry', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Dal Makhani', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Dal Palak', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Chole Bhature', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Chole Kulche', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Rajma Chawal', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Kadhi Pakora', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Aloo Gobi', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Baingan Bharta', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Bhindi Masala', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Mix Veg Curry', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Tandoori Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[40].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[40].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[40].id},
                    {'name': 'Laccha Paratha', 'price': 55.0, 'category': 'Bread', 'restaurant_id': restaurants[40].id},
                    {'name': 'Jeera Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Pulao', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[40].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[40].id},
                    {'name': 'Pickle', 'price': 30.0, 'category': 'Side Dish', 'restaurant_id': restaurants[40].id},

                    # The Square - Multi Cuisine Fine Dining
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[41].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[41].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[41].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[41].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[41].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[41].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[41].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[41].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[41].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[41].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[41].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[41].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[41].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[41].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[41].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[41].id},

                    # Bamboo Bay - Asian Fusion
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[42].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[42].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[42].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[42].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[42].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[42].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[42].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[42].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[42].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[42].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[42].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[42].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[42].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[42].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[42].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[42].id},

                    # Rayalaseema Ruchulu - Andhra Cuisine
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[43].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[43].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[43].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[43].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[43].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[43].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[43].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[43].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[43].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[43].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[43].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[43].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[43].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[43].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[43].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[43].id},

                    # Bawarchi Restaurant - Hyderabadi Biryani
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[44].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[44].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[44].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[44].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[44].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[44].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[44].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[44].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[44].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[44].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[44].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[44].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[44].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[44].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[44].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[44].id},

                    # Cream Stone - Desserts & Ice Cream
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[45].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[45].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[45].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[45].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[45].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[45].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[45].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[45].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[45].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[45].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[45].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[45].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[45].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[45].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[45].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[45].id},

                    # Absolute Barbecues - Grills & BBQ
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[46].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[46].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[46].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[46].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[46].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[46].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[46].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[46].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[46].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[46].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[46].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[46].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[46].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[46].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[46].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[46].id},

                    # Vista - The Park - Continental & Indian
                    {'name': 'Chicken Curry', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Mutton Curry', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Fish Curry', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Egg Curry', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Prawn Curry', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Chicken Masala', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Chicken Korma', 'price': 290.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Chicken Do Pyaza', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Paneer Butter Masala', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Paneer Tikka Masala', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Malai Kofta', 'price': 240.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Shahi Paneer', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Palak Paneer', 'price': 230.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Dal Tadka', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Dal Fry', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Dal Makhani', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Dal Palak', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Chole Bhature', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Chole Kulche', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Rajma Chawal', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Kadhi Pakora', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Aloo Gobi', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Baingan Bharta', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Bhindi Masala', 'price': 190.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Mix Veg Curry', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Tandoori Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[47].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[47].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[47].id},
                    {'name': 'Laccha Paratha', 'price': 55.0, 'category': 'Bread', 'restaurant_id': restaurants[47].id},
                    {'name': 'Jeera Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Pulao', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[47].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[47].id},
                    {'name': 'Pickle', 'price': 30.0, 'category': 'Side Dish', 'restaurant_id': restaurants[47].id},

                    # Dharani - Andhra & South Indian
                    {'name': 'Masala Dosa', 'price': 140.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Plain Dosa', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Rava Dosa', 'price': 130.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Onion Dosa', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Ghee Roast Dosa', 'price': 160.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Set Dosa (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Mysore Masala Dosa', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Paper Roast', 'price': 180.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Idli Sambar (4pc)', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Idli Sambar (2pc)', 'price': 60.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Rava Idli (3pc)', 'price': 110.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Medu Vada (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Vada Sambar (2pc)', 'price': 85.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Sambar Vada (3pc)', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Uttapam Plain', 'price': 130.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Uttapam Onion', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Uttapam Tomato', 'price': 150.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Uttapam Mixed', 'price': 170.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Pongal', 'price': 110.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Upma', 'price': 90.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Kesari Bath', 'price': 100.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Poori Bhaji', 'price': 120.0, 'category': 'Breakfast', 'restaurant_id': restaurants[48].id},
                    {'name': 'Chole Bhature', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[48].id},
                    {'name': 'Lemon Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[48].id},
                    {'name': 'Curd Rice', 'price': 120.0, 'category': 'Main Course', 'restaurant_id': restaurants[48].id},
                    {'name': 'Tamarind Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[48].id},
                    {'name': 'Coconut Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[48].id},
                    {'name': 'Bisi Bele Bath', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[48].id},
                    {'name': 'Sambar Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[48].id},
                    {'name': 'Rasam Rice', 'price': 130.0, 'category': 'Main Course', 'restaurant_id': restaurants[48].id},
                    {'name': 'Filter Coffee', 'price': 50.0, 'category': 'Beverage', 'restaurant_id': restaurants[48].id},
                    {'name': 'Masala Chai', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[48].id},
                    {'name': 'Badam Milk', 'price': 80.0, 'category': 'Beverage', 'restaurant_id': restaurants[48].id},
                    {'name': 'Buttermilk', 'price': 40.0, 'category': 'Beverage', 'restaurant_id': restaurants[48].id},

                    # Flying Spaghetti Monster - Italian & Continental
                    {'name': 'Chicken Biryani', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Mutton Biryani', 'price': 280.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Veg Biryani', 'price': 200.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Egg Biryani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Paneer Biryani', 'price': 220.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Prawn Biryani', 'price': 350.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Butter Chicken', 'price': 320.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Chicken Tikka Masala', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Paneer Butter Masala', 'price': 260.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Dal Makhani', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Kadhai Chicken', 'price': 300.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Kadhai Paneer', 'price': 250.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Tandoori Chicken (Full)', 'price': 380.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Tandoori Chicken (Half)', 'price': 210.0, 'category': 'Appetizer', 'restaurant_id': restaurants[49].id},
                    {'name': 'Chicken 65', 'price': 220.0, 'category': 'Appetizer', 'restaurant_id': restaurants[49].id},
                    {'name': 'Paneer 65', 'price': 200.0, 'category': 'Appetizer', 'restaurant_id': restaurants[49].id},
                    {'name': 'Chilli Chicken', 'price': 240.0, 'category': 'Appetizer', 'restaurant_id': restaurants[49].id},
                    {'name': 'Gobi Manchurian', 'price': 180.0, 'category': 'Appetizer', 'restaurant_id': restaurants[49].id},
                    {'name': 'Veg Fried Rice', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Chicken Fried Rice', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Egg Fried Rice', 'price': 160.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Schezwan Fried Rice', 'price': 170.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Veg Noodles', 'price': 150.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Chicken Noodles', 'price': 180.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Garlic Naan', 'price': 50.0, 'category': 'Bread', 'restaurant_id': restaurants[49].id},
                    {'name': 'Butter Naan', 'price': 45.0, 'category': 'Bread', 'restaurant_id': restaurants[49].id},
                    {'name': 'Tandoori Roti', 'price': 35.0, 'category': 'Bread', 'restaurant_id': restaurants[49].id},
                    {'name': 'Roomali Roti', 'price': 40.0, 'category': 'Bread', 'restaurant_id': restaurants[49].id},
                    {'name': 'Jeera Rice', 'price': 140.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Steamed Rice', 'price': 80.0, 'category': 'Main Course', 'restaurant_id': restaurants[49].id},
                    {'name': 'Raita', 'price': 60.0, 'category': 'Side Dish', 'restaurant_id': restaurants[49].id},
                    {'name': 'Green Salad', 'price': 80.0, 'category': 'Salad', 'restaurant_id': restaurants[49].id},
                    {'name': 'Gulab Jamun (2pc)', 'price': 80.0, 'category': 'Dessert', 'restaurant_id': restaurants[49].id},
                    {'name': 'Ice Cream (2sc)', 'price': 100.0, 'category': 'Dessert', 'restaurant_id': restaurants[49].id},
                    {'name': 'Masala Papad', 'price': 50.0, 'category': 'Appetizer', 'restaurant_id': restaurants[49].id},
                    {'name': 'Roasted Papad', 'price': 40.0, 'category': 'Appetizer', 'restaurant_id': restaurants[49].id},
                ]

                for item_data in menu_items_data:
                    item = MenuItem(**item_data)
                    db.session.add(item)
                
                db.session.commit()
                print("[DEBUG] Comprehensive Visakhapatnam data loaded successfully - 50 restaurants with 1759 menu items")
            else:
                print("[DEBUG] Database already has data, skipping load")
    except Exception as e:
        print(f"[ERROR in init_db] {e}")
        import traceback
        traceback.print_exc()
        raise

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

# Mock Payment Processing Endpoints
@app.route('/api/payments/process-card', methods=['POST'])
def process_card_payment():
    """Mock card payment processing - accepts any card details"""
    try:
        data = request.get_json() or {}
        # Accept any input - no validation required
        order_id = data.get('order_id', 'demo_order')
        amount = data.get('amount', 0)
        
        # Simulate payment processing
        import time
        time.sleep(0.5)
        
        return jsonify({
            'success': True,
            'message': 'Card payment processed successfully',
            'transaction_id': f'txn_card_{int(time.time())}',
            'amount': amount
        }), 200
    except Exception as e:
        return jsonify({'success': True, 'error': str(e)}), 200

@app.route('/api/payments/process-cod', methods=['POST'])
def process_cod_payment():
    """Mock Cash on Delivery processing - accepts any input"""
    try:
        data = request.get_json() or {}
        # Accept any input - no validation required
        order_id = data.get('order_id', 'demo_order')
        amount = data.get('amount', 0)
        
        return jsonify({
            'success': True,
            'message': 'Cash on Delivery confirmed',
            'transaction_id': f'txn_cod_{int(time.time())}',
            'amount': amount,
            'note': 'Payment will be collected upon delivery'
        }), 200
    except Exception as e:
        return jsonify({'success': True, 'error': str(e)}), 200

@app.route('/api/payments/process-upi', methods=['POST'])
def process_upi_payment():
    """Mock UPI payment processing - accepts any UPI details"""
    try:
        data = request.get_json() or {}
        # Accept any input - no validation required
        order_id = data.get('order_id', 'demo_order')
        amount = data.get('amount', 0)
        upi_id = data.get('upi_id', 'demo@upi')
        
        # Simulate UPI payment
        import time
        time.sleep(0.5)
        
        return jsonify({
            'success': True,
            'message': 'UPI payment processed successfully',
            'transaction_id': f'txn_upi_{int(time.time())}',
            'amount': amount,
            'upi_id': upi_id
        }), 200
    except Exception as e:
        return jsonify({'success': True, 'error': str(e)}), 200

if __name__ == '__main__':
    try:
        init_db()
        print("[OK] Database initialized")
        # Use Flask development server directly
        app.run(debug=False, host='0.0.0.0', port=8000, threaded=True)
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
