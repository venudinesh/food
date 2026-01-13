"""
Smart Food Ordering System - Machine Learning Recommendation Engine
===================================================================

A comprehensive recommendation system for food ordering that combines:
- Content-Based Filtering (based on food attributes)
- Collaborative Filtering (based on user behavior)
- Hybrid Model (weighted combination of both)

Features:
- Cosine similarity for finding similar items/users
- User-Item interaction matrix
- Weighted final recommendation score
- Real-time prediction API

Author: B.Tech Project Implementation
Date: December 2025
"""

import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler, MultiLabelBinarizer
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import os
from typing import List, Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class FoodRecommendationEngine:
    """
    Main recommendation engine class that implements multiple ML approaches
    for food item recommendations in the ordering system.
    """

    def __init__(self):
        """Initialize the recommendation engine with empty data structures"""
        self.user_item_matrix = None
        self.food_features = None
        self.user_profiles = None
        self.content_similarity_matrix = None
        self.collaborative_similarity_matrix = None
        self.scaler = StandardScaler()
        self.tfidf_vectorizer = TfidfVectorizer(stop_words='english')
        self.mlb = MultiLabelBinarizer()

        # Model weights for hybrid approach
        self.content_weight = 0.4
        self.collaborative_weight = 0.6

    def load_sample_data(self):
        """
        Load sample dataset for demonstration and testing
        Creates basic sample data for ML training
        """
        print("Loading sample data for ML training...")

        # Create sample users
        self.users_df = pd.DataFrame({
            'user_id': [1, 2, 3, 4, 5],
            'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
            'preferences': [['pizza', 'pasta'], ['burger', 'fries'], ['sushi', 'rice'], ['salad', 'healthy'], ['curry', 'spicy']]
        })

        # Create sample food items based on real restaurant data
        self.food_df = pd.DataFrame({
            'food_id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'name': ['Margherita Pizza', 'Chicken Burger', 'California Roll', 'Caesar Salad', 'Butter Chicken',
                    'Pepperoni Pizza', 'Veggie Burger', 'Spicy Tuna Roll', 'Greek Salad', 'Paneer Tikka'],
            'category': ['Pizza', 'Burger', 'Sushi', 'Salad', 'Curry', 'Pizza', 'Burger', 'Sushi', 'Salad', 'Curry'],
            'cuisine': ['Italian', 'American', 'Japanese', 'Mediterranean', 'Indian', 'Italian', 'American', 'Japanese', 'Mediterranean', 'Indian'],
            'price': [12.99, 8.99, 15.99, 9.99, 13.99, 14.99, 9.99, 16.99, 10.99, 11.99],
            'spiciness_level': [1, 2, 1, 1, 3, 2, 1, 4, 1, 2],  # 1-5 scale
            'preparation_time': [15, 10, 12, 8, 20, 15, 10, 12, 8, 18],  # minutes
            'is_vegetarian': [True, False, False, True, False, False, True, False, True, True],
            'ingredients': [
                ['cheese', 'tomato', 'basil'],
                ['chicken', 'lettuce', 'bun'],
                ['rice', 'nori', 'avocado'],
                ['lettuce', 'croutons', 'parmesan'],
                ['chicken', 'butter', 'spices'],
                ['pepperoni', 'cheese', 'tomato'],
                ['veggie patty', 'lettuce', 'bun'],
                ['tuna', 'spicy mayo', 'rice'],
                ['feta', 'olives', 'cucumber'],
                ['paneer', 'spices', 'yogurt']
            ],
            'restaurant_id': [1, 2, 3, 4, 5, 1, 2, 3, 4, 5]
        })

        # Create sample ratings
        self.ratings_df = pd.DataFrame({
            'user_id': [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 1, 2, 3, 4, 5],
            'food_id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 6, 7, 8, 9, 10],
            'rating': [5, 4, 3, 4, 5, 5, 4, 4, 3, 5, 4, 3, 5, 4, 5]
        })

        print(f"Loaded sample data: {len(self.users_df)} users, {len(self.food_df)} foods, {len(self.ratings_df)} ratings")
        return self.users_df, self.food_df, self.ratings_df

    def preprocess_food_features(self):
        """
        Preprocess food item features for content-based filtering
        Creates feature vectors from food attributes
        """
        print("Preprocessing food features for content-based filtering...")

        # Create feature matrix from food attributes
        food_features = self.food_df.copy().reset_index(drop=True)

        # Debug: print columns to check what's available
        print(f"Available columns: {list(food_features.columns)}")
        print(f"Sample data shape: {food_features.shape}")

        # Convert categorical features to numerical
        category_dummies = pd.get_dummies(food_features['category'], prefix='cat')
        cuisine_dummies = pd.get_dummies(food_features['cuisine'], prefix='cuisine')

        # Process ingredients using TF-IDF
        ingredients_text = food_features['ingredients'].apply(lambda x: ' '.join(x))
        ingredients_tfidf = self.tfidf_vectorizer.fit_transform(ingredients_text)
        ingredients_df = pd.DataFrame(
            ingredients_tfidf.toarray(),
            columns=[f'ingredient_{i}' for i in range(ingredients_tfidf.shape[1])]
        )

        # Scale numerical features
        numerical_features = ['price', 'spiciness_level', 'preparation_time']
        if not all(col in food_features.columns for col in numerical_features):
            print(f"Missing numerical features. Available: {list(food_features.columns)}")
            # Create default values if missing
            for col in numerical_features:
                if col not in food_features.columns:
                    food_features[col] = 1  # default value

        scaled_numerical = self.scaler.fit_transform(food_features[numerical_features])
        scaled_df = pd.DataFrame(scaled_numerical, columns=[f'scaled_{col}' for col in numerical_features])

        # Combine all features
        self.food_features = pd.concat([
            food_features[['food_id', 'is_vegetarian']].reset_index(drop=True),
            category_dummies.reset_index(drop=True),
            cuisine_dummies.reset_index(drop=True),
            ingredients_df,
            scaled_df
        ], axis=1)

        print(f"Created food feature matrix with shape: {self.food_features.shape}")
        return self.food_features

    def build_user_item_matrix(self):
        """
        Build User-Item interaction matrix for collaborative filtering
        Matrix shape: (n_users, n_items)
        """
        print("Building User-Item interaction matrix...")

        # Create pivot table: users x items with ratings
        self.user_item_matrix = self.ratings_df.pivot_table(
            index='user_id',
            columns='food_id',
            values='rating',
            fill_value=0
        )

        # Ensure all users and items are included
        all_users = self.users_df['user_id'].unique()
        all_items = self.food_df['food_id'].unique()

        self.user_item_matrix = self.user_item_matrix.reindex(
            index=all_users,
            columns=all_items,
            fill_value=0
        )

        print(f"User-Item matrix shape: {self.user_item_matrix.shape}")
        return self.user_item_matrix

    def train_content_based_model(self):
        """
        Train content-based filtering model using cosine similarity
        Finds similar items based on their features
        """
        print("Training content-based filtering model...")

        # Use food features for similarity calculation
        feature_matrix = self.food_features.drop('food_id', axis=1).values

        # Calculate cosine similarity between all food items
        self.content_similarity_matrix = cosine_similarity(feature_matrix)

        # Convert to DataFrame for easier handling
        self.content_similarity_df = pd.DataFrame(
            self.content_similarity_matrix,
            index=self.food_df['food_id'],
            columns=self.food_df['food_id']
        )

        print("Content-based model trained successfully")
        return self.content_similarity_matrix

    def train_collaborative_model(self):
        """
        Train collaborative filtering model using user-item matrix
        Finds similar users and predicts ratings
        """
        print("Training collaborative filtering model...")

        # Calculate user-user similarity matrix
        user_matrix = self.user_item_matrix.values
        self.collaborative_similarity_matrix = cosine_similarity(user_matrix)

        # Convert to DataFrame
        self.collaborative_similarity_df = pd.DataFrame(
            self.collaborative_similarity_matrix,
            index=self.user_item_matrix.index,
            columns=self.user_item_matrix.index
        )

        print("Collaborative filtering model trained successfully")
        return self.collaborative_similarity_matrix

    def get_content_based_recommendations(self, food_id: int, top_n: int = 5) -> List[Tuple[int, float]]:
        """
        Get content-based recommendations for a specific food item

        Args:
            food_id: ID of the food item to find similar items for
            top_n: Number of recommendations to return

        Returns:
            List of tuples (food_id, similarity_score)
        """
        if food_id not in self.content_similarity_df.index:
            return []

        # Get similarity scores for the given food item
        similarities = self.content_similarity_df.loc[food_id]

        # Sort by similarity (excluding the item itself)
        similar_items = similarities.drop(food_id).sort_values(ascending=False)

        # Return top N recommendations
        recommendations = [(int(idx), float(score)) for idx, score in similar_items.head(top_n).items()]
        return recommendations

    def get_collaborative_recommendations(self, user_id: int, top_n: int = 5) -> List[Tuple[int, float]]:
        """
        Get collaborative filtering recommendations for a user

        Args:
            user_id: ID of the user to generate recommendations for
            top_n: Number of recommendations to return

        Returns:
            List of tuples (food_id, predicted_rating)
        """
        if user_id not in self.collaborative_similarity_df.index:
            return []

        # Get user's ratings
        user_ratings = self.user_item_matrix.loc[user_id]

        # Find unrated items
        unrated_items = user_ratings[user_ratings == 0].index

        if len(unrated_items) == 0:
            return []

        # Get similar users
        user_similarities = self.collaborative_similarity_df.loc[user_id]

        # Calculate predicted ratings for unrated items
        predictions = {}
        for item_id in unrated_items:
            item_ratings = self.user_item_matrix[item_id]

            # Find users who rated this item
            raters = item_ratings[item_ratings > 0].index

            if len(raters) == 0:
                continue

            # Calculate weighted average rating
            similarities = user_similarities.loc[raters]
            ratings = item_ratings.loc[raters]

            # Weighted prediction
            if similarities.sum() > 0:
                predicted_rating = (similarities * ratings).sum() / similarities.sum()
                predictions[item_id] = predicted_rating

        # Sort by predicted rating
        sorted_predictions = sorted(predictions.items(), key=lambda x: x[1], reverse=True)

        return [(int(item_id), float(rating)) for item_id, rating in sorted_predictions[:top_n]]

    def get_hybrid_recommendations(self, user_id: int, food_history: List[int] = None, top_n: int = 5) -> List[Dict]:
        """
        Get hybrid recommendations combining content-based and collaborative filtering

        Args:
            user_id: ID of the user to generate recommendations for
            food_history: List of food IDs the user has interacted with recently
            top_n: Number of recommendations to return

        Returns:
            List of dictionaries with recommendation details
        """
        print(f"Generating hybrid recommendations for user {user_id}...")

        # Get collaborative filtering recommendations
        collab_recs = self.get_collaborative_recommendations(user_id, top_n * 2)

        # Get content-based recommendations based on user's food history
        content_recs = []
        if food_history:
            for food_id in food_history[:3]:  # Use last 3 items
                similar_items = self.get_content_based_recommendations(food_id, top_n // 2)
                content_recs.extend(similar_items)

        # Combine and weight recommendations
        hybrid_scores = {}

        # Add collaborative scores
        for food_id, score in collab_recs:
            hybrid_scores[food_id] = score * self.collaborative_weight

        # Add content-based scores
        for food_id, score in content_recs:
            if food_id in hybrid_scores:
                hybrid_scores[food_id] += score * self.content_weight
            else:
                hybrid_scores[food_id] = score * self.content_weight

        # Sort by final score
        sorted_recs = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)

        # Format results with food details
        recommendations = []
        for food_id, score in sorted_recs[:top_n]:
            food_info = self.food_df[self.food_df['food_id'] == food_id].iloc[0]
            recommendations.append({
                'food_id': int(food_id),
                'name': food_info['name'],
                'category': food_info['category'],
                'cuisine': food_info['cuisine'],
                'price': float(food_info['price']),
                'recommendation_score': float(score),
                'reason': self._get_recommendation_reason(food_id, score)
            })

        return recommendations

    def _get_recommendation_reason(self, food_id: int, score: float) -> str:
        """
        Generate a human-readable reason for the recommendation
        """
        food_info = self.food_df[self.food_df['food_id'] == food_id].iloc[0]

        reasons = [
            f"Based on your preferences for {food_info['category']} dishes",
            f"Similar to {food_info['cuisine']} cuisine you might enjoy",
            f"Popular choice among users with similar tastes",
            f"Recommended based on your rating history"
        ]

        return reasons[int(score * 10) % len(reasons)]

    def train_all_models(self):
        """
        Train all recommendation models
        This is the main training function that should be called to prepare the system
        """
        print("🚀 Starting comprehensive model training...")

        # Check if data is available
        if self.users_df.empty or self.food_df.empty or self.ratings_df.empty:
            print("❌ No data available for training. Please load real data from database first.")
            return False

        # Preprocess data
        self.preprocess_food_features()
        self.build_user_item_matrix()

        # Train individual models
        self.train_content_based_model()
        self.train_collaborative_model()

        print("✅ All models trained successfully!")
        print(f"📊 Dataset: {len(self.users_df)} users, {len(self.food_df)} items, {len(self.ratings_df)} ratings")
        print(".2f")
        print(".2f")
        return True

    def save_models(self, filepath: str = 'recommendation_models.pkl'):
        """
        Save trained models to disk for later use
        """
        models_data = {
            'user_item_matrix': self.user_item_matrix,
            'food_features': self.food_features,
            'content_similarity_matrix': self.content_similarity_matrix,
            'content_similarity_df': self.content_similarity_df,
            'collaborative_similarity_matrix': self.collaborative_similarity_matrix,
            'collaborative_similarity_df': self.collaborative_similarity_df,
            'food_df': self.food_df,
            'users_df': self.users_df,
            'ratings_df': self.ratings_df,
            'scaler': self.scaler,
            'tfidf_vectorizer': self.tfidf_vectorizer
        }

        with open(filepath, 'wb') as f:
            pickle.dump(models_data, f)

        print(f"Models saved to {filepath}")

    def load_models(self, filepath: str = 'recommendation_models.pkl'):
        """
        Load trained models from disk
        """
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                models_data = pickle.load(f)

            self.user_item_matrix = models_data['user_item_matrix']
            self.food_features = models_data['food_features']
            self.content_similarity_matrix = models_data['content_similarity_matrix']
            self.content_similarity_df = models_data.get('content_similarity_df')
            self.collaborative_similarity_matrix = models_data['collaborative_similarity_matrix']
            self.collaborative_similarity_df = models_data.get('collaborative_similarity_df')
            self.food_df = models_data['food_df']
            self.users_df = models_data['users_df']
            self.ratings_df = models_data['ratings_df']
            self.scaler = models_data['scaler']
            self.tfidf_vectorizer = models_data['tfidf_vectorizer']

            print(f"Models loaded from {filepath}")
            return True
        else:
            print(f"Model file {filepath} not found")
            return False

# Prediction API Class
class RecommendationAPI:
    """
    API class for serving recommendations
    This would be integrated with the Flask backend
    """

    def __init__(self, engine: FoodRecommendationEngine):
        self.engine = engine

    def get_recommendations(self, user_id: int, food_history: List[int] = None, top_n: int = 5) -> Dict:
        """
        API endpoint for getting personalized recommendations

        Args:
            user_id: User ID to generate recommendations for
            food_history: Recent food interactions (optional)
            top_n: Number of recommendations to return

        Returns:
            Dictionary with recommendations and metadata
        """
        try:
            recommendations = self.engine.get_hybrid_recommendations(user_id, food_history, top_n)

            return {
                'status': 'success',
                'user_id': user_id,
                'recommendations': recommendations,
                'total_recommendations': len(recommendations),
                'timestamp': pd.Timestamp.now().isoformat(),
                'model_version': '1.0.0'
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'user_id': user_id
            }

    def get_similar_foods(self, food_id: int, top_n: int = 5) -> Dict:
        """
        API endpoint for getting similar food items

        Args:
            food_id: Food ID to find similar items for
            top_n: Number of similar items to return

        Returns:
            Dictionary with similar foods
        """
        try:
            similar_foods = self.engine.get_content_based_recommendations(food_id, top_n)

            # Get food details
            similar_food_details = []
            for food_id_sim, score in similar_foods:
                food_info = self.engine.food_df[self.engine.food_df['food_id'] == food_id_sim].iloc[0]
                similar_food_details.append({
                    'food_id': int(food_id_sim),
                    'name': food_info['name'],
                    'category': food_info['category'],
                    'similarity_score': float(score)
                })

            return {
                'status': 'success',
                'original_food_id': food_id,
                'similar_foods': similar_food_details,
                'total_similar': len(similar_food_details)
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'food_id': food_id
            }

# Main execution and demonstration
def main():
    """
    Main function to demonstrate the recommendation engine
    This includes training, testing, and API demonstration
    """
    print("=" * 70)
    print("🍕 SMART FOOD ORDERING - ML RECOMMENDATION ENGINE")
    print("=" * 70)

    # Initialize the recommendation engine
    engine = FoodRecommendationEngine()

    # Train all models
    engine.train_all_models()

    # Initialize API
    api = RecommendationAPI(engine)

    print("\n" + "=" * 50)
    print("🧪 TESTING RECOMMENDATION SYSTEM")
    print("=" * 50)

    # Test 1: Get recommendations for a user
    print("\n📋 Test 1: Hybrid Recommendations for User 1")
    user_recs = api.get_recommendations(user_id=1, food_history=[1, 3, 4], top_n=3)
    if user_recs['status'] == 'success':
        for i, rec in enumerate(user_recs['recommendations'], 1):
            print(f"{i}. {rec['name']} ({rec['category']}) - Score: {rec['recommendation_score']:.2f}")
            print(f"   Reason: {rec['reason']}")

    # Test 2: Get similar foods
    print("\n📋 Test 2: Similar Foods to Margherita Pizza")
    similar_foods = api.get_similar_foods(food_id=1, top_n=3)
    if similar_foods['status'] == 'success':
        for i, food in enumerate(similar_foods['similar_foods'], 1):
            print(f"{i}. {food['name']} ({food['category']}) - Similarity: {food['similarity_score']:.2f}")

    # Test 3: Content-based recommendations
    print("\n📋 Test 3: Content-Based Recommendations for Caesar Salad")
    content_recs = engine.get_content_based_recommendations(3, 3)
    for i, (food_id, score) in enumerate(content_recs, 1):
        food_name = engine.food_df[engine.food_df['food_id'] == food_id]['name'].iloc[0]
        print(f"{i}. {food_name} - Similarity: {score:.2f}")

    # Test 4: Collaborative recommendations
    print("\n📋 Test 4: Collaborative Recommendations for User 2")
    collab_recs = engine.get_collaborative_recommendations(2, 3)
    for i, (food_id, score) in enumerate(collab_recs, 1):
        food_name = engine.food_df[engine.food_df['food_id'] == food_id]['name'].iloc[0]
        print(f"{i}. {food_name} - Predicted Rating: {score:.2f}")

    # Save models for future use
    engine.save_models()

    print("\n" + "=" * 50)
    print("✅ RECOMMENDATION ENGINE DEMONSTRATION COMPLETE")
    print("=" * 50)
    print("\n🎯 Key Features Demonstrated:")
    print("   • Content-Based Filtering using food attributes")
    print("   • Collaborative Filtering using user-item matrix")
    print("   • Hybrid Model combining both approaches")
    print("   • Cosine Similarity for finding similar items/users")
    print("   • Weighted scoring for final recommendations")
    print("   • REST API endpoints for real-time predictions")
    print("\n📊 Model Performance:")
    print(".2f")
    print(".2f")
    print(f"   • Total Users: {len(engine.users_df)}")
    print(f"   • Total Food Items: {len(engine.food_df)}")
    print(f"   • Total Ratings: {len(engine.ratings_df)}")

if __name__ == "__main__":
    main()