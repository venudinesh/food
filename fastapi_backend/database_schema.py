"""
Smart Food Customization and Ordering System - Database Schema
===============================================================

Complete database schema documentation for the food ordering system.

Tables:
- Users & Preferences
- Food Items & Ingredients
- Orders & Ratings
- Live Cooking Sessions

Author: B.Tech Project Implementation
Date: December 2025
"""

DATABASE_SCHEMA_SQL = """
-- Smart Food Ordering System Database Schema
-- SQLite compatible

-- =============================================================================
-- USER MANAGEMENT TABLES
-- =============================================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    full_name VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    date_of_birth DATE,
    gender VARCHAR(10), -- 'male', 'female', 'other'
    profile_image_url VARCHAR(200),
    is_active BOOLEAN DEFAULT 1,
    email_verified BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    favorite_cuisines TEXT, -- JSON array of cuisine types
    favorite_categories TEXT, -- JSON array of food categories
    dietary_restrictions TEXT, -- JSON array: ['vegetarian', 'vegan', 'gluten_free', etc.]
    allergies TEXT, -- JSON array of allergens
    spice_level VARCHAR(20), -- 'mild', 'medium', 'hot', 'very_hot'
    price_range VARCHAR(20), -- 'budget', 'moderate', 'premium'
    preferred_meal_times TEXT, -- JSON array: ['breakfast', 'lunch', 'dinner', 'snacks']
    order_frequency VARCHAR(20), -- 'daily', 'weekly', 'monthly', 'occasional'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- =============================================================================
-- FOOD AND INGREDIENTS TABLES
-- =============================================================================

-- Ingredients table
CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50), -- 'vegetable', 'protein', 'dairy', 'grain', 'spice', 'other'
    is_vegetarian BOOLEAN DEFAULT 1,
    is_vegan BOOLEAN DEFAULT 1,
    is_gluten_free BOOLEAN DEFAULT 1,
    calories_per_100g FLOAT,
    protein_per_100g FLOAT,
    carbs_per_100g FLOAT,
    fat_per_100g FLOAT,
    allergens TEXT, -- JSON array of allergens
    image_url VARCHAR(200),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Food items table
CREATE TABLE IF NOT EXISTS food_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price FLOAT NOT NULL,
    image_url VARCHAR(200),
    category VARCHAR(50), -- 'pizza', 'burger', 'pasta', 'salad', 'dessert', etc.
    cuisine VARCHAR(50), -- 'italian', 'american', 'indian', 'chinese', etc.
    is_available BOOLEAN DEFAULT 1,
    is_vegetarian BOOLEAN DEFAULT 0,
    is_vegan BOOLEAN DEFAULT 0,
    is_gluten_free BOOLEAN DEFAULT 0,
    spice_level VARCHAR(20), -- 'mild', 'medium', 'hot', 'very_hot'
    preparation_time INTEGER, -- in minutes
    calories INTEGER,
    protein FLOAT,
    carbs FLOAT,
    fat FLOAT,
    allergens TEXT, -- JSON array of allergens
    tags TEXT, -- JSON array of tags for search
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Food ingredients junction table
CREATE TABLE IF NOT EXISTS food_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    food_item_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    quantity FLOAT, -- in grams
    is_optional BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (food_item_id) REFERENCES food_items(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE,
    UNIQUE(food_item_id, ingredient_id)
);

-- Customization options table
CREATE TABLE IF NOT EXISTS customization_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    food_item_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL, -- e.g., 'Size', 'Toppings', 'Sauce'
    type VARCHAR(20) NOT NULL, -- 'single', 'multiple', 'quantity'
    required BOOLEAN DEFAULT 0,
    options TEXT NOT NULL, -- JSON string of options with prices
    max_selections INTEGER DEFAULT 1, -- For multiple selection type
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (food_item_id) REFERENCES food_items(id) ON DELETE CASCADE
);

-- =============================================================================
-- ORDER MANAGEMENT TABLES
-- =============================================================================

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    order_number VARCHAR(20) UNIQUE NOT NULL,
    total_amount FLOAT NOT NULL,
    tax_amount FLOAT DEFAULT 0.0,
    delivery_fee FLOAT DEFAULT 0.0,
    discount_amount FLOAT DEFAULT 0.0,
    final_amount FLOAT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled'
    payment_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'paid', 'failed', 'refunded'
    payment_method VARCHAR(50),
    delivery_address TEXT NOT NULL,
    delivery_instructions TEXT,
    estimated_delivery_time DATETIME,
    actual_delivery_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Order items table
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    food_item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price FLOAT NOT NULL,
    total_price FLOAT NOT NULL,
    customizations TEXT, -- JSON string of selected customizations
    special_instructions TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (food_item_id) REFERENCES food_items(id)
);

-- =============================================================================
-- RATINGS AND REVIEWS TABLES
-- =============================================================================

-- Ratings table
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    order_id INTEGER NOT NULL,
    food_item_id INTEGER NOT NULL,
    rating INTEGER NOT NULL, -- 1-5 stars
    comment TEXT,
    delivery_rating INTEGER, -- 1-5 stars for delivery service
    food_quality_rating INTEGER, -- 1-5 stars for food quality
    value_rating INTEGER, -- 1-5 stars for value for money
    would_recommend BOOLEAN,
    is_verified_purchase BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (food_item_id) REFERENCES food_items(id),
    UNIQUE(user_id, order_id, food_item_id)
);

-- =============================================================================
-- LIVE COOKING SESSIONS TABLES
-- =============================================================================

-- Cooking sessions table
CREATE TABLE IF NOT EXISTS cooking_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    food_item_id INTEGER NOT NULL,
    chef_id INTEGER NOT NULL, -- Chef conducting the session
    title VARCHAR(200) NOT NULL,
    description TEXT,
    scheduled_time DATETIME NOT NULL,
    duration_minutes INTEGER DEFAULT 30,
    max_participants INTEGER DEFAULT 100,
    current_participants INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'scheduled', -- 'scheduled', 'live', 'completed', 'cancelled'
    stream_url VARCHAR(500), -- URL for live streaming
    recording_url VARCHAR(500), -- URL for recorded session
    thumbnail_url VARCHAR(200),
    tags TEXT, -- JSON array of session tags
    difficulty_level VARCHAR(20), -- 'beginner', 'intermediate', 'advanced'
    ingredients_needed TEXT, -- JSON array of required ingredients
    equipment_needed TEXT, -- JSON array of required equipment
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (food_item_id) REFERENCES food_items(id),
    FOREIGN KEY (chef_id) REFERENCES users(id)
);

-- Cooking session participants table
CREATE TABLE IF NOT EXISTS cooking_session_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cooking_session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    left_at DATETIME,
    is_active BOOLEAN DEFAULT 1,
    engagement_score FLOAT DEFAULT 0.0, -- Based on interactions, questions asked, etc.
    FOREIGN KEY (cooking_session_id) REFERENCES cooking_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(cooking_session_id, user_id)
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- User indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- Food indexes
CREATE INDEX IF NOT EXISTS idx_food_items_category ON food_items(category);
CREATE INDEX IF NOT EXISTS idx_food_items_cuisine ON food_items(cuisine);
CREATE INDEX IF NOT EXISTS idx_food_items_available ON food_items(is_available);

-- Order indexes
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

-- Rating indexes
CREATE INDEX IF NOT EXISTS idx_ratings_food_item_id ON ratings(food_item_id);
CREATE INDEX IF NOT EXISTS idx_ratings_user_id ON ratings(user_id);
CREATE INDEX IF NOT EXISTS idx_ratings_rating ON ratings(rating);

-- Cooking session indexes
CREATE INDEX IF NOT EXISTS idx_cooking_sessions_scheduled_time ON cooking_sessions(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_cooking_sessions_status ON cooking_sessions(status);
CREATE INDEX IF NOT EXISTS idx_cooking_sessions_chef_id ON cooking_sessions(chef_id);
"""

# =============================================================================
# SCHEMA DOCUMENTATION
# =============================================================================

SCHEMA_DOCUMENTATION = """
# Smart Food Ordering System - Database Schema Documentation

## Overview
This database schema supports a comprehensive food ordering system with user preferences, food customization, order management, ratings, and live cooking sessions.

## Tables Overview

### 1. User Management
- **users**: User accounts and profiles
- **user_preferences**: User food preferences for recommendations

### 2. Food & Ingredients
- **ingredients**: Ingredient catalog with nutritional info
- **food_items**: Food items in the catalog
- **food_ingredients**: Junction table for food-ingredient relationships
- **customization_options**: Customization options for food items

### 3. Order Management
- **orders**: Customer orders
- **order_items**: Individual items within orders

### 4. Ratings & Reviews
- **ratings**: User ratings and reviews for orders and food items

### 5. Live Cooking Sessions
- **cooking_sessions**: Live cooking sessions
- **cooking_session_participants**: Session participants

## Key Relationships

### Users
- One user can have multiple orders
- One user can have multiple ratings
- One user can participate in multiple cooking sessions
- One user can have one preference profile

### Food Items
- One food item can have multiple ingredients
- One food item can have multiple customization options
- One food item can be in multiple orders
- One food item can have multiple ratings
- One food item can have multiple cooking sessions

### Orders
- One order belongs to one user
- One order can have multiple order items
- One order can have multiple ratings

## Data Types & Constraints

### Common Patterns
- All tables have `created_at` and `updated_at` timestamps
- Foreign keys use CASCADE delete where appropriate
- JSON fields store complex data (preferences, customizations, etc.)
- Boolean fields use 0/1 values
- Unique constraints prevent duplicate relationships

### Validation Rules
- Usernames and emails must be unique
- Order numbers must be unique
- Ratings must be 1-5 stars
- Food prices must be positive
- Order amounts must be calculated correctly

## Performance Considerations

### Indexes Created
- User lookups (username, email, active status)
- Food filtering (category, cuisine, availability)
- Order queries (user, status, date)
- Rating aggregations (food item, user, rating value)
- Cooking session queries (scheduled time, status, chef)

### Query Optimization
- Use JSON fields for flexible preference storage
- Denormalize frequently accessed data (calories, nutritional info)
- Use junction tables for many-to-many relationships
- Implement pagination for large result sets

## Sample Data Structure

### User Preferences JSON Format
```json
{
  "favorite_cuisines": ["italian", "american"],
  "favorite_categories": ["pizza", "pasta"],
  "dietary_restrictions": ["vegetarian"],
  "allergies": ["nuts", "dairy"],
  "spice_level": "mild",
  "price_range": "moderate",
  "preferred_meal_times": ["lunch", "dinner"],
  "order_frequency": "weekly"
}
```

### Customization Options JSON Format
```json
{
  "name": "Size",
  "type": "single",
  "required": true,
  "options": [
    {"name": "Small (10\")", "price": 0.0},
    {"name": "Medium (12\")", "price": 2.0},
    {"name": "Large (14\")", "price": 4.0}
  ]
}
```

## Migration Strategy

### Version 1.0 (Current)
- Basic user, food, and order management
- Rating system
- Cooking sessions

### Future Enhancements
- Add payment processing tables
- Implement loyalty program tables
- Add delivery driver management
- Include promotional campaign tables

## Backup & Recovery

### Critical Data
- User accounts and preferences
- Order history and ratings
- Food catalog and customizations

### Regular Backups
- Daily automated backups
- Transaction log backups
- Point-in-time recovery capability

## Security Considerations

### Data Protection
- Password hashing using werkzeug
- JWT tokens for API authentication
- Input validation and sanitization
- SQL injection prevention with parameterized queries

### Access Control
- User authentication required for orders
- Admin privileges for food management
- Chef privileges for cooking sessions
"""

def create_database_schema():
    """Create the database schema using SQLAlchemy"""
    from models import db

    # Create all tables
    db.create_all()
    print("✅ Database schema created successfully")

def populate_sample_data():
    """Populate database with sample data"""
    from sample_data import populate_sample_data
    populate_sample_data()

def get_schema_stats():
    """Get database statistics"""
    from crud_operations import DatabaseCRUD

    crud = DatabaseCRUD()
    stats = crud.get_dashboard_stats()

    print("\n📊 Database Statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")

    return stats

if __name__ == "__main__":
    print("Smart Food Ordering System - Database Schema")
    print("=" * 50)

    # Create schema
    create_database_schema()

    # Populate sample data
    populate_sample_data()

    # Show statistics
    get_schema_stats()

    print("\n🎉 Database setup complete!")
    print("📋 Schema documentation available in SCHEMA_DOCUMENTATION variable")