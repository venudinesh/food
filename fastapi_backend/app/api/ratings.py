"""
Ratings and feedback API router
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from app.core.database import get_db
from app.api.auth import get_current_active_user
from app.models.user import User
from app.models.rating import (
    Rating, RatingCreate, RatingUpdate, RatingSummary, RatingStats,
    RatingSearchRequest, RatingResponse, RatingImage, RatingAnalytics,
    RestaurantRatingStats, FoodItemRatingStats
)
from app.models.order import Order, OrderStatus

router = APIRouter(prefix="/ratings", tags=["ratings"])

@router.post("/", response_model=Rating)
async def create_rating(
    rating_data: RatingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create a new rating for an order"""
    # Validate order exists and belongs to user
    order = db.query(Order).filter(
        Order.id == rating_data.order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Check if order is delivered (only allow rating after delivery)
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only rate delivered orders"
        )

    # Check if rating already exists
    existing_rating = db.query(Rating).filter(
        Rating.order_id == rating_data.order_id,
        Rating.user_id == current_user.id
    ).first()

    if existing_rating:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating already exists for this order"
        )

    # Create rating
    rating = Rating(
        user_id=current_user.id,
        order_id=rating_data.order_id,
        restaurant_id=rating_data.restaurant_id,
        food_item_id=rating_data.food_item_id,
        overall_rating=rating_data.overall_rating,
        food_quality_rating=rating_data.food_quality_rating,
        delivery_rating=rating_data.delivery_rating,
        value_rating=rating_data.value_rating,
        review_title=rating_data.review_title,
        review_text=rating_data.review_text,
        pros=rating_data.pros,
        cons=rating_data.cons,
        tags=rating_data.tags,
        is_verified_purchase=True,
        is_recommended=rating_data.is_recommended,
        would_order_again=rating_data.would_order_again
    )

    db.add(rating)
    db.flush()  # Get rating ID

    # Add images if provided
    for image_data in rating_data.images:
        rating_image = RatingImage(
            rating_id=rating.id,
            image_url=image_data.image_url,
            image_type=image_data.image_type,
            caption=image_data.caption
        )
        db.add(rating_image)

    db.commit()
    db.refresh(rating)

    # Update restaurant/food item ratings (background task in production)
    await update_aggregate_ratings(rating.restaurant_id, rating.food_item_id, db)

    return rating

async def update_aggregate_ratings(restaurant_id: str, food_item_id: Optional[str], db: Session):
    """Update aggregate ratings for restaurant and food item"""
    # Update restaurant rating
    restaurant_ratings = (
        db.query(
            func.avg(Rating.overall_rating).label('avg_rating'),
            func.count(Rating.id).label('total_ratings')
        )
        .filter(Rating.restaurant_id == restaurant_id)
        .first()
    )

    if restaurant_ratings.avg_rating:
        db.query(Restaurant).filter(Restaurant.id == restaurant_id).update({
            "rating": round(restaurant_ratings.avg_rating, 1),
            "total_ratings": restaurant_ratings.total_ratings
        })

    # Update food item rating if provided
    if food_item_id:
        food_ratings = (
            db.query(
                func.avg(Rating.overall_rating).label('avg_rating'),
                func.count(Rating.id).label('total_ratings')
            )
            .filter(Rating.food_item_id == food_item_id)
            .first()
        )

        if food_ratings.avg_rating:
            db.query(FoodItem).filter(FoodItem.id == food_item_id).update({
                "rating": round(food_ratings.avg_rating, 1),
                "total_ratings": food_ratings.total_ratings
            })

    db.commit()

@router.get("/", response_model=List[RatingSummary])
async def get_user_ratings(
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user's ratings"""
    ratings = (
        db.query(Rating)
        .options(
            joinedload(Rating.responses),
            joinedload(Rating.images)
        )
        .filter(Rating.user_id == current_user.id)
        .order_by(Rating.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return ratings

@router.get("/{rating_id}", response_model=Rating)
async def get_rating_details(
    rating_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get detailed rating information"""
    rating = (
        db.query(Rating)
        .options(
            joinedload(Rating.responses),
            joinedload(Rating.images)
        )
        .filter(
            Rating.id == rating_id,
            Rating.user_id == current_user.id
        )
        .first()
    )

    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found"
        )

    return rating

@router.put("/{rating_id}", response_model=Rating)
async def update_rating(
    rating_id: str,
    rating_update: RatingUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update user's rating"""
    rating = db.query(Rating).filter(
        Rating.id == rating_id,
        Rating.user_id == current_user.id
    ).first()

    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found"
        )

    # Update fields
    update_data = rating_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rating, field, value)

    rating.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rating)

    # Update aggregate ratings
    await update_aggregate_ratings(rating.restaurant_id, rating.food_item_id, db)

    return rating

@router.delete("/{rating_id}")
async def delete_rating(
    rating_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete user's rating"""
    rating = db.query(Rating).filter(
        Rating.id == rating_id,
        Rating.user_id == current_user.id
    ).first()

    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found"
        )

    # Soft delete by marking as inactive (or hard delete)
    db.delete(rating)
    db.commit()

    # Update aggregate ratings
    await update_aggregate_ratings(rating.restaurant_id, rating.food_item_id, db)

    return {"message": "Rating deleted successfully"}

@router.get("/restaurant/{restaurant_id}", response_model=List[RatingSummary])
async def get_restaurant_ratings(
    restaurant_id: str,
    min_rating: Optional[float] = None,
    has_review: Optional[bool] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
) -> Any:
    """Get ratings for a restaurant"""
    query = (
        db.query(Rating)
        .options(
            joinedload(Rating.responses),
            joinedload(Rating.images)
        )
        .filter(Rating.restaurant_id == restaurant_id)
    )

    if min_rating:
        query = query.filter(Rating.overall_rating >= min_rating)

    if has_review is not None:
        if has_review:
            query = query.filter(Rating.review_text.isnot(None))
        else:
            query = query.filter(Rating.review_text.is_(None))

    # Apply sorting
    if sort_by == "rating":
        order_column = Rating.overall_rating
    elif sort_by == "helpful":
        # Would need to calculate helpful score
        order_column = Rating.created_at
    else:  # created_at
        order_column = Rating.created_at

    if sort_order == "desc":
        query = query.order_by(order_column.desc())
    else:
        query = query.order_by(order_column.asc())

    ratings = query.offset((page - 1) * limit).limit(limit).all()

    return ratings

@router.get("/restaurant/{restaurant_id}/stats", response_model=RestaurantRatingStats)
async def get_restaurant_rating_stats(
    restaurant_id: str,
    db: Session = Depends(get_db)
) -> Any:
    """Get rating statistics for a restaurant"""
    ratings = db.query(Rating).filter(Rating.restaurant_id == restaurant_id).all()

    if not ratings:
        return RestaurantRatingStats(
            restaurant_id=restaurant_id,
            restaurant_name="",
            total_ratings=0,
            average_rating=0.0,
            rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            recommended_percentage=0.0,
            would_order_again_percentage=0.0,
            common_tags=[],
            recent_ratings=[]
        )

    # Calculate statistics
    total_ratings = len(ratings)
    average_rating = sum(r.overall_rating for r in ratings) / total_ratings

    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for rating in ratings:
        rating_distribution[int(rating.overall_rating)] += 1

    recommended_count = sum(1 for r in ratings if r.is_recommended)
    would_order_again_count = sum(1 for r in ratings if r.would_order_again)

    # Common tags (simplified)
    all_tags = []
    for rating in ratings:
        all_tags.extend(rating.tags or [])

    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    common_tags = [
        {"tag": tag, "count": count}
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    # Recent ratings
    recent_ratings = ratings[-5:] if len(ratings) > 5 else ratings

    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()

    return RestaurantRatingStats(
        restaurant_id=restaurant_id,
        restaurant_name=restaurant.name if restaurant else "",
        total_ratings=total_ratings,
        average_rating=round(average_rating, 1),
        rating_distribution=rating_distribution,
        food_quality_avg=sum(r.food_quality_rating or 0 for r in ratings if r.food_quality_rating) / sum(1 for r in ratings if r.food_quality_rating) if any(r.food_quality_rating for r in ratings) else None,
        delivery_avg=sum(r.delivery_rating or 0 for r in ratings if r.delivery_rating) / sum(1 for r in ratings if r.delivery_rating) if any(r.delivery_rating for r in ratings) else None,
        value_avg=sum(r.value_rating or 0 for r in ratings if r.value_rating) / sum(1 for r in ratings if r.value_rating) if any(r.value_rating for r in ratings) else None,
        recommended_percentage=round((recommended_count / total_ratings) * 100, 1),
        would_order_again_percentage=round((would_order_again_count / total_ratings) * 100, 1),
        common_tags=common_tags,
        recent_ratings=recent_ratings
    )

@router.post("/{rating_id}/response", response_model=RatingResponse)
async def respond_to_rating(
    rating_id: str,
    response_text: str,
    db: Session = Depends(get_db)
) -> Any:
    """Add response to a rating (restaurant/admin endpoint)"""
    rating = db.query(Rating).filter(Rating.id == rating_id).first()

    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found"
        )

    # In a real implementation, check if user is restaurant owner/admin
    response = RatingResponse(
        rating_id=rating_id,
        responder_id="restaurant_admin",  # Would be actual user ID
        responder_type="restaurant",
        response_text=response_text
    )

    db.add(response)
    db.commit()
    db.refresh(response)

    return response

@router.post("/{rating_id}/helpful/{response_id}")
async def mark_response_helpful(
    rating_id: str,
    response_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Mark a rating response as helpful"""
    response = db.query(RatingResponse).filter(
        RatingResponse.id == response_id,
        RatingResponse.rating_id == rating_id
    ).first()

    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Response not found"
        )

    response.helpful_count += 1
    db.commit()

    return {"message": "Response marked as helpful"}

@router.get("/food-item/{food_item_id}/stats", response_model=FoodItemRatingStats)
async def get_food_item_rating_stats(
    food_item_id: str,
    db: Session = Depends(get_db)
) -> Any:
    """Get rating statistics for a food item"""
    ratings = db.query(Rating).filter(Rating.food_item_id == food_item_id).all()

    if not ratings:
        return FoodItemRatingStats(
            food_item_id=food_item_id,
            food_item_name="",
            total_ratings=0,
            average_rating=0.0,
            rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            recommended_percentage=0.0,
            would_order_again_percentage=0.0,
            common_tags=[],
            recent_ratings=[]
        )

    # Similar calculations as restaurant stats
    total_ratings = len(ratings)
    average_rating = sum(r.overall_rating for r in ratings) / total_ratings

    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for rating in ratings:
        rating_distribution[int(rating.overall_rating)] += 1

    recommended_count = sum(1 for r in ratings if r.is_recommended)
    would_order_again_count = sum(1 for r in ratings if r.would_order_again)

    all_tags = []
    for rating in ratings:
        all_tags.extend(rating.tags or [])

    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    common_tags = [
        {"tag": tag, "count": count}
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    recent_ratings = ratings[-5:] if len(ratings) > 5 else ratings

    food_item = db.query(FoodItem).filter(FoodItem.id == food_item_id).first()

    return FoodItemRatingStats(
        food_item_id=food_item_id,
        food_item_name=food_item.name if food_item else "",
        total_ratings=total_ratings,
        average_rating=round(average_rating, 1),
        rating_distribution=rating_distribution,
        recommended_percentage=round((recommended_count / total_ratings) * 100, 1),
        would_order_again_percentage=round((would_order_again_count / total_ratings) * 100, 1),
        common_tags=common_tags,
        recent_ratings=recent_ratings
    )

# Import required modules
from datetime import datetime
from app.models.food import Restaurant, FoodItem