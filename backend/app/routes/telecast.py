# Live telecast routes for WebRTC streaming
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models.models import Order, User

telecast_bp = Blueprint('telecast', __name__)

@telecast_bp.route('/api/streams/create', methods=['POST'])
@jwt_required()
def create_stream():
    """Create a new live stream room for chef-customer interaction"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')

        if not order_id:
            return jsonify({
                'success': False,
                'error': 'Order ID is required'
            }), 400

        user_id = get_jwt_identity()

        # Verify the order exists and user is involved
        order = Order.query.filter_by(id=order_id).first()
        if not order:
            return jsonify({
                'success': False,
                'error': 'Order not found'
            }), 404

        # Check if user is the customer or if they're a chef/restaurant owner
        is_customer = order.user_id == user_id
        is_chef = order.restaurant and order.restaurant.owner_id == user_id  # Assuming restaurant has owner_id

        if not (is_customer or is_chef):
            return jsonify({
                'success': False,
                'error': 'Unauthorized to create stream for this order'
            }), 403

        # Determine chef and customer IDs
        chef_id = order.restaurant.owner_id if order.restaurant else None
        customer_id = order.user_id

        if not chef_id:
            return jsonify({
                'success': False,
                'error': 'Restaurant information not available'
            }), 400

        # Create stream room
        from flask import current_app
        telecast_service = current_app.telecast_service
        room_id = telecast_service.create_stream_room(order_id, chef_id, customer_id)

        return jsonify({
            'success': True,
            'room_id': room_id,
            'stream_url': f'/stream/{room_id}',
            'message': 'Stream room created successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@telecast_bp.route('/api/streams/user', methods=['GET'])
@jwt_required()
def get_user_streams():
    """Get all active streams for the authenticated user"""
    try:
        user_id = get_jwt_identity()

        from flask import current_app
        telecast_service = current_app.telecast_service
        streams = telecast_service.get_active_streams_for_user(user_id)

        return jsonify({
            'success': True,
            'streams': streams
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@telecast_bp.route('/api/streams/<room_id>', methods=['GET'])
@jwt_required()
def get_stream_info(room_id):
    """Get information about a specific stream room"""
    try:
        user_id = get_jwt_identity()

        from flask import current_app
        telecast_service = current_app.telecast_service
        stream_info = telecast_service.get_stream_info(room_id)

        if not stream_info:
            return jsonify({
                'success': False,
                'error': 'Stream not found'
            }), 404

        # Check if user is authorized to view this stream
        if user_id not in [stream_info['chef_id'], stream_info['customer_id']]:
            return jsonify({
                'success': False,
                'error': 'Unauthorized to access this stream'
            }), 403

        return jsonify({
            'success': True,
            'stream': stream_info
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@telecast_bp.route('/api/streams/<room_id>/join', methods=['POST'])
@jwt_required()
def join_stream(room_id):
    """Join a stream room"""
    try:
        data = request.get_json()
        user_type = data.get('user_type')  # 'chef' or 'customer'

        if user_type not in ['chef', 'customer']:
            return jsonify({
                'success': False,
                'error': 'Invalid user type'
            }), 400

        user_id = get_jwt_identity()

        from flask import current_app
        telecast_service = current_app.telecast_service
        result = telecast_service.join_stream_room(room_id, user_id, user_type)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@telecast_bp.route('/api/streams/<room_id>/end', methods=['POST'])
@jwt_required()
def end_stream(room_id):
    """End a stream room"""
    try:
        user_id = get_jwt_identity()

        from flask import current_app
        telecast_service = current_app.telecast_service
        stream_info = telecast_service.get_stream_info(room_id)

        if not stream_info:
            return jsonify({
                'success': False,
                'error': 'Stream not found'
            }), 404

        # Check if user is authorized to end this stream
        if user_id not in [stream_info['chef_id'], stream_info['customer_id']]:
            return jsonify({
                'success': False,
                'error': 'Unauthorized to end this stream'
            }), 403

        # End the stream by removing all participants
        stream_info['status'] = 'ended'
        stream_info['ended_at'] = datetime.utcnow().isoformat()

        # Clean up
        if room_id in telecast_service.active_streams:
            del telecast_service.active_streams[room_id]

        if telecast_service.redis_client:
            telecast_service.redis_client.delete(f"stream:{room_id}")

        return jsonify({
            'success': True,
            'message': 'Stream ended successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500