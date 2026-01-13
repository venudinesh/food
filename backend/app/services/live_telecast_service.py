# Live telecast service for WebRTC video streaming
import os
import json
import uuid
from datetime import datetime, timedelta
from flask import current_app
from flask_socketio import SocketIO, emit, join_room, leave_room
import redis
import eventlet

class LiveTelecastService:
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.active_streams = {}  # room_id -> stream_info
        self.redis_client = None

        # Try to connect to Redis for production scaling
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', '6379')),
                db=int(os.getenv('REDIS_DB', '0')),
                password=os.getenv('REDIS_PASSWORD'),
                decode_responses=True
            )
            self.redis_client.ping()  # Test connection
            print("Connected to Redis for live telecast scaling")
        except Exception as e:
            print(f"Redis not available, using in-memory storage: {e}")
            self.redis_client = None

    def create_stream_room(self, order_id, chef_id, customer_id):
        """Create a new WebRTC stream room for chef-customer interaction"""
        room_id = f"stream_{order_id}_{uuid.uuid4().hex[:8]}"

        stream_info = {
            'room_id': room_id,
            'order_id': order_id,
            'chef_id': chef_id,
            'customer_id': customer_id,
            'status': 'waiting',  # waiting, active, ended
            'participants': [],
            'created_at': datetime.utcnow().isoformat(),
            'ended_at': None,
            'stream_type': 'webrtc',  # webrtc, hls, etc.
            'quality': 'hd',  # sd, hd, fhd
            'max_participants': 2  # chef + customer
        }

        self.active_streams[room_id] = stream_info

        # Store in Redis if available
        if self.redis_client:
            self.redis_client.setex(
                f"stream:{room_id}",
                3600,  # 1 hour TTL
                json.dumps(stream_info)
            )

        print(f"Created stream room {room_id} for order {order_id}")
        return room_id

    def join_stream_room(self, room_id, user_id, user_type):
        """Join a WebRTC stream room"""
        if room_id not in self.active_streams:
            # Try to load from Redis
            if self.redis_client:
                stream_data = self.redis_client.get(f"stream:{room_id}")
                if stream_data:
                    self.active_streams[room_id] = json.loads(stream_data)
                else:
                    return {'success': False, 'error': 'Stream room not found'}

        stream_info = self.active_streams[room_id]

        # Validate user permissions
        if user_type == 'chef' and user_id != stream_info['chef_id']:
            return {'success': False, 'error': 'Unauthorized chef'}
        elif user_type == 'customer' and user_id != stream_info['customer_id']:
            return {'success': False, 'error': 'Unauthorized customer'}

        # Check if room is full
        if len(stream_info['participants']) >= stream_info['max_participants']:
            return {'success': False, 'error': 'Stream room is full'}

        # Add participant
        participant = {
            'user_id': user_id,
            'user_type': user_type,
            'joined_at': datetime.utcnow().isoformat(),
            'socket_id': None  # Will be set by socket handler
        }

        stream_info['participants'].append(participant)

        # Update status if both participants joined
        if len(stream_info['participants']) == 2:
            stream_info['status'] = 'active'

        # Save updated info
        if self.redis_client:
            self.redis_client.setex(
                f"stream:{room_id}",
                3600,
                json.dumps(stream_info)
            )

        print(f"User {user_id} ({user_type}) joined stream room {room_id}")
        return {
            'success': True,
            'room_id': room_id,
            'stream_info': stream_info
        }

    def leave_stream_room(self, room_id, user_id):
        """Leave a WebRTC stream room"""
        if room_id not in self.active_streams:
            return {'success': False, 'error': 'Stream room not found'}

        stream_info = self.active_streams[room_id]

        # Remove participant
        stream_info['participants'] = [
            p for p in stream_info['participants']
            if p['user_id'] != user_id
        ]

        # If no participants left, end the stream
        if len(stream_info['participants']) == 0:
            stream_info['status'] = 'ended'
            stream_info['ended_at'] = datetime.utcnow().isoformat()

            # Clean up from Redis
            if self.redis_client:
                self.redis_client.delete(f"stream:{room_id}")

            print(f"Stream room {room_id} ended - no participants")
        else:
            # Update status to waiting if only one participant left
            stream_info['status'] = 'waiting'

            # Save updated info
            if self.redis_client:
                self.redis_client.setex(
                    f"stream:{room_id}",
                    3600,
                    json.dumps(stream_info)
                )

        return {'success': True, 'stream_info': stream_info}

    def get_stream_info(self, room_id):
        """Get information about a stream room"""
        if room_id in self.active_streams:
            return self.active_streams[room_id]

        # Try Redis
        if self.redis_client:
            stream_data = self.redis_client.get(f"stream:{room_id}")
            if stream_data:
                return json.loads(stream_data)

        return None

    def get_active_streams_for_user(self, user_id):
        """Get all active streams for a user"""
        user_streams = []

        # Check in-memory streams
        for room_id, stream_info in self.active_streams.items():
            if (stream_info['chef_id'] == user_id or
                stream_info['customer_id'] == user_id):
                user_streams.append(stream_info)

        # Check Redis for additional streams
        if self.redis_client:
            for key in self.redis_client.scan_iter("stream:*"):
                stream_data = self.redis_client.get(key)
                if stream_data:
                    stream_info = json.loads(stream_data)
                    if (stream_info['chef_id'] == user_id or
                        stream_info['customer_id'] == user_id):
                        user_streams.append(stream_info)

        return user_streams

    def send_stream_message(self, room_id, message_type, data, sender_id=None):
        """Send a message to all participants in a stream room"""
        if not self.socketio:
            return False

        try:
            self.socketio.emit(message_type, data, room=room_id)
            print(f"Sent {message_type} message to room {room_id}")
            return True
        except Exception as e:
            print(f"Failed to send message to room {room_id}: {e}")
            return False

# Socket.IO event handlers for WebRTC signaling
def register_socket_events(socketio, telecast_service):
    @socketio.on('join_stream')
    def handle_join_stream(data):
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        user_type = data.get('user_type')

        result = telecast_service.join_stream_room(room_id, user_id, user_type)

        if result['success']:
            join_room(room_id)
            emit('stream_joined', {
                'room_id': room_id,
                'stream_info': result['stream_info']
            })

            # Notify other participants
            emit('participant_joined', {
                'user_id': user_id,
                'user_type': user_type
            }, room=room_id, skip_sid=True)
        else:
            emit('stream_error', result)

    @socketio.on('leave_stream')
    def handle_leave_stream(data):
        room_id = data.get('room_id')
        user_id = data.get('user_id')

        result = telecast_service.leave_stream_room(room_id, user_id)

        if result['success']:
            leave_room(room_id)
            emit('stream_left', {'room_id': room_id})

            # Notify other participants
            emit('participant_left', {
                'user_id': user_id
            }, room=room_id)

    @socketio.on('webrtc_offer')
    def handle_webrtc_offer(data):
        room_id = data.get('room_id')
        offer = data.get('offer')

        # Forward offer to other participant
        emit('webrtc_offer', {
            'offer': offer,
            'from': data.get('from')
        }, room=room_id, skip_sid=True)

    @socketio.on('webrtc_answer')
    def handle_webrtc_answer(data):
        room_id = data.get('room_id')
        answer = data.get('answer')

        # Forward answer to other participant
        emit('webrtc_answer', {
            'answer': answer,
            'from': data.get('from')
        }, room=room_id, skip_sid=True)

    @socketio.on('webrtc_ice_candidate')
    def handle_ice_candidate(data):
        room_id = data.get('room_id')
        candidate = data.get('candidate')

        # Forward ICE candidate to other participant
        emit('webrtc_ice_candidate', {
            'candidate': candidate,
            'from': data.get('from')
        }, room=room_id, skip_sid=True)

    @socketio.on('stream_message')
    def handle_stream_message(data):
        room_id = data.get('room_id')
        message = data.get('message')
        sender_id = data.get('sender_id')

        # Broadcast message to all participants in room
        emit('stream_message', {
            'message': message,
            'sender_id': sender_id,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room_id)