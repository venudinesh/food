"""
Recommendation API Integration for Flask Backend
================================================

This module integrates the ML recommendation engine with the Flask backend API.
It provides REST endpoints for getting personalized food recommendations.

Integration Points:
- User order history from database
- Real-time recommendation generation
- Caching for performance
- Error handling and logging

Author: B.Tech Project Implementation
Date: December 2025
"""

from flask import Flask, request, jsonify
import sys
import os
sys.path.append(os.path.dirname(__file__))
from recommendation_engine import FoodRecommendationEngine, RecommendationAPI
import json
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecommendationService:
    """
    Service class that manages the recommendation engine integration
    with the Flask backend application.
    """

    def __init__(self):
        """Initialize the recommendation service"""
        self.engine = FoodRecommendationEngine()
        self.api = None
        self.is_initialized = False

    def initialize(self):
        """
        Initialize the recommendation engine
        Load models or train if not available
        """
        try:
            logger.info("Initializing recommendation service...")

            # Load sample data for training
            self.engine.load_sample_data()

            # Try to load pre-trained models
            if self.engine.load_models('models/recommendation_models.pkl'):
                logger.info("Pre-trained models loaded successfully")
            else:
                logger.warning("No pre-trained models found, training new models...")
                self.engine.train_all_models()
                # Save models for future use
                os.makedirs('models', exist_ok=True)
                self.engine.save_models('models/recommendation_models.pkl')
                logger.info("New models trained and saved")

            # Initialize API
            self.api = RecommendationAPI(self.engine)
            self.is_initialized = True
            logger.info("Recommendation service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize recommendation service: {e}")
            self.is_initialized = False

    def get_user_recommendations(self, user_id: int, food_history: list = None, top_n: int = 5):
        """
        Get personalized recommendations for a user

        Args:
            user_id: User ID from the database
            food_history: List of recently ordered food IDs
            top_n: Number of recommendations to return

        Returns:
            Dictionary with recommendations or error
        """
        if not self.is_initialized:
            return {
                'status': 'error',
                'message': 'Recommendation service not initialized'
            }

        try:
            logger.info(f"Generating recommendations for user {user_id}")

            # Get recommendations from the API
            recommendations = self.api.get_recommendations(user_id, food_history, top_n)

            # Log successful recommendation generation
            if recommendations['status'] == 'success':
                logger.info(f"Generated {len(recommendations['recommendations'])} recommendations for user {user_id}")

            return recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations for user {user_id}: {e}")
            return {
                'status': 'error',
                'message': f'Failed to generate recommendations: {str(e)}',
                'user_id': user_id
            }

    def get_similar_foods(self, food_id: int, top_n: int = 5):
        """
        Get similar food items based on content features

        Args:
            food_id: Food ID to find similar items for
            top_n: Number of similar items to return

        Returns:
            Dictionary with similar foods or error
        """
        if not self.is_initialized:
            return {
                'status': 'error',
                'message': 'Recommendation service not initialized'
            }

        try:
            logger.info(f"Finding similar foods for food ID {food_id}")
            similar_foods = self.api.get_similar_foods(food_id, top_n)
            return similar_foods

        except Exception as e:
            logger.error(f"Error finding similar foods for {food_id}: {e}")
            return {
                'status': 'error',
                'message': f'Failed to find similar foods: {str(e)}',
                'food_id': food_id
            }

    def update_user_preferences(self, user_id: int, food_id: int, rating: float = None, order_count: int = 1):
        """
        Update user preferences based on new interactions
        This would be called when users rate foods or place orders

        Args:
            user_id: User ID
            food_id: Food ID
            rating: Rating given (1-5 scale)
            order_count: Number of times ordered
        """
        # In a production system, this would update the user-item matrix
        # and potentially retrain the models periodically
        logger.info(f"Updating preferences for user {user_id}: food {food_id}, rating {rating}")

        # For now, just log the interaction
        # In production, you would:
        # 1. Update the ratings database
        # 2. Update user-item matrix
        # 3. Potentially retrain models if significant new data

# Global recommendation service instance
recommendation_service = RecommendationService()

def create_recommendation_blueprint():
    """
    Create Flask Blueprint for recommendation endpoints
    This can be registered with the main Flask app
    """
    from flask import Blueprint

    recommendation_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')

    @recommendation_bp.route('/user/<int:user_id>', methods=['GET'])
    def get_user_recommendations(user_id):
        """
        Get personalized recommendations for a user
        Query parameters:
        - food_history: comma-separated list of recently ordered food IDs
        - top_n: number of recommendations (default: 5)
        """
        try:
            # Parse query parameters
            food_history_str = request.args.get('food_history', '')
            food_history = [int(x.strip()) for x in food_history_str.split(',') if x.strip()] if food_history_str else None

            top_n = int(request.args.get('top_n', 5))
            top_n = min(max(top_n, 1), 20)  # Limit between 1 and 20

            # Get recommendations
            result = recommendation_service.get_user_recommendations(user_id, food_history, top_n)

            return jsonify(result)

        except ValueError as e:
            return jsonify({
                'status': 'error',
                'message': f'Invalid parameters: {str(e)}'
            }), 400
        except Exception as e:
            logger.error(f"API error for user {user_id}: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Internal server error'
            }), 500

    @recommendation_bp.route('/food/<int:food_id>/similar', methods=['GET'])
    def get_similar_foods(food_id):
        """
        Get similar food items
        Query parameters:
        - top_n: number of similar items (default: 5)
        """
        try:
            top_n = int(request.args.get('top_n', 5))
            top_n = min(max(top_n, 1), 20)  # Limit between 1 and 20

            result = recommendation_service.get_similar_foods(food_id, top_n)
            return jsonify(result)

        except ValueError as e:
            return jsonify({
                'status': 'error',
                'message': f'Invalid parameters: {str(e)}'
            }), 400
        except Exception as e:
            logger.error(f"API error for food {food_id}: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Internal server error'
            }), 500

    @recommendation_bp.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for the recommendation service"""
        return jsonify({
            'status': 'healthy' if recommendation_service.is_initialized else 'initializing',
            'service': 'Recommendation Engine',
            'version': '1.0.0',
            'initialized': recommendation_service.is_initialized,
            'timestamp': datetime.now().isoformat()
        })

    @recommendation_bp.route('/stats', methods=['GET'])
    def get_stats():
        """Get recommendation engine statistics"""
        if not recommendation_service.is_initialized:
            return jsonify({
                'status': 'error',
                'message': 'Recommendation service not initialized'
            }), 503

        engine = recommendation_service.engine

        return jsonify({
            'status': 'success',
            'stats': {
                'total_users': len(engine.users_df) if engine.users_df is not None else 0,
                'total_foods': len(engine.food_df) if engine.food_df is not None else 0,
                'total_ratings': len(engine.ratings_df) if engine.ratings_df is not None else 0,
                'user_item_matrix_shape': engine.user_item_matrix.shape if engine.user_item_matrix is not None else None,
                'content_similarity_shape': engine.content_similarity_matrix.shape if engine.content_similarity_matrix is not None else None,
                'collaborative_similarity_shape': engine.collaborative_similarity_matrix.shape if engine.collaborative_similarity_matrix is not None else None
            },
            'model_weights': {
                'content_based': engine.content_weight,
                'collaborative': engine.collaborative_weight
            }
        })

    return recommendation_bp

# Standalone Flask app for testing the recommendation service
def create_standalone_app():
    """
    Create a standalone Flask app for testing the recommendation service
    """
    app = Flask(__name__)

    # Initialize recommendation service
    global recommendation_service
    recommendation_service.initialize()

    # Register blueprint
    recommendation_bp = create_recommendation_blueprint()
    app.register_blueprint(recommendation_bp)

    # Add CORS headers
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        return response

    @app.route('/')
    def index():
        return jsonify({
            'message': 'Smart Food Ordering - Recommendation API',
            'version': '1.0.0',
            'endpoints': {
                'GET /api/recommendations/user/<user_id>': 'Get user recommendations',
                'GET /api/recommendations/food/<food_id>/similar': 'Get similar foods',
                'GET /api/recommendations/health': 'Service health check',
                'GET /api/recommendations/stats': 'Service statistics'
            },
            'documentation': '/docs'
        })

    return app

if __name__ == '__main__':
    # Run standalone recommendation API server
    app = create_standalone_app()
    print("🚀 Starting Recommendation API Server...")
    print("📊 API Endpoints:")
    print("   • GET  /api/recommendations/user/<user_id> - User recommendations")
    print("   • GET  /api/recommendations/food/<food_id>/similar - Similar foods")
    print("   • GET  /api/recommendations/health - Health check")
    print("   • GET  /api/recommendations/stats - Statistics")
    print("\n🌐 Server running at: http://127.0.0.1:5000")

    app.run(debug=True, host='0.0.0.0', port=5000)