from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.models import User, Order
from app import db
import uuid
from datetime import datetime, timedelta

rating_bp = Blueprint('rating', __name__)

@rating_bp.route('/submit', methods=['POST'])
@jwt_required()
def submit_rating():
    """Submit a new rating"""
    try:
        data = request.get_json()
        current_user_id = get_jwt_identity()

        # Validate required fields
        required_fields = ['target_id', 'rating', 'rating_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Validate rating range
        if not (1 <= data['rating'] <= 5):
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400

        # Create rating
        rating_id = str(uuid.uuid4())
        rating = Rating(
            id=rating_id,
            user_id=current_user_id,
            rating=data['rating'],
            feedback_text=data.get('feedback_text', ''),
            rating_type=data['rating_type'],
            is_anonymous=data.get('is_anonymous', False),
            tags=data.get('tags', [])
        )

        # Set target ID based on rating type
        rating_type = data['rating_type']
        if rating_type == 'ORDER':
            rating.order_id = data['target_id']
        elif rating_type == 'FOOD_ITEM':
            rating.food_item_id = data['target_id']
        elif rating_type == 'RESTAURANT':
            rating.restaurant_id = data['target_id']
        elif rating_type == 'DELIVERY_PERSON':
            rating.delivery_person_id = data['target_id']

        db.session.add(rating)
        db.session.commit()

        # Update rating statistics
        update_rating_stats(data['target_id'], rating_type)

        return jsonify({
            'success': True,
            'message': 'Rating submitted successfully',
            'rating_id': rating_id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@rating_bp.route('/<rating_id>', methods=['GET'])
@jwt_required()
def get_rating(rating_id):
    """Get a specific rating"""
    try:
        rating = Rating.query.get(rating_id)
        if not rating:
            return jsonify({'error': 'Rating not found'}), 404

        # Check if user can view this rating
        current_user_id = get_jwt_identity()
        if rating.user_id != current_user_id and not rating.is_anonymous:
            return jsonify({'error': 'Unauthorized'}), 403

        return jsonify(rating.to_dict()), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rating_bp.route('/user/<user_id>', methods=['GET'])
@jwt_required()
def get_user_ratings(user_id):
    """Get all ratings by a user"""
    try:
        current_user_id = get_jwt_identity()
        if user_id != current_user_id:
            return jsonify({'error': 'Unauthorized'}), 403

        ratings = Rating.query.filter_by(user_id=user_id).order_by(Rating.timestamp.desc()).all()
        return jsonify([rating.to_dict() for rating in ratings]), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rating_bp.route('/target/<target_id>', methods=['GET'])
def get_target_ratings(target_id):
    """Get all ratings for a target (order, food item, etc.)"""
    try:
        rating_type = request.args.get('type', 'ORDER')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        query = Rating.query.filter_by(**{f'{rating_type.lower()}_id': target_id})
        ratings = query.order_by(Rating.timestamp.desc()).paginate(page=page, per_page=per_page)

        return jsonify({
            'ratings': [rating.to_dict() for rating in ratings.items],
            'total': ratings.total,
            'pages': ratings.pages,
            'current_page': ratings.page
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rating_bp.route('/stats/<target_id>', methods=['GET'])
def get_rating_stats(target_id):
    """Get rating statistics for a target"""
    try:
        rating_type = request.args.get('type', 'ORDER')

        # Try to get cached stats
        stats = RatingStats.query.filter_by(
            target_id=target_id,
            target_type=rating_type
        ).first()

        if not stats or (datetime.utcnow() - stats.last_updated) > timedelta(hours=1):
            # Update stats if not exist or outdated
            stats = update_rating_stats(target_id, rating_type)

        return jsonify(stats.to_dict()), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rating_bp.route('/<rating_id>/helpful', methods=['POST'])
@jwt_required()
def mark_helpful(rating_id):
    """Mark a rating as helpful"""
    try:
        rating = Rating.query.get(rating_id)
        if not rating:
            return jsonify({'error': 'Rating not found'}), 404

        rating.helpful_votes += 1
        db.session.commit()

        return jsonify({'success': True, 'helpful_votes': rating.helpful_votes}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def update_rating_stats(target_id, target_type):
    """Update rating statistics for a target"""
    try:
        # Get all ratings for this target
        field_name = f'{target_type.lower()}_id'
        ratings = Rating.query.filter_by(**{field_name: target_id}).all()

        if not ratings:
            return None

        # Calculate statistics
        total_ratings = len(ratings)
        average_rating = sum(r.rating for r in ratings) / total_ratings

        # Calculate distribution
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for rating in ratings:
            distribution[int(rating.rating)] += 1

        # Update or create stats
        stats_id = f"{target_type}_{target_id}"
        stats = RatingStats.query.get(stats_id)

        if not stats:
            stats = RatingStats(
                id=stats_id,
                target_id=target_id,
                target_type=target_type
            )
            db.session.add(stats)

        stats.average_rating = average_rating
        stats.total_ratings = total_ratings
        stats.rating_distribution = distribution
        stats.last_updated = datetime.utcnow()

        db.session.commit()
        return stats

    except Exception as e:
        db.session.rollback()
        print(f"Error updating rating stats: {e}")
        return None