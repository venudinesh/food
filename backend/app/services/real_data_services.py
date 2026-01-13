import requests
import os
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional, Tuple
from flask import current_app
import googlemaps
from urllib.parse import quote
import stripe

class LocationService:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="food_delivery_app")

    def get_location_from_ip(self, ip_address: str = None) -> Optional[Dict]:
        """Get location from IP address using a free IP geolocation service"""
        try:
            # Using ipapi.co for free IP geolocation
            response = requests.get('https://ipapi.co/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'latitude': float(data.get('latitude', 0)),
                    'longitude': float(data.get('longitude', 0)),
                    'city': data.get('city', ''),
                    'country': data.get('country_name', ''),
                    'address': f"{data.get('city', '')}, {data.get('country_name', '')}"
                }
        except Exception as e:
            current_app.logger.error(f"IP geolocation error: {e}")

        return None

    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """Convert address to coordinates"""
        try:
            location = self.geolocator.geocode(address, timeout=10)
            if location:
                return (location.latitude, location.longitude)
        except Exception as e:
            current_app.logger.error(f"Geocoding error: {e}")

        return None

    def reverse_geocode(self, lat: float, lng: float) -> Optional[str]:
        """Convert coordinates to address"""
        try:
            location = self.geolocator.reverse((lat, lng), timeout=10)
            if location:
                return location.address
        except Exception as e:
            current_app.logger.error(f"Reverse geocoding error: {e}")

        return None
    def __init__(self):
        self.geolocator = Nominatim(user_agent="food_delivery_app")

    def get_location_from_ip(self, ip_address: str = None) -> Optional[Dict]:
        """Get location from IP address using a free IP geolocation service"""
        try:
            # Using ipapi.co for free IP geolocation
            response = requests.get('https://ipapi.co/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'latitude': float(data.get('latitude', 0)),
                    'longitude': float(data.get('longitude', 0)),
                    'city': data.get('city', ''),
                    'country': data.get('country_name', ''),
                    'address': f"{data.get('city', '')}, {data.get('country_name', '')}"
                }
        except Exception as e:
            current_app.logger.error(f"IP geolocation error: {e}")

        return None

    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """Convert address to coordinates"""
        try:
            location = self.geolocator.geocode(address, timeout=10)
            if location:
                return (location.latitude, location.longitude)
        except Exception as e:
            current_app.logger.error(f"Geocoding error: {e}")

        return None

    def reverse_geocode(self, lat: float, lng: float) -> Optional[str]:
        """Convert coordinates to address"""
        try:
            location = self.geolocator.reverse((lat, lng), timeout=10)
            if location:
                return location.address
        except Exception as e:
            current_app.logger.error(f"Reverse geocoding error: {e}")

        return None

class RestaurantService:
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_PLACES_API_KEY', '')
        self.yelp_api_key = os.getenv('YELP_API_KEY', '')

        # Initialize API clients only if keys are available
        try:
            self.google_maps = googlemaps.Client(key=self.google_api_key) if self.google_api_key else None
        except Exception as e:
            print(f"Warning: Failed to initialize Google Maps client: {e}")
            self.google_maps = None

    def get_restaurants_nearby(self, lat: float, lng: float, radius: int = 5000) -> List[Dict]:
        """Get restaurants near a location using real APIs"""
        restaurants = []

        # Try Google Places API first
        if self.google_api_key:
            google_restaurants = self._get_google_restaurants(lat, lng, radius)
            restaurants.extend(google_restaurants)

        # Try Yelp API as backup
        if self.yelp_api_key and len(restaurants) < 10:
            yelp_restaurants = self._get_yelp_restaurants(lat, lng, radius)
            # Avoid duplicates
            existing_ids = {r.get('place_id') or r.get('id') for r in restaurants}
            for r in yelp_restaurants:
                if r.get('place_id') not in existing_ids and r.get('id') not in existing_ids:
                    restaurants.append(r)

        # If no real data, return empty list (no mock data)
        return restaurants[:20]  # Limit to 20 results

    def _get_google_restaurants(self, lat: float, lng: float, radius: int) -> List[Dict]:
        """Get restaurants from Google Places API"""
        try:
            if not self.google_maps:
                return []

            # Search for restaurants
            places_result = self.google_maps.places_nearby(
                location=(lat, lng),
                radius=radius,
                type='restaurant',
                open_now=True
            )

            restaurants = []
            for place in places_result.get('results', []):
                restaurant = {
                    'place_id': place.get('place_id'),
                    'name': place.get('name'),
                    'address': place.get('vicinity', ''),
                    'rating': place.get('rating'),
                    'price_level': place.get('price_level'),
                    'location': {
                        'lat': place.get('geometry', {}).get('location', {}).get('lat'),
                        'lng': place.get('geometry', {}).get('location', {}).get('lng')
                    },
                    'types': place.get('types', []),
                    'open_now': place.get('opening_hours', {}).get('open_now'),
                    'photo_reference': place.get('photos', [{}])[0].get('photo_reference') if place.get('photos') else None,
                    'source': 'google'
                }
                restaurants.append(restaurant)

            return restaurants
        except Exception as e:
            current_app.logger.error(f"Google Places API error: {e}")
            return []

    def _get_yelp_restaurants(self, lat: float, lng: float, radius: int) -> List[Dict]:
        """Get restaurants from Yelp API"""
        try:
            if not self.yelp_api_key:
                return []

            headers = {
                'Authorization': f'Bearer {self.yelp_api_key}'
            }

            params = {
                'latitude': lat,
                'longitude': lng,
                'radius': min(radius, 40000),  # Yelp max is 40km
                'categories': 'restaurants',
                'limit': 20,
                'open_now': True
            }

            response = requests.get('https://api.yelp.com/v3/businesses/search', headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                restaurants = []

                for business in data.get('businesses', []):
                    restaurant = {
                        'place_id': business.get('id'),
                        'name': business.get('name'),
                        'address': ', '.join(business.get('location', {}).get('display_address', [])),
                        'rating': business.get('rating'),
                        'price_level': len(business.get('price', '$')) if business.get('price') else None,
                        'location': {
                            'lat': business.get('coordinates', {}).get('latitude'),
                            'lng': business.get('coordinates', {}).get('longitude')
                        },
                        'types': business.get('categories', [{}])[0].get('title', '').lower().split(),
                        'open_now': business.get('is_closed') is False,
                        'image_url': business.get('image_url'),
                        'phone': business.get('phone'),
                        'source': 'yelp'
                    }
                    restaurants.append(restaurant)

                return restaurants
            else:
                current_app.logger.error(f"Yelp API error: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            current_app.logger.error(f"Yelp API error: {e}")
            return []

    def get_restaurant_details(self, place_id: str) -> Optional[Dict]:
        """Get detailed restaurant information"""
        # Mock implementation
        mock_details = {
            'place_id': place_id,
            'name': 'Sample Restaurant',
            'address': '123 Sample St',
            'phone': '+1-555-0123',
            'website': 'https://example.com',
            'opening_hours': {
                'open_now': True,
                'weekday_text': [
                    'Monday: 9:00 AM – 9:00 PM',
                    'Tuesday: 9:00 AM – 9:00 PM',
                    'Wednesday: 9:00 AM – 9:00 PM',
                    'Thursday: 9:00 AM – 9:00 PM',
                    'Friday: 9:00 AM – 9:00 PM',
                    'Saturday: 9:00 AM – 10:00 PM',
                    'Sunday: 10:00 AM – 8:00 PM'
                ]
            },
            'reviews': []
        }
        return mock_details

class MenuCustomizationService:
    def __init__(self):
        pass

    def get_menu_item_customizations(self, menu_item_id: int) -> List[Dict]:
        """Get available customizations for a menu item"""
        # Mock customizations
        customizations = [
            {
                'id': 1,
                'name': 'Spice Level',
                'type': 'radio',
                'required': False,
                'options': [
                    {'id': 1, 'name': 'Mild', 'price': 0},
                    {'id': 2, 'name': 'Medium', 'price': 0},
                    {'id': 3, 'name': 'Hot', 'price': 0},
                    {'id': 4, 'name': 'Extra Hot', 'price': 0.50}
                ]
            },
            {
                'id': 2,
                'name': 'Extra Toppings',
                'type': 'checkbox',
                'required': False,
                'options': [
                    {'id': 5, 'name': 'Cheese', 'price': 1.50},
                    {'id': 6, 'name': 'Bacon', 'price': 2.00},
                    {'id': 7, 'name': 'Mushrooms', 'price': 1.00},
                    {'id': 8, 'name': 'Pepperoni', 'price': 1.75}
                ]
            },
            {
                'id': 3,
                'name': 'Special Instructions',
                'type': 'text',
                'required': False,
                'options': []
            }
        ]
        return customizations

    def calculate_customization_price(self, customizations: Dict) -> float:
        """Calculate total price for customizations"""
        total = 0.0
        # Mock price calculation
        if 'spice_level' in customizations and customizations['spice_level'] == 'Extra Hot':
            total += 0.50

        if 'extra_toppings' in customizations:
            topping_prices = {'cheese': 1.50, 'bacon': 2.00, 'mushrooms': 1.00, 'pepperoni': 1.75}
            for topping in customizations['extra_toppings']:
                total += topping_prices.get(topping.lower(), 0)

        return total

class DeliveryTrackingService:
    def __init__(self):
        pass

    def get_delivery_status(self, order_id: str) -> Dict:
        """Get current delivery status for an order"""
        # Mock delivery status based on order creation time
        # In a real app, this would be stored in the database
        statuses = ['confirmed', 'preparing', 'ready', 'picked_up', 'delivered']
        mock_status_index = 2  # Default to 'ready'

        status = statuses[min(mock_status_index, len(statuses) - 1)]

        status_info = {
            'status': status,
            'location': None,
            'estimated_time': None,
            'driver_name': None,
            'driver_phone': None
        }

        if status in ['picked_up', 'delivered']:
            status_info.update({
                'driver_name': 'John Smith',
                'driver_phone': '+1-555-0199',
                'estimated_time': '15-20 minutes'
            })

            if status == 'picked_up':
                status_info['location'] = {'lat': 40.7128, 'lng': -74.0060}  # Mock location

        return status_info

    def update_delivery_status(self, order_id: str, status: str, location: Optional[Dict] = None) -> bool:
        """Update delivery status (would update database in real app)"""
        # Mock implementation - in real app would update database
        current_app.logger.info(f"Updated order {order_id} status to {status}")
        return True

class FeedbackService:
    def __init__(self):
        pass

    def submit_feedback(self, feedback_data: Dict) -> bool:
        """Submit customer feedback"""
        try:
            # In a real app, this would save to database
            current_app.logger.info(f"Feedback submitted: {feedback_data}")
            return True
        except Exception as e:
            current_app.logger.error(f"Feedback submission error: {e}")
            return False

    def get_restaurant_feedback_summary(self, restaurant_id: str) -> Dict:
        """Get feedback summary for a restaurant"""
        # Mock feedback summary
        return {
            'average_rating': 4.2,
            'total_reviews': 156,
            'rating_breakdown': {
                '5': 89,
                '4': 45,
                '3': 15,
                '2': 5,
                '1': 2
            },
            'recommendation_rate': 0.85
        }


class MenuService:
    def __init__(self):
        self.spoonacular_api_key = os.getenv('SPOONACULAR_API_KEY', '')
        self.yelp_api_key = os.getenv('YELP_API_KEY', '')

    def get_restaurant_menu(self, restaurant_id: str, restaurant_name: str = None, cuisine_type: str = None) -> List[Dict]:
        """Get real menu items for a restaurant using various APIs"""
        menu_items = []

        # Try Spoonacular API for menu data
        if self.spoonacular_api_key:
            spoonacular_items = self._get_spoonacular_menu(restaurant_name or "restaurant", cuisine_type)
            menu_items.extend(spoonacular_items)

        # Try Yelp menu API if available
        if self.yelp_api_key and len(menu_items) < 10:
            yelp_items = self._get_yelp_menu(restaurant_id)
            menu_items.extend(yelp_items)

        # Generate menu based on cuisine type if no real data
        if not menu_items and cuisine_type:
            menu_items = self._generate_menu_from_cuisine(cuisine_type)

        return menu_items

    def _get_spoonacular_menu(self, restaurant_name: str, cuisine_type: str = None) -> List[Dict]:
        """Get menu items from Spoonacular API"""
        try:
            if not self.spoonacular_api_key:
                return []

            # Search for recipes by cuisine
            cuisine = cuisine_type or "american"
            url = f"https://api.spoonacular.com/recipes/complexSearch"
            params = {
                'apiKey': self.spoonacular_api_key,
                'cuisine': cuisine,
                'number': 10,
                'addRecipeInformation': True,
                'fillIngredients': True
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                menu_items = []

                for recipe in data.get('results', []):
                    # Convert recipe to menu item
                    menu_item = {
                        'id': recipe.get('id'),
                        'name': recipe.get('title', ''),
                        'description': recipe.get('summary', '').replace('<b>', '').replace('</b>', '')[:200] + '...' if recipe.get('summary') else '',
                        'price': self._estimate_price(recipe.get('pricePerServing', 0)),
                        'category': self._classify_category(recipe.get('dishTypes', []), cuisine_type),
                        'image_url': recipe.get('image'),
                        'is_available': True,
                        'ingredients': [ing.get('name') for ing in recipe.get('extendedIngredients', [])],
                        'customizations': self._generate_customizations(recipe.get('extendedIngredients', [])),
                        'source': 'spoonacular'
                    }
                    menu_items.append(menu_item)

                return menu_items
            else:
                current_app.logger.error(f"Spoonacular API error: {response.status_code}")
                return []
        except Exception as e:
            current_app.logger.error(f"Spoonacular API error: {e}")
            return []

    def _get_yelp_menu(self, restaurant_id: str) -> List[Dict]:
        """Get menu items from Yelp API (if available)"""
        try:
            if not self.yelp_api_key:
                return []

            headers = {'Authorization': f'Bearer {self.yelp_api_key}'}
            url = f"https://api.yelp.com/v3/businesses/{restaurant_id}"

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                business = response.json()
                # Note: Yelp doesn't provide detailed menu items in their free API
                # This would require Yelp Fusion Premium or other menu APIs
                return []
            else:
                return []
        except Exception as e:
            current_app.logger.error(f"Yelp menu API error: {e}")
            return []

    def _generate_menu_from_cuisine(self, cuisine_type: str) -> List[Dict]:
        """Generate realistic menu items based on cuisine type"""
        cuisine_menus = {
            'italian': [
                {'name': 'Margherita Pizza', 'price': 12.99, 'category': 'Pizza', 'desc': 'Fresh mozzarella, tomato sauce, basil'},
                {'name': 'Spaghetti Carbonara', 'price': 14.99, 'category': 'Pasta', 'desc': 'Creamy sauce with pancetta and parmesan'},
                {'name': 'Chicken Parmesan', 'price': 16.99, 'category': 'Main Courses', 'desc': 'Breaded chicken with marinara and mozzarella'},
                {'name': 'Tiramisu', 'price': 6.99, 'category': 'Desserts', 'desc': 'Classic Italian dessert with coffee and mascarpone'},
            ],
            'japanese': [
                {'name': 'California Roll', 'price': 8.99, 'category': 'Sushi', 'desc': 'Crab, avocado, cucumber'},
                {'name': 'Salmon Sashimi', 'price': 12.99, 'category': 'Sashimi', 'desc': 'Fresh salmon slices'},
                {'name': 'Chicken Teriyaki Bowl', 'price': 11.99, 'category': 'Bowls', 'desc': 'Grilled chicken with teriyaki sauce'},
                {'name': 'Green Tea Ice Cream', 'price': 4.99, 'category': 'Desserts', 'desc': 'Traditional Japanese green tea flavor'},
            ],
            'mexican': [
                {'name': 'Chicken Quesadilla', 'price': 9.99, 'category': 'Appetizers', 'desc': 'Grilled chicken, cheese, peppers'},
                {'name': 'Beef Tacos', 'price': 10.99, 'category': 'Tacos', 'desc': 'Seasoned beef with fresh toppings'},
                {'name': 'Chicken Burrito Bowl', 'price': 11.99, 'category': 'Bowls', 'desc': 'Rice, chicken, beans, salsa'},
                {'name': 'Churros', 'price': 5.99, 'category': 'Desserts', 'desc': 'Cinnamon sugar coated fried dough'},
            ],
            'american': [
                {'name': 'Cheeseburger', 'price': 10.99, 'category': 'Burgers', 'desc': 'Beef patty with cheese, lettuce, tomato'},
                {'name': 'Chicken Wings', 'price': 12.99, 'category': 'Appetizers', 'desc': 'Buffalo wings with ranch dressing'},
                {'name': 'Caesar Salad', 'price': 8.99, 'category': 'Salads', 'desc': 'Romaine, parmesan, croutons'},
                {'name': 'Apple Pie', 'price': 6.99, 'category': 'Desserts', 'desc': 'Warm apple pie with vanilla ice cream'},
            ]
        }

        base_menu = cuisine_menus.get(cuisine_type.lower(), cuisine_menus['american'])
        menu_items = []

        for i, item in enumerate(base_menu):
            menu_item = {
                'id': f"{cuisine_type}_{i+1}",
                'name': item['name'],
                'description': item['desc'],
                'price': item['price'],
                'category': item['category'],
                'image_url': None,
                'is_available': True,
                'ingredients': self._extract_ingredients_from_description(item['desc']),
                'customizations': self._generate_customizations([]),
                'source': 'generated'
            }
            menu_items.append(menu_item)

        return menu_items

    def _estimate_price(self, spoonacular_price: int) -> float:
        """Convert Spoonacular price per serving to menu price"""
        if spoonacular_price == 0:
            return 12.99  # Default price

        # Spoonacular prices are in cents per serving
        price_per_serving = spoonacular_price / 100
        # Estimate restaurant price (typically 2-3x cost)
        return round(price_per_serving * 2.5, 2)

    def _classify_category(self, dish_types: List[str], cuisine_type: str = None) -> str:
        """Classify dish into menu category"""
        type_mapping = {
            'main course': 'Main Courses',
            'main dish': 'Main Courses',
            'side dish': 'Sides',
            'appetizer': 'Appetizers',
            'starter': 'Appetizers',
            'dessert': 'Desserts',
            'soup': 'Soups',
            'salad': 'Salads',
            'breakfast': 'Breakfast',
            'lunch': 'Lunch Specials',
            'dinner': 'Dinner Specials'
        }

        for dish_type in dish_types:
            if dish_type.lower() in type_mapping:
                return type_mapping[dish_type.lower()]

        # Default categories based on cuisine
        return 'Main Courses'

    def _extract_ingredients_from_description(self, description: str) -> List[str]:
        """Extract ingredients from item description"""
        # Simple extraction - in real app, use NLP
        common_ingredients = [
            'chicken', 'beef', 'pork', 'fish', 'salmon', 'shrimp', 'cheese', 'mozzarella',
            'parmesan', 'lettuce', 'tomato', 'onion', 'garlic', 'basil', 'oregano', 'rice',
            'pasta', 'bread', 'flour', 'eggs', 'milk', 'cream', 'butter', 'oil'
        ]

        found_ingredients = []
        desc_lower = description.lower()

        for ingredient in common_ingredients:
            if ingredient in desc_lower:
                found_ingredients.append(ingredient.title())

        return found_ingredients[:5]  # Limit to 5 ingredients

    def _generate_customizations(self, ingredients: List[Dict]) -> List[Dict]:
        """Generate customization options for menu item"""
        customizations = []

        # Spice level customization
        customizations.append({
            'id': 'spice_level',
            'name': 'Spice Level',
            'type': 'radio',
            'required': False,
            'options': [
                {'id': 'mild', 'name': 'Mild', 'price': 0},
                {'id': 'medium', 'name': 'Medium', 'price': 0},
                {'id': 'hot', 'name': 'Hot', 'price': 0},
                {'id': 'extra_hot', 'name': 'Extra Hot', 'price': 0.50}
            ]
        })

        # Extra ingredients if available
        if ingredients:
            extra_options = []
            for ing in ingredients[:4]:  # Limit to 4 options
                ing_name = ing.get('name', '') if isinstance(ing, dict) else str(ing)
                extra_options.append({
                    'id': f"extra_{ing_name.lower().replace(' ', '_')}",
                    'name': f"Extra {ing_name.title()}",
                    'price': 1.50
                })

            if extra_options:
                customizations.append({
                    'id': 'extra_ingredients',
                    'name': 'Extra Ingredients',
                    'type': 'checkbox',
                    'required': False,
                    'options': extra_options
                })

        # Special instructions
        customizations.append({
            'id': 'special_instructions',
            'name': 'Special Instructions',
            'type': 'text',
            'required': False,
            'options': []
        })

        return customizations


class PaymentService:
    def __init__(self):
        self.stripe_secret_key = os.getenv('STRIPE_SECRET_KEY', '')
        self.stripe_publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
        if self.stripe_secret_key:
            stripe.api_key = self.stripe_secret_key

    def create_payment_intent(self, amount: float, currency: str = 'usd') -> Dict:
        """Create a Stripe payment intent"""
        try:
            if not self.stripe_secret_key:
                return {'error': 'Stripe not configured'}

            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                payment_method_types=['card'],
            )

            return {
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
                'amount': amount,
                'currency': currency
            }
        except Exception as e:
            current_app.logger.error(f"Payment intent creation error: {e}")
            return {'error': str(e)}

    def confirm_payment(self, payment_intent_id: str) -> Dict:
        """Confirm a payment intent"""
        try:
            if not self.stripe_secret_key:
                return {'error': 'Stripe not configured'}

            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            return {
                'status': intent.status,
                'amount': intent.amount / 100,  # Convert from cents
                'currency': intent.currency,
                'payment_method': intent.payment_method
            }
        except Exception as e:
            current_app.logger.error(f"Payment confirmation error: {e}")
            return {'error': str(e)}

    def process_cod_payment(self, order_id: str, amount: float) -> bool:
        """Process cash on delivery (no actual payment processing needed)"""
        try:
            current_app.logger.info(f"Cash on delivery processed for order {order_id}, amount: ${amount}")
            return True
        except Exception as e:
            current_app.logger.error(f"Cash on delivery processing error: {e}")
            return False

    def process_upi_payment(self, order_id: str, amount: float, upi_id: str) -> Dict:
        """Process UPI payment (mock implementation)"""
        try:
            # In a real implementation, you would integrate with UPI payment gateway
            # For now, we'll simulate a successful payment
            current_app.logger.info(f"UPI payment processed for order {order_id}, UPI ID: {upi_id}, amount: ${amount}")

            return {
                'status': 'success',
                'transaction_id': f"upi_{order_id}_{datetime.utcnow().timestamp()}",
                'amount': amount,
                'upi_id': upi_id
            }
        except Exception as e:
            current_app.logger.error(f"UPI payment processing error: {e}")
            return {'error': str(e)}