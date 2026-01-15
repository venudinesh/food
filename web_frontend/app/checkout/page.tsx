'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { useCart } from '@/lib/cart-context';
import { useLocation } from '@/lib/location-context';
import { useAuth } from '@/lib/auth-context';

export default function Checkout() {
  const { items, total, clearCart } = useCart();
  const { currentLocation } = useLocation();
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [deliveryAddress, setDeliveryAddress] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('card');
  const [specialInstructions, setSpecialInstructions] = useState('');
  const [upiId, setUpiId] = useState('');

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!isAuthenticated) {
      router.push('/login?redirect=/checkout');
      return;
    }

    // Auto-fill delivery address from current location if available
    if (currentLocation && !deliveryAddress) {
      // In a real app, you'd reverse geocode the coordinates to get an address
      setDeliveryAddress(`${currentLocation.latitude.toFixed(4)}, ${currentLocation.longitude.toFixed(4)}`);
    }
  }, [currentLocation, deliveryAddress, isAuthenticated, router]);

  const handlePlaceOrder = async () => {
    if (items.length === 0) {
      setError('Please add items to your cart');
      return;
    }

    if (!deliveryAddress.trim()) {
      setError('Please enter a delivery address');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Transform cart items to match backend API format
      const transformedItems = items.map(item => ({
        menu_item_id: item.id,  // Backend expects menu_item_id
        quantity: item.quantity,
        special_instructions: item.customizations ? JSON.stringify(item.customizations) : ''
      }));

      // Get restaurant_id from first item (all items should be from same restaurant)
      const restaurantId = items[0]?.restaurant_id || 1;

      const orderData = {
        items: transformedItems,
        delivery_address: deliveryAddress.trim(),
        restaurant_id: restaurantId,
        payment_method: paymentMethod,
        special_instructions: specialInstructions?.trim() || undefined
      };

      // First, create the order
      const response = await apiClient.post('/api/orders', orderData);

      if (!response.success && !response.order_id) {
        setError(response.error || 'Failed to create order. Please try again.');
        return;
      }

      const createdOrderId = response.order_id || response.id;
      const finalTotal = total + 2.99 + total * 0.08; // Include delivery fee and tax

      if (!createdOrderId) {
        setError('Unable to create order - no order ID received');
        return;
      }

      // Redirect to payment page with order details
      router.push(`/payment?order_id=${createdOrderId}&total=${finalTotal.toFixed(2)}&payment_method=${paymentMethod}`);

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create order. Please try again.';
      console.error('Order creation error:', err);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  if (items.length === 0) {
    return (
      <div className="bg-gradient-to-b from-orange-50 via-white to-slate-50 min-h-screen">
        <div className="max-w-4xl mx-auto px-4 md:px-6 py-12">
          <div className="text-center">
            <div className="text-6xl mb-6">🛒</div>
            <h1 className="text-4xl font-bold text-gray-800 mb-4">Your Cart is Empty</h1>
            <p className="text-xl text-gray-600 mb-8">Add some delicious food to get started!</p>
            <Link
              href="/menu"
              className="bg-orange-500 hover:bg-orange-600 text-white px-8 py-3 rounded-lg font-semibold transition-colors inline-block"
            >
              Browse Menu
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-b from-orange-50 via-white to-slate-50 min-h-screen">
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-12">
        <h1 className="text-5xl md:text-6xl font-bold text-gray-800 mb-4">🛒 Checkout</h1>
        <p className="text-lg text-gray-600 mb-12">Complete your order and enjoy delicious food</p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          {/* Order Summary */}
          <div className="space-y-8">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">Order Summary</h2>

              <div className="space-y-4">
                {items.map((item, index) => (
                  <div key={index} className="flex justify-between items-center py-4 border-b border-gray-100 last:border-b-0">
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-800">{item.name}</h3>
                      <p className="text-sm text-gray-600">{item.restaurant}</p>
                      <p className="text-sm text-gray-500">Quantity: {item.quantity}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-orange-600">${(item.price * item.quantity).toFixed(2)}</p>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6 pt-6 border-t border-gray-200">
                <div className="flex justify-between items-center text-xl font-bold">
                  <span>Total:</span>
                  <span className="text-orange-600">${total.toFixed(2)}</span>
                </div>
              </div>
            </div>

            {/* Delivery Address */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">📍 Delivery Address</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Delivery Address
                  </label>
                  <textarea
                    value={deliveryAddress}
                    onChange={(e) => setDeliveryAddress(e.target.value)}
                    placeholder="Enter your delivery address"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent resize-none"
                    rows={3}
                    required
                  />
                </div>
              </div>
            </div>

            {/* Payment Method */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">💳 Payment Method</h2>

              <div className="space-y-4">
                <div className="flex items-center">
                  <input
                    type="radio"
                    id="card"
                    name="payment"
                    value="card"
                    checked={paymentMethod === 'card'}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                    className="mr-3"
                  />
                  <label htmlFor="card" className="flex items-center cursor-pointer">
                    <span className="text-2xl mr-2">💳</span>
                    <span className="font-semibold">Credit/Debit Card</span>
                  </label>
                </div>

                {paymentMethod === 'card' && (
                  <div className="ml-8 p-4 border border-gray-200 rounded-lg">
                    <p className="text-gray-600">Card payment integration coming soon...</p>
                  </div>
                )}

                <div className="flex items-center">
                  <input
                    type="radio"
                    id="upi"
                    name="payment"
                    value="upi"
                    checked={paymentMethod === 'upi'}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                    className="mr-3"
                  />
                  <label htmlFor="upi" className="flex items-center cursor-pointer">
                    <span className="text-2xl mr-2">📱</span>
                    <span className="font-semibold">UPI Payment</span>
                  </label>
                </div>

                {paymentMethod === 'upi' && (
                  <div className="ml-8 p-4 border border-gray-200 rounded-lg">
                    <input
                      type="text"
                      value={upiId}
                      onChange={(e) => setUpiId(e.target.value)}
                      placeholder="Enter your UPI ID (e.g., user@paytm)"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                      required
                    />
                  </div>
                )}

                <div className="flex items-center">
                  <input
                    type="radio"
                    id="cod"
                    name="payment"
                    value="cod"
                    checked={paymentMethod === 'cod'}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                    className="mr-3"
                  />
                  <label htmlFor="cod" className="flex items-center cursor-pointer">
                    <span className="text-2xl mr-2">💵</span>
                    <span className="font-semibold">Cash on Delivery</span>
                  </label>
                </div>
              </div>
            </div>

            {/* Special Instructions */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">📝 Special Instructions</h2>

              <textarea
                value={specialInstructions}
                onChange={(e) => setSpecialInstructions(e.target.value)}
                placeholder="Any special instructions for your order? (e.g., extra napkins, doorbell, etc.)"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent resize-none"
                rows={3}
              />
            </div>
          </div>

          {/* Place Order Button */}
          <div className="lg:sticky lg:top-8">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">Ready to Order?</h2>

              {error && (
                <div className="bg-gradient-to-r from-red-100 to-red-50 border-l-4 border-red-500 text-red-700 px-4 py-3 rounded-lg mb-6">
                  <p className="font-semibold">⚠️ {error}</p>
                </div>
              )}

              <div className="space-y-4">
                <div className="flex justify-between text-lg">
                  <span>Subtotal:</span>
                  <span>${total.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-lg">
                  <span>Delivery Fee:</span>
                  <span>$2.99</span>
                </div>
                <div className="flex justify-between text-lg">
                  <span>Tax:</span>
                  <span>${(total * 0.08).toFixed(2)}</span>
                </div>
                <hr className="my-4" />
                <div className="flex justify-between text-xl font-bold">
                  <span>Total:</span>
                  <span className="text-orange-600">${(total + 2.99 + total * 0.08).toFixed(2)}</span>
                </div>
              </div>

              <button
                onClick={handlePlaceOrder}
                disabled={loading || !deliveryAddress.trim()}
                className="w-full mt-8 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 disabled:from-gray-400 disabled:to-gray-500 text-white py-4 px-6 rounded-lg font-bold text-lg transition-all transform hover:scale-105 disabled:hover:scale-100 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white mr-2"></div>
                    Creating Order...
                  </div>
                ) : (
                  `Proceed to Payment - ₹${(total + 2.99 + total * 0.08).toFixed(2)}`
                )}
              </button>

              <p className="text-sm text-gray-500 text-center mt-4">
                By placing your order, you agree to our terms and conditions
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}