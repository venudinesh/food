'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import { useCart } from '@/lib/cart-context';
import { useAuth } from '@/lib/auth-context';

interface OrderDetails {
  order_id: string;
  total: number;
  items: any[];
  delivery_address: string;
  payment_method: string;
}

function PaymentContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { clearCart } = useCart();
  const { isAuthenticated } = useAuth();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [orderDetails, setOrderDetails] = useState<OrderDetails | null>(null);

  // Payment form states
  const [cardNumber, setCardNumber] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [cvv, setCvv] = useState('');
  const [cardName, setCardName] = useState('');
  const [upiId, setUpiId] = useState('');

  useEffect(() => {
    // Get order details from URL parameters
    const orderId = searchParams.get('order_id');
    const total = searchParams.get('total');
    const paymentMethod = searchParams.get('payment_method');

    if (!orderId || !total || !paymentMethod) {
      setError('Invalid payment session. Please go back to checkout.');
      return;
    }

    const parsedTotal = parseFloat(total);
    if (isNaN(parsedTotal) || parsedTotal <= 0) {
      setError('Invalid payment amount. Please go back to checkout.');
      return;
    }

    // In a real app, you'd fetch order details from the API
    // For now, we'll reconstruct from URL params
    setOrderDetails({
      order_id: orderId,
      total: parsedTotal,
      items: [], // Would be fetched from API
      delivery_address: '', // Would be fetched from API
      payment_method: paymentMethod
    });
  }, [isAuthenticated, router, searchParams]);

  const handleCardPayment = async () => {
    if (!orderDetails) return;

    // Accept any card details as valid
    try {
      setLoading(true);
      setError(null);

      console.log('Processing card payment for order:', orderDetails.order_id);

      // Always succeed - accept any details
      setSuccess(true);
      clearCart();
      // Redirect to order confirmation after a delay
      setTimeout(() => {
        router.push(`/orders/${orderDetails.order_id}`);
      }, 3000);
    } catch (err) {
      // This should never happen now, but keeping for safety
      const message = err instanceof Error ? err.message : 'Payment processing failed';
      setError(message);
      console.error('Payment error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCodPayment = async () => {
    if (!orderDetails) return;

    try {
      setLoading(true);
      setError(null);

      // Always succeed for COD
      setSuccess(true);
      clearCart();
      setTimeout(() => {
        router.push(`/orders/${orderDetails.order_id}`);
      }, 3000);
    } catch (err) {
      // This should never happen now, but keeping for safety
      setError('Failed to process payment. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpiPayment = async () => {
    if (!orderDetails) return;

    // Accept any UPI ID as valid
    try {
      setLoading(true);
      setError(null);

      // Always succeed - accept any UPI ID
      setSuccess(true);
      clearCart();
      setTimeout(() => {
        router.push(`/orders/${orderDetails.order_id}`);
      }, 3000);
    } catch (err) {
      // This should never happen now, but keeping for safety
      setError('UPI payment processing failed. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handlePayment = () => {
    if (!orderDetails) return;

    switch (orderDetails.payment_method) {
      case 'card':
        handleCardPayment();
        break;
      case 'cod':
        handleCodPayment();
        break;
      case 'upi':
        handleUpiPayment();
        break;
      default:
        setError('Invalid payment method');
    }
  };

  if (error && !orderDetails) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-red-50 via-white to-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">❌</div>
          <h1 className="text-2xl font-bold text-red-800 mb-4">Payment Error</h1>
          <p className="text-gray-600 mb-6">{error}</p>
          <Link
            href="/checkout"
            className="bg-orange-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-orange-700 transition-colors"
          >
            Back to Checkout
          </Link>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-green-50 via-white to-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-8xl mb-6">🎉</div>
          <h1 className="text-4xl font-bold text-green-800 mb-4">Payment Successful!</h1>
          <p className="text-xl text-gray-600 mb-8">Your order is being prepared</p>

          <div className="bg-white rounded-xl shadow-lg p-8 mb-8 max-w-md mx-auto">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">Order #{orderDetails?.order_id}</h2>
            <div className="text-left space-y-2">
              <p><strong>Total Paid:</strong> ₹{orderDetails?.total.toFixed(2)}</p>
              <p><strong>Payment Method:</strong> {orderDetails?.payment_method.toUpperCase()}</p>
            </div>
          </div>

          <p className="text-gray-600 mb-6">Redirecting to order details...</p>
          <Link
            href="/orders"
            className="bg-orange-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-orange-700 transition-colors"
          >
            View All Orders
          </Link>
        </div>
      </div>
    );
  }

  if (!orderDetails) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading payment details...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-50">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-12">
        <div className="mb-8">
          <Link
            href="/checkout"
            className="text-orange-600 hover:text-orange-700 font-semibold flex items-center"
          >
            ← Back to Checkout
          </Link>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Order Summary */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Order Summary</h2>

            <div className="space-y-4">
              <div className="flex justify-between">
                <span className="text-gray-600">Order ID:</span>
                <span className="font-semibold">#{orderDetails.order_id}</span>
              </div>

              <div className="flex justify-between">
                <span className="text-gray-600">Payment Method:</span>
                <span className="font-semibold capitalize">{orderDetails.payment_method}</span>
              </div>

              <div className="border-t pt-4">
                <div className="flex justify-between text-lg font-bold">
                  <span>Total Amount:</span>
                  <span className="text-orange-600">₹{orderDetails.total.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Payment Form */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Complete Payment</h2>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                <p className="text-red-800">{error}</p>
              </div>
            )}

            {orderDetails.payment_method === 'card' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Card Number
                  </label>
                  <input
                    type="text"
                    value={cardNumber}
                    onChange={(e) => setCardNumber(e.target.value.replace(/\s/g, '').replace(/(\d{4})/g, '$1 ').trim())}
                    placeholder="Any card number works"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    maxLength={19}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Expiry Date
                    </label>
                    <input
                      type="text"
                      value={expiryDate}
                      onChange={(e) => setExpiryDate(e.target.value.replace(/\D/g, '').replace(/(\d{2})(\d{2})/, '$1/$2'))}
                      placeholder="Any date works"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                      maxLength={5}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      CVV
                    </label>
                    <input
                      type="text"
                      value={cvv}
                      onChange={(e) => setCvv(e.target.value.replace(/\D/g, ''))}
                      placeholder="Any CVV works"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                      maxLength={4}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Cardholder Name
                  </label>
                  <input
                    type="text"
                    value={cardName}
                    onChange={(e) => setCardName(e.target.value)}
                    placeholder="Any name works"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  />
                </div>
              </div>
            )}

            {orderDetails.payment_method === 'upi' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    UPI ID
                  </label>
                  <input
                    type="text"
                    value={upiId}
                    onChange={(e) => setUpiId(e.target.value)}
                    placeholder="Any UPI ID works"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  />
                </div>

                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <p className="text-green-800 text-sm">
                    💡 Any UPI ID will be accepted for testing purposes
                  </p>
                </div>
              </div>
            )}

            {orderDetails.payment_method === 'cod' && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h3 className="text-green-800 font-semibold mb-2">Cash on Delivery</h3>
                <p className="text-green-700 text-sm">
                  You will pay ₹{orderDetails.total.toFixed(2)} in cash when your order is delivered.
                  No payment required now.
                </p>
              </div>
            )}

            <button
              onClick={handlePayment}
              disabled={loading}
              className="w-full bg-orange-600 text-white py-4 px-6 rounded-lg font-semibold hover:bg-orange-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-6"
            >
              {loading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Processing...
                </div>
              ) : (
                `Pay ₹${orderDetails.total.toFixed(2)}`
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Payment() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <PaymentContent />
    </Suspense>
  );
}