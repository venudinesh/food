"""
Food catalog API router
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_
from app.core.database import get_db
from app.api.auth import get_current_active_user
from app.models.user import User
from app.models.food import (
    Restaurant, Category, FoodItem, FoodItemDetail, FoodItemSummary,
    FoodSearchRequest, RestaurantSearchRequest, PaginatedResponse,
    FoodCatalogResponse, Ingredient, CookingMethod, CustomizationOption
)

router = APIRouter(prefix="/food", tags=["food-catalog"])

@router.get("/catalog", response_model=FoodCatalogResponse)
async def get_food_catalog(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user)
) -> Any:
    """Get complete food catalog with categories, popular items, and featured restaurants"""
    # Get all active categories
    categories = db.query(Category).filter(Category.is_active == True).order_by(Category.display_order).all()

    # Get popular food items (based on rating and total ratings)
    popular_items = (
        db.query(FoodItem)
        .filter(
            FoodItem.is_available == True,
            FoodItem.rating >= 4.0,
            FoodItem.total_ratings >= 10
        )
        .order_by(FoodItem.popularity_score.desc())
        .limit(20)
        .all()
    )

    # Get featured restaurants (based on rating and total ratings)
    featured_restaurants = (
        db.query(Restaurant)
        .filter(
            Restaurant.is_active == True,
            Restaurant.is_open == True,
            Restaurant.rating >= 4.0,
            Restaurant.total_ratings >= 50
        )
        .order_by(Restaurant.rating.desc())
        .limit(10)
        .all()
    )

    return {
        "categories": categories,
        "popular_items": popular_items,
        "featured_restaurants": featured_restaurants
    }

@router.get("/restaurants", response_model=PaginatedResponse)
async def search_restaurants(
    query: Optional[str] = None,
    cuisine_type: Optional[str] = None,
    city: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: Optional[float] = 10.0,  # km
    price_range: Optional[str] = None,
    min_rating: Optional[float] = None,
    sort_by: str = "distance",
    sort_order: str = "asc",
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
) -> Any:
    """Search and filter restaurants"""
    # Base query
    restaurants_query = db.query(Restaurant).filter(Restaurant.is_active == True)

    # Apply filters
    if query:
        restaurants_query = restaurants_query.filter(
            or_(
                Restaurant.name.ilike(f"%{query}%"),
                Restaurant.description.ilike(f"%{query}%"),
                Restaurant.cuisine_types.contains([query])
            )
        )

    if cuisine_type:
        restaurants_query = restaurants_query.filter(
            Restaurant.cuisine_types.contains([cuisine_type])
        )

    if city:
        restaurants_query = restaurants_query.filter(Restaurant.city == city)

    if price_range:
        restaurants_query = restaurants_query.filter(Restaurant.price_range == price_range)

    if min_rating:
        restaurants_query = restaurants_query.filter(Restaurant.rating >= min_rating)

    # Location-based filtering (simplified - in production use proper geospatial queries)
    if latitude and longitude and radius:
        # This is a simplified distance calculation
        # In production, use PostGIS or similar for accurate geospatial queries
        restaurants_query = restaurants_query.filter(
            and_(
                Restaurant.latitude.between(latitude - 0.1, latitude + 0.1),
                Restaurant.longitude.between(longitude - 0.1, longitude + 0.1)
            )
        )

    # Apply sorting
    if sort_by == "distance" and latitude and longitude:
        # Simplified distance sorting - in production use proper distance calculation
        pass  # Would need proper geospatial sorting
    elif sort_by == "rating":
        order_column = Restaurant.rating
    elif sort_by == "delivery_time":
        order_column = Restaurant.delivery_time_min
    else:
        order_column = Restaurant.name

    if sort_order == "desc":
        restaurants_query = restaurants_query.order_by(order_column.desc())
    else:
        restaurants_query = restaurants_query.order_by(order_column.asc())

    # Pagination
    total = restaurants_query.count()
    restaurants = restaurants_query.offset((page - 1) * limit).limit(limit).all()

    return {
        "items": restaurants,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "limit": limit
    }

@router.get("/restaurants/{restaurant_id}", response_model=Restaurant)
async def get_restaurant_details(
    restaurant_id: str,
    db: Session = Depends(get_db)
) -> Any:
    """Get detailed restaurant information"""
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )
    return restaurant

@router.get("/restaurants/{restaurant_id}/menu", response_model=List[FoodItemSummary])
async def get_restaurant_menu(
    restaurant_id: str,
    category: Optional[str] = None,
    is_vegetarian: Optional[bool] = None,
    is_vegan: Optional[bool] = None,
    spice_level: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    db: Session = Depends(get_db)
) -> Any:
    """Get restaurant menu with filtering options"""
    # Verify restaurant exists
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    # Base query
    menu_query = (
        db.query(FoodItem)
        .filter(
            FoodItem.restaurant_id == restaurant_id,
            FoodItem.is_available == True
        )
    )

    # Apply filters
    if category:
        menu_query = menu_query.filter(FoodItem.category_id == category)

    if is_vegetarian is not None:
        menu_query = menu_query.filter(FoodItem.is_vegetarian == is_vegetarian)

    if is_vegan is not None:
        menu_query = menu_query.filter(FoodItem.is_vegan == is_vegan)

    if spice_level:
        menu_query = menu_query.filter(FoodItem.spice_level == spice_level)

    # Apply sorting
    if sort_by == "price":
        order_column = FoodItem.price
    elif sort_by == "rating":
        order_column = FoodItem.rating
    elif sort_by == "popularity":
        order_column = FoodItem.popularity_score
    else:
        order_column = FoodItem.name

    if sort_order == "desc":
        menu_query = menu_query.order_by(order_column.desc())
    else:
        menu_query = menu_query.order_by(order_column.asc())

    return menu_query.all()

@router.get("/items", response_model=PaginatedResponse)
async def search_food_items(
    query: Optional[str] = None,
    category: Optional[str] = None,
    restaurant_id: Optional[str] = None,
    cuisine_type: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    is_vegetarian: Optional[bool] = None,
    is_vegan: Optional[bool] = None,
    spice_level: Optional[str] = None,
    sort_by: str = "popularity",
    sort_order: str = "desc",
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
) -> Any:
    """Search and filter food items"""
    # Base query with restaurant join for cuisine type filtering
    items_query = (
        db.query(FoodItem)
        .join(Restaurant)
        .filter(FoodItem.is_available == True)
    )

    # Apply filters
    if query:
        items_query = items_query.filter(
            or_(
                FoodItem.name.ilike(f"%{query}%"),
                FoodItem.description.ilike(f"%{query}%"),
                FoodItem.tags.contains([query])
            )
        )

    if category:
        items_query = items_query.filter(FoodItem.category_id == category)

    if restaurant_id:
        items_query = items_query.filter(FoodItem.restaurant_id == restaurant_id)

    if cuisine_type:
        items_query = items_query.filter(Restaurant.cuisine_types.contains([cuisine_type]))

    if price_min is not None:
        items_query = items_query.filter(FoodItem.price >= price_min)

    if price_max is not None:
        items_query = items_query.filter(FoodItem.price <= price_max)

    if is_vegetarian is not None:
        items_query = items_query.filter(FoodItem.is_vegetarian == is_vegetarian)

    if is_vegan is not None:
        items_query = items_query.filter(FoodItem.is_vegan == is_vegan)

    if spice_level:
        items_query = items_query.filter(FoodItem.spice_level == spice_level)

    # Apply sorting
    if sort_by == "price":
        order_column = FoodItem.price
    elif sort_by == "rating":
        order_column = FoodItem.rating
    elif sort_by == "name":
        order_column = FoodItem.name
    else:  # popularity
        order_column = FoodItem.popularity_score

    if sort_order == "desc":
        items_query = items_query.order_by(order_column.desc())
    else:
        items_query = items_query.order_by(order_column.asc())

    # Pagination
    total = items_query.count()
    items = items_query.offset((page - 1) * limit).limit(limit).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "limit": limit
    }

@router.get("/items/{item_id}", response_model=FoodItemDetail)
async def get_food_item_details(
    item_id: str,
    db: Session = Depends(get_db)
) -> Any:
    """Get detailed food item information with customizations"""
    item = (
        db.query(FoodItem)
        .options(
            joinedload(FoodItem.restaurant),
            joinedload(FoodItem.category),
            joinedload(FoodItem.customizations).joinedload("customization"),
            joinedload(FoodItem.ingredients),
            joinedload(FoodItem.cooking_methods)
        )
        .filter(FoodItem.id == item_id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food item not found"
        )

    # Format ingredients with quantity info
    ingredients = []
    for item_ingredient in item.ingredients:
        ingredients.append({
            "id": item_ingredient.ingredient.id,
            "name": item_ingredient.ingredient.name,
            "quantity": item_ingredient.quantity,
            "is_removable": item_ingredient.is_removable,
            "image_url": item_ingredient.ingredient.image_url
        })

    # Convert to response format
    result = FoodItemDetail.from_orm(item)
    result.ingredients = ingredients

    return result

@router.get("/categories", response_model=List[Category])
async def get_categories(
    db: Session = Depends(get_db)
) -> Any:
    """Get all active categories"""
    categories = (
        db.query(Category)
        .filter(Category.is_active == True)
        .order_by(Category.display_order)
        .all()
    )
    return categories

@router.get("/ingredients", response_model=List[Ingredient])
async def get_ingredients(
    category: Optional[str] = None,
    is_vegetarian: Optional[bool] = None,
    is_vegan: Optional[bool] = None,
    db: Session = Depends(get_db)
) -> Any:
    """Get ingredients with filtering"""
    query = db.query(Ingredient).filter(Ingredient.is_active == True)

    if category:
        query = query.filter(Ingredient.category == category)

    if is_vegetarian is not None:
        query = query.filter(Ingredient.is_vegetarian == is_vegetarian)

    if is_vegan is not None:
        query = query.filter(Ingredient.is_vegan == is_vegan)

    return query.order_by(Ingredient.name).all()

@router.get("/cooking-methods", response_model=List[CookingMethod])
async def get_cooking_methods(
    db: Session = Depends(get_db)
) -> Any:
    """Get all active cooking methods"""
    methods = (
        db.query(CookingMethod)
        .filter(CookingMethod.is_active == True)
        .order_by(CookingMethod.name)
        .all()
    )
    return methods