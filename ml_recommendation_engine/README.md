# Machine Learning Recommendation Engine

## Smart Food Ordering System - ML Component

A comprehensive machine learning recommendation system for the Smart Food Customization and Ordering System that implements multiple recommendation approaches and provides real-time personalized food recommendations.

## 🎯 Features

### Core Algorithms
- **Content-Based Filtering**: Recommends foods based on item attributes (category, cuisine, ingredients, price, etc.)
- **Collaborative Filtering**: Finds similar users and recommends based on their preferences
- **Hybrid Model**: Combines both approaches with weighted scoring for optimal recommendations
- **Cosine Similarity**: Measures similarity between users and items
- **User-Item Matrix**: Represents user preferences and interactions

### Technical Features
- **Real-time API**: Flask-based REST API for instant recommendations
- **Model Persistence**: Save/load trained models for production use
- **Scalable Architecture**: Handles growing user and food databases
- **Error Handling**: Robust error handling and logging
- **Performance Monitoring**: Built-in statistics and health checks

## 📊 Algorithm Details

### Content-Based Filtering
```
Input: Food attributes (category, cuisine, ingredients, price, spiciness)
Process: TF-IDF vectorization + Cosine similarity
Output: Similar foods based on item features
```

### Collaborative Filtering
```
Input: User-Item rating matrix
Process: User-user similarity + weighted predictions
Output: Predicted ratings for unrated items
```

### Hybrid Model
```
Input: Content scores + Collaborative scores
Process: Weighted linear combination
Output: Final recommendation score = (content_weight × content_score) + (collab_weight × collab_score)
```

## 🚀 Quick Start

### Prerequisites
```bash
Python 3.8+
pip package manager
```

### Installation
```bash
# Navigate to ML directory
cd ml_recommendation_engine

# Install dependencies
pip install -r requirements.txt
```

### Run Demonstration
```bash
# Complete demonstration with all features
python demonstrate.py

# Run standalone API server
python recommendation_api.py

# Test core engine
python recommendation_engine.py
```

## 📋 API Endpoints

### Get User Recommendations
```http
GET /api/recommendations/user/{user_id}?food_history=1,3,5&top_n=5
```

**Response:**
```json
{
  "status": "success",
  "user_id": 1,
  "recommendations": [
    {
      "food_id": 2,
      "name": "Chicken Burger",
      "category": "Burger",
      "cuisine": "American",
      "price": 8.99,
      "recommendation_score": 0.85,
      "reason": "Based on your preferences for American dishes"
    }
  ],
  "total_recommendations": 5,
  "timestamp": "2025-12-29T10:30:00",
  "model_version": "1.0.0"
}
```

### Get Similar Foods
```http
GET /api/recommendations/food/{food_id}/similar?top_n=5
```

### Health Check
```http
GET /api/recommendations/health
```

### Statistics
```http
GET /api/recommendations/stats
```

## 🧪 Sample Dataset

The system includes a comprehensive sample dataset:

- **10 Users** with demographics and cuisine preferences
- **15 Food Items** with detailed attributes
- **40+ User-Item Ratings** for training
- **Realistic food categories**: Pizza, Burger, Salad, Pasta, Curry, etc.

## 📈 Performance Metrics

### Dataset Statistics
- **Users**: 10
- **Food Items**: 15
- **Ratings**: 40
- **Sparsity**: 73.3% (typical for recommendation systems)

### Model Performance
- **Content-Based**: High precision for item similarity
- **Collaborative**: Effective for user preference prediction
- **Hybrid**: Best overall performance (60% collaborative, 40% content)

## 🎓 Viva Preparation

### Key Questions & Answers

1. **What is Content-Based Filtering?**
   - Recommends items similar to user's past preferences based on item features

2. **What is Collaborative Filtering?**
   - Uses preferences of similar users to make recommendations

3. **Why Hybrid Model?**
   - Overcomes limitations of individual approaches, handles cold start problem

4. **What is Cosine Similarity?**
   - Measures angle between vectors, ranges from -1 to 1 (1 = most similar)

5. **What is User-Item Matrix?**
   - Matrix where rows = users, columns = items, values = ratings/preferences

6. **Why Weighted Scoring?**
   - Allows balancing different recommendation approaches for optimal results

## 🏗 Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Data     │    │  Food Catalog    │    │   User Ratings  │
│   (Demographics)│    │  (Attributes)    │    │   (Preferences) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────────────┐
                    │  Feature Engineering│
                    │  • TF-IDF vectors   │
                    │  • User-Item Matrix │
                    │  • Similarity calc  │
                    └────────────────────┘
                                 │
                    ┌────────────────────┐
                    │   ML Models        │
                    │  • Content-Based   │
                    │  • Collaborative   │
                    │  • Hybrid System   │
                    └────────────────────┘
                                 │
                    ┌────────────────────┐
                    │   Prediction API   │
                    │  • REST Endpoints  │
                    │  • Real-time       │
                    │  • Error Handling  │
                    └────────────────────┘
```

## 🔧 Integration with Main System

### Android App Integration
```kotlin
// Retrofit service for recommendations
interface RecommendationService {
    @GET("api/recommendations/user/{userId}")
    suspend fun getRecommendations(
        @Path("userId") userId: Int,
        @Query("food_history") foodHistory: String,
        @Query("top_n") topN: Int = 5
    ): Response<RecommendationResponse>
}
```

### Backend Integration
```python
# Add to Flask main app
from ml_recommendation_engine.recommendation_api import create_recommendation_blueprint

recommendation_bp = create_recommendation_blueprint()
app.register_blueprint(recommendation_bp)
```

## 📊 Evaluation Metrics

- **Precision@K**: Fraction of recommended items that are relevant
- **Recall@K**: Fraction of relevant items that are recommended
- **MAP**: Mean Average Precision across all users
- **NDCG**: Normalized Discounted Cumulative Gain

## 🚀 Production Deployment

### Model Training
```bash
# Train models with production data
python -c "
from recommendation_engine import FoodRecommendationEngine
engine = FoodRecommendationEngine()
engine.train_all_models()
engine.save_models('models/production_models.pkl')
"
```

### API Deployment
```bash
# Run with Gunicorn for production
gunicorn -w 4 -b 0.0.0.0:8000 recommendation_api:create_standalone_app()
```

### Monitoring
- Health check endpoints
- Performance metrics logging
- Model accuracy tracking
- User satisfaction surveys

## 📚 Dependencies

- **pandas**: Data manipulation
- **numpy**: Numerical computations
- **scikit-learn**: ML algorithms and similarity
- **flask**: Web API framework
- **scipy**: Scientific computing

## 🎯 Future Enhancements

- **Deep Learning**: Neural collaborative filtering
- **Context-Aware**: Time-based, location-based recommendations
- **A/B Testing**: Compare different recommendation strategies
- **Real-time Learning**: Online model updates
- **Multi-modal**: Images, reviews, nutritional data

## 📄 License

B.Tech Project Implementation - Smart Food Ordering System

---

**Ready for Viva! 🎓**

This ML component demonstrates advanced understanding of:
- Machine Learning algorithms and their applications
- Recommendation system design and implementation
- API development and integration
- Performance evaluation and optimization
- Production-ready code architecture