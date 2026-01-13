from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.real_data_services import (
    LocationService,
    RestaurantService,
    MenuService,
    MenuCustomizationService,
    DeliveryTrackingService,
    FeedbackService,
    PaymentService
)
from app.services.notification_service import NotificationService
from app import db
from app.models.models import User, Order, OrderItem, DeliveryTracking, Feedback
import json
from datetime import datetime, timedelta
import stripe

delivery_bp = Blueprint('delivery', __name__)

# Initialize services
location_service = LocationService()
restaurant_service = RestaurantService()
menu_service = MenuService()
customization_service = MenuCustomizationService()
delivery_service = DeliveryTrackingService()
feedback_service = FeedbackService()
payment_service = PaymentService()
notification_service = NotificationService()

@delivery_bp.route('/api/location/detect', methods=['GET'])
def detect_location():
    """Detect user location from IP"""
    try:
        location = location_service.get_location_from_ip()
        if location:
            return jsonify({
                'success': True,
                'location': location
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Unable to detect location'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@delivery_bp.route('/api/restaurants/nearby', methods=['GET'])
def get_restaurants_nearby():
    """Get restaurants near user location"""
    try:
        lat = float(request.args.get('lat', 0))
        lng = float(request.args.get('lng', 0))
        radius = int(request.args.get('radius', 5000))

        if lat == 0 or lng == 0:
            return jsonify({
                'success': False,
                'error': 'Invalid coordinates'
            }), 400

        restaurants = restaurant_service.get_restaurants_nearby(lat, lng, radius)

        return jsonify({
            'success': True,
            'restaurants': restaurants
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@delivery_bp.route('/api/restaurants/<int:restaurant_id>/menu', methods=['GET'])
def get_restaurant_menu(restaurant_id):
    """Get menu items for a restaurant"""
    try:
        # Get restaurant details first to determine cuisine type
        restaurant_name = request.args.get('name', '')
        cuisine_type = request.args.get('cuisine', '')

        # Try to get real menu data
        menu_items = menu_service.get_restaurant_menu(str(restaurant_id), restaurant_name, cuisine_type)

        if not menu_items:
            # Fallback to generated menu based on cuisine
            menu_items = menu_service._generate_menu_from_cuisine(cuisine_type or 'american')

        return jsonify({
            'success': True,
            'menu_items': menu_items
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@delivery_bp.route('/api/orders', methods=['POST'])
@jwt_required()
def create_order():
    """Create a new order"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        # Create order
        order = Order(
            user_id=user_id,
            restaurant_id=data.get('restaurant_id'),  # Add restaurant_id
            delivery_address=data['delivery_address'],
            payment_method=data.get('payment_method', 'card'),
            special_instructions=data.get('special_instructions', ''),
            status='confirmed',
            total_amount=0  # Will calculate below
        )

        db.session.add(order)
        db.session.flush()  # Get order ID

        total_amount = 0

        # Add order items
        for item in data['items']:
            customizations = item.get('customizations', {})
            customization_price = customization_service.calculate_customization_price(customizations)

            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item['id'],
                quantity=item['quantity'],
                unit_price=item['price'],
                customizations=json.dumps(customizations),
                customization_price=customization_price
            )

            total_amount += (item['price'] * item['quantity']) + customization_price
            db.session.add(order_item)

        # Update order total
        order.total_amount = total_amount + 2.99 + (total_amount * 0.08)  # Add delivery fee and tax

        # Create delivery tracking
        tracking = DeliveryTracking(
            order_id=order.id,
            status='confirmed',
            estimated_time='30-45 minutes'
        )
        db.session.add(tracking)

        db.session.commit()

        # Send order confirmation notifications
        order_details = {
            'id': order.id,
            'restaurant_name': order.restaurant.name if order.restaurant else 'SmartFood',
            'total': order.total_amount
        }
        notification_service.send_order_confirmation(
            user.email,
            getattr(user, 'phone', None),  # Assuming phone field might be added later
            order_details
        )

        return jsonify({
            'success': True,
            'order_id': order.id,
            'message': 'Order created successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@delivery_bp.route('/api/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    """Get order details"""
    try:
        user_id = get_jwt_identity()

        order = Order.query.filter_by(id=order_id, user_id=user_id).first()
        if not order:
            return jsonify({
                'success': False,
                'error': 'Order not found'
            }), 404

        order_items = OrderItem.query.filter_by(order_id=order_id).all()

        order_data = {
            'id': order.id,
            'status': order.status,
            'total': order.total_amount,
            'delivery_address': order.delivery_address,
            'created_at': order.created_at.isoformat(),
            'estimated_delivery': order.estimated_delivery.isoformat() if order.estimated_delivery else None,
            'items': [
                {
                    'id': item.menu_item_id,
                    'name': f'Menu Item {item.menu_item_id}',  # Mock name
                    'price': item.unit_price,
                    'quantity': item.quantity,
                    'customizations': json.loads(item.customizations) if item.customizations else {}
                }
                for item in order_items
            ]
        }

        return jsonify({
            'success': True,
            'order': order_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@delivery_bp.route('/api/orders/<int:order_id>/tracking', methods=['GET'])
@jwt_required()
def get_order_tracking(order_id):
    """Get delivery tracking information"""
    try:
        user_id = get_jwt_identity()

        order = Order.query.filter_by(id=order_id, user_id=user_id).first()
        if not order:
            return jsonify({
                'success': False,
                'error': 'Order not found'
            }), 404

        tracking = DeliveryTracking.query.filter_by(order_id=order_id).first()
        if not tracking:
            return jsonify({
                'success': False,
                'error': 'Tracking information not available'
            }), 404

        tracking_data = {
            'status': tracking.status,
            'location': json.loads(tracking.location) if tracking.location else None,
            'estimated_time': tracking.estimated_time,
            'driver_name': tracking.driver_name,
            'driver_phone': tracking.driver_phone
        }

        return jsonify({
            'success': True,
            'tracking': tracking_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@delivery_bp.route('/api/orders/user', methods=['GET'])
@jwt_required()
def get_user_orders():
    """Get all orders for the authenticated user"""
    try:
        user_id = get_jwt_identity()

        orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()

        orders_data = []
        for order in orders:
            order_items = OrderItem.query.filter_by(order_id=order.id).all()

            order_data = {
                'id': order.id,
                'status': order.status,
                'total': order.total_amount,
                'delivery_address': order.delivery_address,
                'created_at': order.created_at.isoformat(),
                'estimated_delivery': order.estimated_delivery.isoformat() if order.estimated_delivery else None,
                'restaurant_name': order.restaurant.name if order.restaurant else 'Unknown Restaurant',
                'items_count': len(order_items),
                'items': [
                    {
                        'id': item.menu_item_id,
                        'name': f'Menu Item {item.menu_item_id}',  # Mock name - could be enhanced
                        'price': item.unit_price,
                        'quantity': item.quantity,
                        'subtotal': item.unit_price * item.quantity
                    }
                    for item in order_items
                ]
            }
            orders_data.append(order_data)

        return jsonify({
            'success': True,
            'orders': orders_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@delivery_bp.route('/api/orders/<int:order_id>/status', methods=['PUT'])
@jwt_required()
def update_order_status(order_id):
    """Update order status (for restaurant/admin use)"""
    try:
        data = request.get_json()
        new_status = data.get('status')

        if not new_status:
            return jsonify({
                'success': False,
                'error': 'Status is required'
            }), 400

        # For now, allow any authenticated user to update status (in production, restrict to restaurant owners/admins)
        order = Order.query.filter_by(id=order_id).first()
        if not order:
            return jsonify({
                'success': False,
                'error': 'Order not found'
            }), 404

        old_status = order.status
        order.status = new_status

        # Update tracking status if it exists
        tracking = DeliveryTracking.query.filter_by(order_id=order_id).first()
        if tracking:
            tracking.status = new_status

        db.session.commit()

        # Send status update notifications if status changed
        if old_status != new_status:
            order_details = {
                'id': order.id,
                'restaurant_name': order.restaurant.name if order.restaurant else 'SmartFood',
                'total': order.total_amount
            }
            notification_service.send_order_status_update(
                order.user.email,
                getattr(order.user, 'phone', None),
                order_details,
                new_status
            )

        return jsonify({
            'success': True,
            'message': f'Order status updated to {new_status}',
            'order': {
                'id': order.id,
                'status': order.status
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@delivery_bp.route('/api/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    """Submit customer feedback"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        feedback = Feedback(
            user_id=user_id,
            order_id=data.get('order_id'),
            restaurant_rating=data['restaurant_rating'],
            delivery_rating=data['delivery_rating'],
            food_quality_rating=data['food_quality_rating'],
            comments=data.get('comments', ''),
            would_recommend=data.get('would_recommend', True)
        )

        db.session.add(feedback)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Feedback submitted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@delivery_bp.route('/api/payments/create-intent', methods=['POST'])
@jwt_required()
def create_payment_intent():
    """Create a payment intent for Stripe"""
    try:
        data = request.get_json()
        amount = data.get('amount', 0)

        if amount <= 0:
            return jsonify({
                'success': False,
                'error': 'Invalid amount'
            }), 400

        result = payment_service.create_payment_intent(amount)

        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400

        return jsonify({
            'success': True,
            'payment_intent': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@delivery_bp.route('/api/payments/process-cod', methods=['POST'])
@jwt_required()
def process_cod_payment():
    """Process cash on delivery payment"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        amount = data.get('amount', 0)

        if not order_id or amount <= 0:
            return jsonify({
                'success': False,
                'error': 'Invalid order ID or amount'
            }), 400

        success = payment_service.process_cod_payment(order_id, amount)

        if success:
            return jsonify({
                'success': True,
                'message': 'Cash on delivery payment processed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to process cash on delivery payment'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@delivery_bp.route('/api/payments/process-upi', methods=['POST'])
@jwt_required()
def process_upi_payment():
    """Process UPI payment"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        amount = data.get('amount', 0)
        upi_id = data.get('upi_id')

        if not order_id or amount <= 0 or not upi_id:
            return jsonify({
                'success': False,
                'error': 'Invalid order ID, amount, or UPI ID'
            }), 400

        result = payment_service.process_upi_payment(order_id, amount, upi_id)

        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400

        return jsonify({
            'success': True,
            'payment': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500