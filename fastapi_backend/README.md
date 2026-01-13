# Smart Food Customization and Ordering System - Flask Backend

A complete REST API backend for the Android food ordering application with advanced customization, real-time order tracking, ratings, and comprehensive food management.

## 🚀 Features

- **User Authentication**: Registration and login with secure password hashing
- **Food Catalog**: Comprehensive food items with categories, pricing, and customization options
- **Order Management**: Complete order lifecycle with status tracking and item customizations
- **Ratings & Reviews**: User feedback system with star ratings and comments
- **CORS Support**: Cross-origin resource sharing for Android app integration
- **SQLite Database**: Lightweight database with SQLAlchemy ORM

## 📋 API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login

### Food Catalog
- `GET /api/food` - Get all food items (with optional category/search filters)

### Orders
- `POST /api/orders` - Create new order
- `GET /api/orders` - Get user's order history

### Ratings
- `POST /api/ratings` - Submit rating for ordered items

## 🛠 Installation & Setup

### Prerequisites
- Python 3.8+
- pip package manager

### Installation Steps

1. **Navigate to backend directory:**
   ```bash
   cd fastapi_backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment:**
   ```bash
   # Windows
   venv\Scripts\activate
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the server:**
   ```bash
   python working_app.py
   ```

The server will start on `http://127.0.0.1:8000`

## 🧪 Testing the API

Run the comprehensive test suite:

```bash
python complete_test.py
```

This will test all endpoints and verify the backend functionality.

## 📊 Database Models

### User
- User authentication and profile information
- Secure password hashing with Werkzeug

### FoodItem
- Food catalog with pricing, categories, and preparation times
- Availability status and image URLs

### Order & OrderItem
- Complete order management with customizations
- Status tracking and delivery information

### Rating
- User feedback system with star ratings and comments
- Linked to specific orders and food items

## 🔧 Configuration

The application uses the following configuration:
- **Database**: SQLite (`food_ordering.db`)
- **Port**: 8000
- **CORS**: Enabled for all origins (configure for production)
- **Debug Mode**: Enabled for development

## 📱 Android Integration

The backend provides REST APIs that the Android app can consume:

```kotlin
// Example Retrofit service calls
interface ApiService {
    @POST("api/auth/login")
    suspend fun login(@Body loginRequest: LoginRequest): Response<LoginResponse>

    @GET("api/food")
    suspend fun getFoodItems(): Response<List<FoodItem>>

    @POST("api/orders")
    suspend fun createOrder(@Body order: OrderRequest): Response<OrderResponse>
}
```

## 🚀 Production Deployment

For production deployment:

1. **Database**: Switch to PostgreSQL
2. **Security**: Implement proper JWT authentication
3. **CORS**: Restrict origins to your domain
4. **HTTPS**: Enable SSL/TLS
5. **WSGI Server**: Use Gunicorn instead of Flask development server

## 📝 Sample API Usage

### Register User
```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test User"
  }'
```

### Login
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

### Get Food Items
```bash
curl -X GET "http://127.0.0.1:8000/api/food"
```

### Create Order
```bash
curl -X POST http://127.0.0.1:8000/api/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer user_1_token" \
  -d '{
    "total_amount": 21.98,
    "delivery_address": "123 Test Street",
    "payment_method": "Credit Card",
    "items": [
      {
        "food_item_id": 1,
        "quantity": 1,
        "price": 12.99,
        "customizations": {"size": "large"}
      }
    ]
  }'
```

## 🎯 Project Status

✅ **Completed Features:**
- Complete Flask REST API backend
- User authentication system
- Food catalog management
- Order creation and management
- Ratings and feedback system
- Database models with relationships
- CORS configuration
- Comprehensive test suite
- Sample data initialization

🔄 **Ready for Integration:**
- Android app can now connect to this backend
- All required API endpoints implemented
- Proper error handling and responses
- Database relationships established

## 📚 Dependencies

- Flask: Web framework
- Flask-CORS: Cross-origin resource sharing
- Flask-SQLAlchemy: Database ORM
- Werkzeug: Password hashing utilities
- Requests: HTTP client for testing

## 🤝 Contributing

This backend is designed to work with the Android food ordering app. The API endpoints match the Android app's requirements for:

- User authentication flow
- Food browsing and customization
- Order placement with real-time tracking
- Ratings and feedback submission

## 📄 License

This project is part of the Smart Food Customization and Ordering System B.Tech project.

4. **Environment Configuration**

   Create a `.env` file in the root directory:

   ```env
   # Database
   DATABASE_URL=postgresql://user:password@localhost/food_ordering_db

   # Security
   SECRET_KEY=your-secret-key-here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30

   # CORS
   ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

   # Email (optional)
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password

   # File Upload (optional)
   UPLOAD_DIR=uploads/
   MAX_UPLOAD_SIZE=5242880  # 5MB

   # Redis (optional)
   REDIS_URL=redis://localhost:6379

   # Debug
   DEBUG=True
   ```

5. **Database Setup**

   ```bash
   # Create database
   createdb food_ordering_db

   # Run migrations (if using Alembic)
   alembic upgrade head
   ```

6. **Run the application**

   ```bash
   # Development server
   uvicorn app.main:app --reload

   # Production server
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user profile
- `PUT /auth/me` - Update user profile

### Food Catalog
- `GET /food/catalog` - Get complete food catalog
- `GET /food/restaurants` - Search restaurants
- `GET /food/restaurants/{id}` - Get restaurant details
- `GET /food/restaurants/{id}/menu` - Get restaurant menu
- `GET /food/items` - Search food items
- `GET /food/items/{id}` - Get food item details
- `GET /food/categories` - Get categories

### Orders
- `POST /orders/` - Create new order
- `GET /orders/` - Get user orders
- `GET /orders/{id}` - Get order details
- `GET /orders/{id}/tracking` - Get order tracking info
- `PUT /orders/{id}/status` - Update order status
- `GET /orders/{id}/cooking-session` - Get cooking session
- `POST /orders/{id}/cooking-session/start` - Start cooking session

### Ratings & Reviews
- `POST /ratings/` - Create rating
- `GET /ratings/` - Get user ratings
- `GET /ratings/{id}` - Get rating details
- `PUT /ratings/{id}` - Update rating
- `DELETE /ratings/{id}` - Delete rating
- `GET /ratings/restaurant/{id}` - Get restaurant ratings
- `GET /ratings/restaurant/{id}/stats` - Get restaurant rating stats

## Database Schema

### Core Tables
- `users` - User accounts and profiles
- `restaurants` - Restaurant information
- `food_items` - Food items catalog
- `categories` - Food categories
- `orders` - Order information
- `order_items` - Order line items
- `ratings` - User ratings and reviews

### Advanced Features
- `cooking_sessions` - Live cooking sessions
- `delivery_partners` - Delivery personnel
- `chefs` - Chef profiles
- `telecast_notifications` - Live cooking notifications

## Development

### Project Structure
```
fastapi_backend/
├── app/
│   ├── api/           # API route handlers
│   │   ├── auth.py    # Authentication endpoints
│   │   ├── food.py    # Food catalog endpoints
│   │   ├── orders.py  # Order management endpoints
│   │   └── ratings.py # Rating system endpoints
│   ├── core/          # Core functionality
│   │   ├── config.py  # Configuration settings
│   │   ├── database.py# Database connection
│   │   └── security.py# Security utilities
│   ├── models/        # Database models
│   │   ├── user.py    # User models
│   │   ├── food.py    # Food catalog models
│   │   ├── order.py   # Order models
│   │   └── rating.py  # Rating models
│   └── main.py        # FastAPI application
├── requirements.txt   # Python dependencies
├── README.md         # This file
└── .env             # Environment variables
```

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
# Format code
black .

# Sort imports
isort .

# Lint code
flake8 .
```

## Deployment

### Docker Deployment

1. **Build Docker image**
   ```bash
   docker build -t food-api .
   ```

2. **Run with Docker Compose**
   ```yaml
   # docker-compose.yml
   version: '3.8'
   services:
     api:
       build: .
       ports:
         - "8000:8000"
       environment:
         - DATABASE_URL=postgresql://user:password@db/food_ordering_db
       depends_on:
         - db

     db:
       image: postgres:13
       environment:
         - POSTGRES_DB=food_ordering_db
         - POSTGRES_USER=user
         - POSTGRES_PASSWORD=password
   ```

### Production Considerations

- Use environment-specific configuration
- Set up proper logging and monitoring
- Implement rate limiting
- Use HTTPS in production
- Set up database connection pooling
- Implement proper error handling and validation
- Use Redis for caching and session management
- Set up background task processing with Celery
- Implement proper backup strategies

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the documentation at `/docs`
- Review the API examples in the Swagger UI