import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
from app.models.rating import Rating, RatingStats
from app import db

class RatingsAnalysisService:
    """Service for analyzing ratings data for ML and business intelligence"""

    @staticmethod
    def get_ratings_dataframe(target_id: str = None, rating_type: str = None,
                            days_back: int = 30) -> pd.DataFrame:
        """Get ratings data as pandas DataFrame for ML processing"""

        query = Rating.query

        if target_id:
            field_name = f'{rating_type.lower()}_id'
            query = query.filter_by(**{field_name: target_id})

        # Filter by date range
        start_date = datetime.utcnow() - timedelta(days=days_back)
        query = query.filter(Rating.timestamp >= start_date)

        ratings = query.all()

        # Convert to DataFrame
        data = []
        for rating in ratings:
            data.append({
                'rating_id': rating.id,
                'user_id': rating.user_id,
                'target_id': getattr(rating, f'{rating.rating_type.lower()}_id'),
                'rating_type': rating.rating_type,
                'rating': rating.rating,
                'feedback_text': rating.feedback_text or '',
                'timestamp': rating.timestamp,
                'is_anonymous': rating.is_anonymous,
                'helpful_votes': rating.helpful_votes,
                'tags': ','.join(rating.tags) if rating.tags else '',
                'feedback_length': len(rating.feedback_text or ''),
                'has_feedback': 1 if rating.feedback_text else 0,
                'tag_count': len(rating.tags) if rating.tags else 0
            })

        return pd.DataFrame(data)

    @staticmethod
    def analyze_sentiment(ratings_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze sentiment patterns in ratings"""

        if ratings_df.empty:
            return {'error': 'No data available'}

        # Basic sentiment analysis based on rating scores
        sentiment_map = {
            'very_negative': ratings_df[ratings_df['rating'] <= 2],
            'negative': ratings_df[(ratings_df['rating'] > 2) & (ratings_df['rating'] <= 3)],
            'neutral': ratings_df[ratings_df['rating'] == 3],
            'positive': ratings_df[(ratings_df['rating'] > 3) & (ratings_df['rating'] <= 4)],
            'very_positive': ratings_df[ratings_df['rating'] == 5]
        }

        sentiment_stats = {}
        for sentiment, df in sentiment_map.items():
            sentiment_stats[sentiment] = {
                'count': len(df),
                'percentage': len(df) / len(ratings_df) * 100 if len(ratings_df) > 0 else 0,
                'avg_feedback_length': df['feedback_length'].mean() if len(df) > 0 else 0
            }

        return {
            'total_ratings': len(ratings_df),
            'average_rating': ratings_df['rating'].mean(),
            'sentiment_distribution': sentiment_stats,
            'feedback_rate': ratings_df['has_feedback'].mean() * 100,
            'avg_feedback_length': ratings_df['feedback_length'].mean()
        }

    @staticmethod
    def extract_common_tags(ratings_df: pd.DataFrame, min_occurrences: int = 3) -> List[Dict[str, Any]]:
        """Extract commonly used tags from ratings"""

        all_tags = []
        for tags_str in ratings_df['tags']:
            if tags_str:
                all_tags.extend([tag.strip() for tag in tags_str.split(',')])

        if not all_tags:
            return []

        # Count tag frequencies
        tag_counts = pd.Series(all_tags).value_counts()

        # Filter tags that appear at least min_occurrences times
        common_tags = tag_counts[tag_counts >= min_occurrences]

        return [
            {
                'tag': tag,
                'count': count,
                'percentage': count / len(ratings_df) * 100
            }
            for tag, count in common_tags.items()
        ]

    @staticmethod
    def generate_rating_insights(target_id: str, rating_type: str) -> Dict[str, Any]:
        """Generate comprehensive insights for a target"""

        # Get ratings data
        df = RatingsAnalysisService.get_ratings_dataframe(target_id, rating_type)

        if df.empty:
            return {'error': 'No ratings data available'}

        # Basic statistics
        basic_stats = {
            'total_ratings': len(df),
            'average_rating': round(df['rating'].mean(), 2),
            'rating_distribution': df['rating'].value_counts().sort_index().to_dict(),
            'feedback_rate': round(df['has_feedback'].mean() * 100, 2)
        }

        # Sentiment analysis
        sentiment = RatingsAnalysisService.analyze_sentiment(df)

        # Common tags
        common_tags = RatingsAnalysisService.extract_common_tags(df)

        # Time-based analysis
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['date_only'] = df['date'].dt.date

        daily_ratings = df.groupby('date_only').agg({
            'rating': ['count', 'mean'],
            'has_feedback': 'mean'
        }).round(2)

        # Rating trends
        rating_trend = daily_ratings['rating']['mean'].rolling(window=7).mean().round(2).to_dict()

        return {
            'basic_stats': basic_stats,
            'sentiment_analysis': sentiment,
            'common_tags': common_tags,
            'daily_stats': daily_ratings.to_dict(),
            'rating_trend': rating_trend,
            'insights': RatingsAnalysisService._generate_insights(df, basic_stats)
        }

    @staticmethod
    def _generate_insights(df: pd.DataFrame, basic_stats: Dict) -> List[str]:
        """Generate human-readable insights"""

        insights = []

        avg_rating = basic_stats['average_rating']

        # Rating quality insight
        if avg_rating >= 4.5:
            insights.append("Excellent performance with very high customer satisfaction")
        elif avg_rating >= 4.0:
            insights.append("Good performance with high customer satisfaction")
        elif avg_rating >= 3.5:
            insights.append("Average performance - room for improvement")
        else:
            insights.append("Below average performance - significant improvements needed")

        # Feedback rate insight
        feedback_rate = basic_stats['feedback_rate']
        if feedback_rate > 70:
            insights.append("High feedback engagement - customers are vocal about their experience")
        elif feedback_rate > 40:
            insights.append("Moderate feedback engagement")
        else:
            insights.append("Low feedback engagement - consider encouraging more reviews")

        # Rating consistency
        rating_std = df['rating'].std()
        if rating_std < 0.5:
            insights.append("Consistent ratings indicate reliable performance")
        elif rating_std > 1.0:
            insights.append("Highly variable ratings suggest inconsistent quality")

        # Tag analysis
        if len(df) > 10:
            positive_tags = df[df['rating'] >= 4]['tags'].str.split(',').explode().value_counts()
            negative_tags = df[df['rating'] <= 2]['tags'].str.split(',').explode().value_counts()

            if not positive_tags.empty:
                top_positive = positive_tags.index[0]
                insights.append(f"Customers frequently praise: {top_positive}")

            if not negative_tags.empty:
                top_negative = negative_tags.index[0]
                insights.append(f"Common complaints about: {top_negative}")

        return insights

    @staticmethod
    def export_ratings_for_ml(target_id: str = None, rating_type: str = None,
                            output_path: str = None) -> str:
        """Export ratings data in ML-ready format"""

        df = RatingsAnalysisService.get_ratings_dataframe(target_id, rating_type)

        if df.empty:
            return "No data to export"

        # Prepare ML features
        ml_df = df.copy()

        # Convert timestamp to useful features
        ml_df['hour'] = pd.to_datetime(ml_df['timestamp'], unit='ms').dt.hour
        ml_df['day_of_week'] = pd.to_datetime(ml_df['timestamp'], unit='ms').dt.dayofweek
        ml_df['month'] = pd.to_datetime(ml_df['timestamp'], unit='ms').dt.month

        # Text features (basic for now - can be enhanced with NLP)
        ml_df['feedback_word_count'] = ml_df['feedback_text'].str.split().str.len()

        # One-hot encode tags (simplified)
        if 'tags' in ml_df.columns:
            # This is a simplified version - in production, use proper multi-label encoding
            ml_df['has_positive_tags'] = ml_df['tags'].str.contains('tasty|fresh|hot|fast|friendly', case=False, na=False).astype(int)
            ml_df['has_negative_tags'] = ml_df['tags'].str.contains('cold|slow|tasteless|late|rude', case=False, na=False).astype(int)

        # Select relevant columns for ML
        ml_features = [
            'rating', 'feedback_word_count', 'has_feedback', 'tag_count',
            'hour', 'day_of_week', 'month', 'helpful_votes',
            'has_positive_tags', 'has_negative_tags'
        ]

        ml_export = ml_df[ml_features]

        if output_path:
            ml_export.to_csv(output_path, index=False)
            return f"Data exported to {output_path}"

        return ml_export.to_csv(index=False)