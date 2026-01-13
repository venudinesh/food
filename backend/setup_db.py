import os
from app import create_app, db
from config import DevelopmentConfig, ProductionConfig

def setup_database():
    """Setup database based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')

    if env == 'production':
        app = create_app(ProductionConfig)
        print("Setting up production database...")
    else:
        app = create_app(DevelopmentConfig)
        print("Setting up development database...")

    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("Database tables created successfully!")

            # Create some sample data for testing
            from app.models.models import User, Restaurant, MenuItem
            from datetime import datetime

            # Check if sample data already exists
            if not User.query.first():
                print("Creating sample data...")

                # Create a sample user
                user = User(
                    username='testuser',
                    email='test@example.com',
                    password_hash='hashed_password'  # In real app, use proper hashing
                )
                db.session.add(user)

                # Create a sample restaurant
                restaurant = Restaurant(
                    place_id='sample_restaurant_123',
                    name='Sample Restaurant',
                    address='123 Main St',
                    phone='555-0123',
                    latitude=40.7128,
                    longitude=-74.0060,
                    cuisine_type='Italian',
                    is_open=True
                )
                db.session.add(restaurant)

                # Create sample menu items
                menu_items = [
                    MenuItem(
                        restaurant_id=1,  # Will be set after restaurant is committed
                        name='Margherita Pizza',
                        description='Classic pizza with tomato sauce, mozzarella, and basil',
                        price=12.99,
                        category='Pizza',
                        is_available=True,
                        preparation_time=15
                    ),
                    MenuItem(
                        restaurant_id=1,
                        name='Pasta Carbonara',
                        description='Creamy pasta with bacon and parmesan',
                        price=14.99,
                        category='Pasta',
                        is_available=True,
                        preparation_time=12
                    )
                ]

                db.session.commit()  # Commit restaurant first to get ID

                # Now add menu items with correct restaurant_id
                for item in menu_items:
                    item.restaurant_id = restaurant.id
                    db.session.add(item)

                db.session.commit()
                print("Sample data created!")
            else:
                print("Sample data already exists.")
        except Exception as e:
            print(f"Error setting up database: {e}")
            db.session.rollback()

if __name__ == '__main__':
    setup_database()