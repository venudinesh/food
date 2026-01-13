"""
Smart Food Ordering System - CRUD Operations
============================================

Comprehensive CRUD operations for all database models:
- Users and Preferences
- Food Items and Ingredients
- Orders and Ratings
- Live Cooking Sessions

Author: B.Tech Project Implementation
Date: December 2025
"""

from models import db, User, UserPreference, Ingredient, FoodItem, FoodIngredient
from models import CustomizationOption, Order, OrderItem, Rating, CookingSession, CookingSessionParticipant
from datetime import datetime
import json
from typing import List, Dict, Optional, Any
import random
import string

class DatabaseCRUD:
    """Comprehensive CRUD operations for the food ordering system"""

    def __init__(self):
        self.db = db

    # =========================================================================
    # USER MANAGEMENT CRUD
    # =========================================================================

    def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create a new user"""
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            full_name=user_data.get('full_name'),
            phone=user_data.get('phone'),
            address=user_data.get('address'),
            date_of_birth=user_data.get('date_of_birth'),
            gender=user_data.get('gender'),
            profile_image_url=user_data.get('profile_image_url')
        )
        user.set_password(user_data['password'])

        db.session.add(user)
        db.session.commit()
        return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return User.query.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return User.query.filter_by(username=username).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return User.query.filter_by(email=email).first()

    def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Optional[User]:
        """Update user information"""
        user = User.query.get(user_id)
        if not user:
            return None

        for key, value in update_data.items():
            if key == 'password':
                user.set_password(value)
            elif hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = datetime.utcnow()
        db.session.commit()
        return user

    def delete_user(self, user_id: int) -> bool:
        """Delete user (soft delete by setting is_active=False)"""
        user = User.query.get(user_id)
        if not user:
            return False

        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return True

    def create_user_preference(self, preference_data: Dict[str, Any]) -> UserPreference:
        """Create user preferences"""
        preference = UserPreference(
            user_id=preference_data['user_id'],
            favorite_cuisines=json.dumps(preference_data.get('favorite_cuisines', [])),
            favorite_categories=json.dumps(preference_data.get('favorite_categories', [])),
            dietary_restrictions=json.dumps(preference_data.get('dietary_restrictions', [])),
            allergies=json.dumps(preference_data.get('allergies', [])),
            spice_level=preference_data.get('spice_level'),
            price_range=preference_data.get('price_range'),
            preferred_meal_times=json.dumps(preference_data.get('preferred_meal_times', [])),
            order_frequency=preference_data.get('order_frequency')
        )

        db.session.add(preference)
        db.session.commit()
        return preference

    def get_user_preferences(self, user_id: int) -> Optional[UserPreference]:
        """Get user preferences"""
        return UserPreference.query.filter_by(user_id=user_id).first()

    def update_user_preferences(self, user_id: int, preference_data: Dict[str, Any]) -> Optional[UserPreference]:
        """Update user preferences"""
        preference = UserPreference.query.filter_by(user_id=user_id).first()
        if not preference:
            preference_data['user_id'] = user_id
            return self.create_user_preference(preference_data)

        for key, value in preference_data.items():
            if key in ['favorite_cuisines', 'favorite_categories', 'dietary_restrictions',
                      'allergies', 'preferred_meal_times']:
                setattr(preference, key, json.dumps(value))
            elif hasattr(preference, key):
                setattr(preference, key, value)

        preference.updated_at = datetime.utcnow()
        db.session.commit()
        return preference

    # =========================================================================
    # FOOD AND INGREDIENTS CRUD
    # =========================================================================

    def create_ingredient(self, ingredient_data: Dict[str, Any]) -> Ingredient:
        """Create a new ingredient"""
        ingredient = Ingredient(
            name=ingredient_data['name'],
            category=ingredient_data.get('category'),
            is_vegetarian=ingredient_data.get('is_vegetarian', True),
            is_vegan=ingredient_data.get('is_vegan', True),
            is_gluten_free=ingredient_data.get('is_gluten_free', True),
            calories_per_100g=ingredient_data.get('calories_per_100g'),
            protein_per_100g=ingredient_data.get('protein_per_100g'),
            carbs_per_100g=ingredient_data.get('carbs_per_100g'),
            fat_per_100g=ingredient_data.get('fat_per_100g'),
            allergens=json.dumps(ingredient_data.get('allergens', [])),
            image_url=ingredient_data.get('image_url')
        )

        db.session.add(ingredient)
        db.session.commit()
        return ingredient

    def get_ingredient_by_id(self, ingredient_id: int) -> Optional[Ingredient]:
        """Get ingredient by ID"""
        return Ingredient.query.get(ingredient_id)

    def get_all_ingredients(self, category: str = None) -> List[Ingredient]:
        """Get all ingredients, optionally filtered by category"""
        query = Ingredient.query
        if category:
            query = query.filter_by(category=category)
        return query.all()

    def update_ingredient(self, ingredient_id: int, update_data: Dict[str, Any]) -> Optional[Ingredient]:
        """Update ingredient information"""
        ingredient = Ingredient.query.get(ingredient_id)
        if not ingredient:
            return None

        for key, value in update_data.items():
            if key == 'allergens':
                setattr(ingredient, key, json.dumps(value))
            elif hasattr(ingredient, key):
                setattr(ingredient, key, value)

        db.session.commit()
        return ingredient

    def create_food_item(self, food_data: Dict[str, Any]) -> FoodItem:
        """Create a new food item"""
        food_item = FoodItem(
            name=food_data['name'],
            description=food_data.get('description'),
            price=food_data['price'],
            image_url=food_data.get('image_url'),
            category=food_data.get('category'),
            cuisine=food_data.get('cuisine'),
            is_vegetarian=food_data.get('is_vegetarian', False),
            is_vegan=food_data.get('is_vegan', False),
            is_gluten_free=food_data.get('is_gluten_free', False),
            spice_level=food_data.get('spice_level'),
            preparation_time=food_data.get('preparation_time'),
            calories=food_data.get('calories'),
            protein=food_data.get('protein'),
            carbs=food_data.get('carbs'),
            fat=food_data.get('fat'),
            allergens=json.dumps(food_data.get('allergens', [])),
            tags=json.dumps(food_data.get('tags', []))
        )

        db.session.add(food_item)
        db.session.commit()

        # Add ingredients if provided
        if 'ingredients' in food_data:
            for ingredient_data in food_data['ingredients']:
                self.add_ingredient_to_food(food_item.id, ingredient_data)

        return food_item

    def get_food_item_by_id(self, food_id: int) -> Optional[FoodItem]:
        """Get food item by ID"""
        return FoodItem.query.get(food_id)

    def get_food_items(self, category: str = None, cuisine: str = None,
                      is_available: bool = True) -> List[FoodItem]:
        """Get food items with optional filters"""
        query = FoodItem.query.filter_by(is_available=is_available)

        if category:
            query = query.filter_by(category=category)
        if cuisine:
            query = query.filter_by(cuisine=cuisine)

        return query.all()

    def update_food_item(self, food_id: int, update_data: Dict[str, Any]) -> Optional[FoodItem]:
        """Update food item information"""
        food_item = FoodItem.query.get(food_id)
        if not food_item:
            return None

        for key, value in update_data.items():
            if key in ['allergens', 'tags']:
                setattr(food_item, key, json.dumps(value))
            elif hasattr(food_item, key):
                setattr(food_item, key, value)

        food_item.updated_at = datetime.utcnow()
        db.session.commit()
        return food_item

    def add_ingredient_to_food(self, food_id: int, ingredient_data: Dict[str, Any]) -> FoodIngredient:
        """Add ingredient to food item"""
        food_ingredient = FoodIngredient(
            food_item_id=food_id,
            ingredient_id=ingredient_data['ingredient_id'],
            quantity=ingredient_data.get('quantity'),
            is_optional=ingredient_data.get('is_optional', False)
        )

        db.session.add(food_ingredient)
        db.session.commit()
        return food_ingredient

    def create_customization_option(self, customization_data: Dict[str, Any]) -> CustomizationOption:
        """Create customization option for food item"""
        customization = CustomizationOption(
            food_item_id=customization_data['food_item_id'],
            name=customization_data['name'],
            type=customization_data['type'],
            required=customization_data.get('required', False),
            options=json.dumps(customization_data['options']),
            max_selections=customization_data.get('max_selections', 1)
        )

        db.session.add(customization)
        db.session.commit()
        return customization

    # =========================================================================
    # ORDER MANAGEMENT CRUD
    # =========================================================================

    def create_order(self, order_data: Dict[str, Any]) -> Order:
        """Create a new order"""
        # Generate unique order number
        order_number = self._generate_order_number()

        order = Order(
            user_id=order_data['user_id'],
            order_number=order_number,
            total_amount=order_data['total_amount'],
            tax_amount=order_data.get('tax_amount', 0.0),
            delivery_fee=order_data.get('delivery_fee', 0.0),
            discount_amount=order_data.get('discount_amount', 0.0),
            final_amount=order_data['final_amount'],
            payment_method=order_data.get('payment_method'),
            delivery_address=order_data['delivery_address'],
            delivery_instructions=order_data.get('delivery_instructions')
        )

        db.session.add(order)
        db.session.flush()  # Get order ID without committing

        # Add order items
        for item_data in order_data['items']:
            self.create_order_item(order.id, item_data)

        db.session.commit()
        return order

    def _generate_order_number(self) -> str:
        """Generate unique order number"""
        while True:
            order_number = f"ORD{datetime.now().strftime('%Y%m%d')}{''.join(random.choices(string.digits, k=4))}"
            if not Order.query.filter_by(order_number=order_number).first():
                return order_number

    def create_order_item(self, order_id: int, item_data: Dict[str, Any]) -> OrderItem:
        """Create order item"""
        order_item = OrderItem(
            order_id=order_id,
            food_item_id=item_data['food_item_id'],
            quantity=item_data['quantity'],
            unit_price=item_data['unit_price'],
            total_price=item_data['total_price'],
            customizations=json.dumps(item_data.get('customizations', {})),
            special_instructions=item_data.get('special_instructions')
        )

        db.session.add(order_item)
        return order_item

    def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID"""
        return Order.query.get(order_id)

    def get_user_orders(self, user_id: int, status: str = None) -> List[Order]:
        """Get orders for a user"""
        query = Order.query.filter_by(user_id=user_id)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(Order.created_at.desc()).all()

    def update_order_status(self, order_id: int, status: str) -> Optional[Order]:
        """Update order status"""
        order = Order.query.get(order_id)
        if not order:
            return None

        order.status = status
        if status == 'delivered':
            order.actual_delivery_time = datetime.utcnow()

        order.updated_at = datetime.utcnow()
        db.session.commit()
        return order

    # =========================================================================
    # RATINGS CRUD
    # =========================================================================

    def create_rating(self, rating_data: Dict[str, Any]) -> Rating:
        """Create a new rating"""
        rating = Rating(
            user_id=rating_data['user_id'],
            order_id=rating_data['order_id'],
            food_item_id=rating_data['food_item_id'],
            rating=rating_data['rating'],
            comment=rating_data.get('comment'),
            delivery_rating=rating_data.get('delivery_rating'),
            food_quality_rating=rating_data.get('food_quality_rating'),
            value_rating=rating_data.get('value_rating'),
            would_recommend=rating_data.get('would_recommend')
        )

        db.session.add(rating)
        db.session.commit()
        return rating

    def get_food_ratings(self, food_id: int) -> List[Rating]:
        """Get all ratings for a food item"""
        return Rating.query.filter_by(food_item_id=food_id).order_by(Rating.created_at.desc()).all()

    def get_average_rating(self, food_id: int) -> float:
        """Get average rating for a food item"""
        ratings = Rating.query.filter_by(food_item_id=food_id).all()
        if not ratings:
            return 0.0
        return sum(r.rating for r in ratings) / len(ratings)

    # =========================================================================
    # LIVE COOKING SESSIONS CRUD
    # =========================================================================

    def create_cooking_session(self, session_data: Dict[str, Any]) -> CookingSession:
        """Create a new cooking session"""
        session = CookingSession(
            food_item_id=session_data['food_item_id'],
            chef_id=session_data['chef_id'],
            title=session_data['title'],
            description=session_data.get('description'),
            scheduled_time=session_data['scheduled_time'],
            duration_minutes=session_data.get('duration_minutes', 30),
            max_participants=session_data.get('max_participants', 100),
            stream_url=session_data.get('stream_url'),
            thumbnail_url=session_data.get('thumbnail_url'),
            tags=json.dumps(session_data.get('tags', [])),
            difficulty_level=session_data.get('difficulty_level'),
            ingredients_needed=json.dumps(session_data.get('ingredients_needed', [])),
            equipment_needed=json.dumps(session_data.get('equipment_needed', []))
        )

        db.session.add(session)
        db.session.commit()
        return session

    def get_cooking_session_by_id(self, session_id: int) -> Optional[CookingSession]:
        """Get cooking session by ID"""
        return CookingSession.query.get(session_id)

    def get_upcoming_sessions(self) -> List[CookingSession]:
        """Get upcoming cooking sessions"""
        return CookingSession.query.filter(
            CookingSession.scheduled_time > datetime.utcnow(),
            CookingSession.status == 'scheduled'
        ).order_by(CookingSession.scheduled_time).all()

    def get_live_sessions(self) -> List[CookingSession]:
        """Get currently live cooking sessions"""
        return CookingSession.query.filter_by(status='live').all()

    def update_session_status(self, session_id: int, status: str) -> Optional[CookingSession]:
        """Update cooking session status"""
        session = CookingSession.query.get(session_id)
        if not session:
            return None

        session.status = status
        session.updated_at = datetime.utcnow()
        db.session.commit()
        return session

    def join_cooking_session(self, session_id: int, user_id: int) -> Optional[CookingSessionParticipant]:
        """Join a cooking session"""
        session = CookingSession.query.get(session_id)
        if not session or session.status not in ['scheduled', 'live']:
            return None

        if session.current_participants >= session.max_participants:
            return None

        # Check if user is already participating
        existing = CookingSessionParticipant.query.filter_by(
            cooking_session_id=session_id, user_id=user_id
        ).first()

        if existing:
            return existing

        participant = CookingSessionParticipant(
            cooking_session_id=session_id,
            user_id=user_id
        )

        session.current_participants += 1
        db.session.add(participant)
        db.session.commit()
        return participant

    def leave_cooking_session(self, session_id: int, user_id: int) -> bool:
        """Leave a cooking session"""
        participant = CookingSessionParticipant.query.filter_by(
            cooking_session_id=session_id, user_id=user_id
        ).first()

        if not participant:
            return False

        participant.left_at = datetime.utcnow()
        participant.is_active = False

        session = CookingSession.query.get(session_id)
        if session:
            session.current_participants = max(0, session.current_participants - 1)

        db.session.commit()
        return True

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        return {
            'total_users': User.query.filter_by(is_active=True).count(),
            'total_food_items': FoodItem.query.filter_by(is_available=True).count(),
            'total_orders': Order.query.count(),
            'total_ratings': Rating.query.count(),
            'active_sessions': CookingSession.query.filter_by(status='live').count(),
            'upcoming_sessions': CookingSession.query.filter(
                CookingSession.scheduled_time > datetime.utcnow(),
                CookingSession.status == 'scheduled'
            ).count()
        }

    def search_food_items(self, query: str, category: str = None) -> List[FoodItem]:
        """Search food items by name, description, or tags"""
        search_filter = f"%{query.lower()}%"
        food_items = FoodItem.query.filter(
            db.or_(
                db.func.lower(FoodItem.name).like(search_filter),
                db.func.lower(FoodItem.description).like(search_filter),
                db.func.lower(FoodItem.tags).like(search_filter)
            ),
            FoodItem.is_available == True
        )

        if category:
            food_items = food_items.filter_by(category=category)

        return food_items.all()