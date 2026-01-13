from datetime import datetime
from app import db

class Rating(db.Model):
    __tablename__ = 'ratings'

    id = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'), nullable=True)
    food_item_id = db.Column(db.String(50), nullable=True)
    restaurant_id = db.Column(db.String(50), nullable=True)
    delivery_person_id = db.Column(db.String(50), nullable=True)
    rating = db.Column(db.Float, nullable=False)  # 1-5 stars
    feedback_text = db.Column(db.Text, nullable=True)
    rating_type = db.Column(db.String(20), nullable=False)  # ORDER, FOOD_ITEM, etc.
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_anonymous = db.Column(db.Boolean, default=False)
    helpful_votes = db.Column(db.Integer, default=0)

    # Relationship with user
    user = db.relationship('User', backref=db.backref('ratings', lazy=True))

    # Tags stored as JSON
    tags = db.Column(db.JSON, default=list)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'order_id': self.order_id,
            'food_item_id': self.food_item_id,
            'restaurant_id': self.restaurant_id,
            'delivery_person_id': self.delivery_person_id,
            'rating': self.rating,
            'feedback_text': self.feedback_text,
            'rating_type': self.rating_type,
            'timestamp': self.timestamp.isoformat(),
            'is_anonymous': self.is_anonymous,
            'helpful_votes': self.helpful_votes,
            'tags': self.tags or []
        }

class RatingStats(db.Model):
    __tablename__ = 'rating_stats'

    id = db.Column(db.String(50), primary_key=True)
    target_id = db.Column(db.String(50), nullable=False)  # order_id, food_item_id, etc.
    target_type = db.Column(db.String(20), nullable=False)  # ORDER, FOOD_ITEM, etc.
    average_rating = db.Column(db.Float, default=0.0)
    total_ratings = db.Column(db.Integer, default=0)
    rating_distribution = db.Column(db.JSON, default=dict)  # {1: 5, 2: 10, 3: 15, 4: 20, 5: 25}
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'target_id': self.target_id,
            'target_type': self.target_type,
            'average_rating': self.average_rating,
            'total_ratings': self.total_ratings,
            'rating_distribution': self.rating_distribution or {},
            'last_updated': self.last_updated.isoformat()
        }