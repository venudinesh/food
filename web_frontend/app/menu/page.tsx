'use client';

import { useEffect, useState, useCallback } from 'react';
import { apiClient } from '@/lib/api';
import { useLocation } from '@/lib/location-context';
import { useCart } from '@/lib/cart-context';

interface Restaurant {
  place_id: string;
  name: string;
  address: string;
  rating: number;
  price_level: number;
  location: {
    lat: number;
    lng: number;
  };
  types: string[];
  open_now: boolean;
}

interface MenuItem {
  id: number;
  name: string;
  description: string;
  price: number;
  category: string;
  image_url?: string;
  is_available: boolean;
  customizations?: Record<string, unknown>[];
}

export default function Menu() {
  const { currentLocation, isLoading: locationLoading, error: locationError, detectLocation } = useLocation();
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [selectedRestaurant, setSelectedRestaurant] = useState<Restaurant | null>(null);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { addItem } = useCart();

  const fetchRestaurants = useCallback(async () => {
    if (!currentLocation) return;

    try {
      setLoading(true);
      const response = await apiClient.get(
        `/api/restaurants/nearby?lat=${currentLocation.latitude}&lng=${currentLocation.longitude}&radius=1000`
      );

      if (response.success) {
        setRestaurants(response.restaurants);
      } else {
        setError('Failed to load restaurants');
      }
    } catch (err) {
      setError('Failed to load restaurants. Please check your location permissions.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [currentLocation]);

  // Fetch restaurants near user location
  useEffect(() => {
    if (currentLocation) {
      fetchRestaurants();
    }
  }, [currentLocation, fetchRestaurants]);

  const fetchRestaurantMenu = async (restaurant: Restaurant) => {
    try {
      setLoading(true);
      // Extract cuisine type from restaurant types
      const cuisineType = restaurant.types?.find(type =>
        ['italian', 'japanese', 'mexican', 'american', 'chinese', 'indian', 'thai', 'french'].includes(type)
      ) || 'american';

      const response = await apiClient.get(
        `/api/restaurants/${restaurant.place_id.split('').reduce((a, b) => a + b.charCodeAt(0), 0) % 1000 + 1}/menu?name=${encodeURIComponent(restaurant.name)}&cuisine=${cuisineType}`
      );

      if (response.success) {
        setSelectedRestaurant(restaurant);
        setMenuItems(response.menu_items);
      } else {
        setError('Failed to load menu');
      }
    } catch (err) {
      setError('Failed to load menu');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCart = (item: MenuItem) => {
    addItem({
      id: item.id,
      name: item.name,
      price: item.price,
      restaurant: selectedRestaurant?.name || 'Unknown',
      customizations: {}
    });
  };

  if (locationLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-b from-orange-50 to-white">
        <div className="text-center">
          <div className="text-6xl mb-4 animate-bounce">📍</div>
          <div className="text-2xl text-orange-600 font-semibold">Detecting your location...</div>
        </div>
      </div>
    );
  }

  if (locationError) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-b from-orange-50 to-white">
        <div className="text-center">
          <div className="text-6xl mb-4">📍</div>
          <div className="text-xl text-red-600 font-semibold mb-4">Location Access Required</div>
          <p className="text-gray-600 mb-6">{locationError}</p>
          <button
            onClick={detectLocation}
            className="bg-orange-500 hover:bg-orange-600 text-white px-6 py-3 rounded-lg font-semibold"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!selectedRestaurant) {
    // Show restaurant selection
    return (
      <div className="bg-gradient-to-b from-orange-50 via-white to-slate-50 min-h-screen">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-12">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-800 mb-4">🍽️ Restaurants Near You</h1>
          <p className="text-lg text-gray-600 mb-12">Discover amazing restaurants in your area</p>

          {error && (
            <div className="bg-gradient-to-r from-red-100 to-red-50 border-l-4 border-red-500 text-red-700 px-6 py-4 rounded-lg mb-8 shadow-lg">
              <p className="font-semibold">⚠️ {error}</p>
            </div>
          )}

          {loading ? (
            <div className="text-center py-12">
              <div className="text-6xl animate-spin mb-4">🍽️</div>
              <div className="text-xl text-gray-600">Finding restaurants...</div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {restaurants.map((restaurant) => (
                <div
                  key={restaurant.place_id}
                  className="bg-white rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300 overflow-hidden"
                >
                  <div className="p-6">
                    <h3 className="text-xl font-bold text-gray-800 mb-2">{restaurant.name}</h3>
                    <p className="text-gray-600 text-sm mb-3">{restaurant.address}</p>

                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center">
                        <span className="text-yellow-500 mr-1">⭐</span>
                        <span className="font-semibold">{restaurant.rating || 'N/A'}</span>
                      </div>
                      <div className="text-sm text-gray-500">
                        {'$'.repeat(restaurant.price_level || 1)}
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                        restaurant.open_now
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {restaurant.open_now ? 'Open' : 'Closed'}
                      </span>

                      <button
                        onClick={() => fetchRestaurantMenu(restaurant)}
                        className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg font-semibold text-sm transition-colors"
                      >
                        View Menu
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {restaurants.length === 0 && !loading && (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">🏠</div>
              <div className="text-xl text-gray-600 mb-4">No restaurants found nearby</div>
              <button
                onClick={fetchRestaurants}
                className="bg-orange-500 hover:bg-orange-600 text-white px-6 py-3 rounded-lg font-semibold"
              >
                Search Again
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Show restaurant menu
  const categories = Array.from(new Set(menuItems.map(item => item.category)));

  return (
    <div className="bg-gradient-to-b from-orange-50 via-white to-slate-50 min-h-screen">
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-12">
        {/* Restaurant Header */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 mb-2">{selectedRestaurant.name}</h1>
              <p className="text-gray-600">{selectedRestaurant.address}</p>
              <div className="flex items-center mt-2">
                <span className="text-yellow-500 mr-1">⭐</span>
                <span className="font-semibold mr-4">{selectedRestaurant.rating || 'N/A'}</span>
                <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                  selectedRestaurant.open_now
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                }`}>
                  {selectedRestaurant.open_now ? 'Open' : 'Closed'}
                </span>
              </div>
            </div>
            <button
              onClick={() => setSelectedRestaurant(null)}
              className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg font-semibold"
            >
              ← Back to Restaurants
            </button>
          </div>
        </div>

        {/* Menu Categories and Items */}
        {categories.map((category) => (
          <div key={category} className="mb-12">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">{category}</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {menuItems
                .filter(item => item.category === category)
                .map((item) => (
                  <div
                    key={item.id}
                    className="bg-white rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300 overflow-hidden"
                  >
                    <div className="p-6">
                      <h3 className="text-lg font-bold text-gray-800 mb-2">{item.name}</h3>
                      <p className="text-gray-600 text-sm mb-4">{item.description}</p>
                      <div className="flex items-center justify-between">
                        <span className="text-xl font-bold text-orange-600">${item.price.toFixed(2)}</span>
                        <button
                          onClick={() => handleAddToCart(item)}
                          className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg font-semibold text-sm transition-colors"
                        >
                          Add to Cart
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        ))}

        {menuItems.length === 0 && !loading && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🍽️</div>
            <div className="text-xl text-gray-600">No menu items available</div>
          </div>
        )}
      </div>
    </div>
  );
}
