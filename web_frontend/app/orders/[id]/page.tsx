'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { apiClient } from '@/lib/api';

interface OrderItem {
  id: number;
  name: string;
  price: number;
  quantity: number;
  subtotal: number;
}

interface Order {
  id: string;
  status: string;
  items: OrderItem[];
  total: number;
  delivery_address: string;
  created_at: string;
  estimated_delivery?: string;
}

interface DeliveryTracking {
  status: string;
  location?: {
    lat: number;
    lng: number;
  };
  estimated_time?: string;
  driver_name?: string;
  driver_phone?: string;
}

const statusSteps = [
  { key: 'confirmed', label: 'Order Confirmed', icon: '✅', color: 'text-green-600' },
  { key: 'preparing', label: 'Preparing Food', icon: '👨‍🍳', color: 'text-orange-600' },
  { key: 'ready', label: 'Ready for Pickup', icon: '📦', color: 'text-blue-600' },
  { key: 'picked_up', label: 'Picked Up', icon: '🚴', color: 'text-purple-600' },
  { key: 'delivered', label: 'Delivered', icon: '🎉', color: 'text-green-600' }
];

export default function OrderTracking() {
  const params = useParams();
  const orderId = params.id as string;

  const [order, setOrder] = useState<Order | null>(null);
  const [tracking, setTracking] = useState<DeliveryTracking | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOrderDetails = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/orders/${orderId}`);
      if (response.success) {
        setOrder(response.order);
      } else {
        setError('Order not found');
      }
    } catch (err) {
      setError('Failed to load order details');
      console.error(err);
    }
  }, [orderId]);

  const fetchTrackingInfo = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/orders/${orderId}/tracking`);
      if (response.success) {
        setTracking(response.tracking);
      }
    } catch (err) {
      console.error('Failed to load tracking info:', err);
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    if (orderId) {
      fetchOrderDetails();
      fetchTrackingInfo();

      // Set up polling for real-time updates
      const interval = setInterval(() => {
        fetchTrackingInfo();
      }, 30000); // Update every 30 seconds

      return () => clearInterval(interval);
    }
  }, [orderId, fetchOrderDetails, fetchTrackingInfo]);

  const getCurrentStatusIndex = (status: string) => {
    return statusSteps.findIndex(step => step.key === status);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-b from-orange-50 to-white">
        <div className="text-center">
          <div className="text-6xl mb-4 animate-spin">📦</div>
          <div className="text-2xl text-orange-600 font-semibold">Loading order details...</div>
        </div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="bg-gradient-to-b from-orange-50 via-white to-slate-50 min-h-screen">
        <div className="max-w-4xl mx-auto px-4 md:px-6 py-12">
          <div className="text-center">
            <div className="text-6xl mb-6">❌</div>
            <h1 className="text-4xl font-bold text-red-600 mb-4">Order Not Found</h1>
            <p className="text-xl text-gray-600 mb-8">{error || 'The order you\'re looking for doesn\'t exist.'}</p>
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

  const currentStatusIndex = getCurrentStatusIndex(order.status);

  return (
    <div className="bg-gradient-to-b from-orange-50 via-white to-slate-50 min-h-screen">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-12">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">📦 Order Tracking</h1>
          <p className="text-lg text-gray-600">Order #{order.id}</p>
        </div>

        {/* Order Status Progress */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">Order Status</h2>

          <div className="relative">
            {/* Progress Line */}
            <div className="absolute top-8 left-8 right-8 h-1 bg-gray-200 rounded">
              <div
                className="h-full bg-gradient-to-r from-orange-500 to-red-500 rounded transition-all duration-500"
                style={{ width: `${(currentStatusIndex / (statusSteps.length - 1)) * 100}%` }}
              ></div>
            </div>

            {/* Status Steps */}
            <div className="relative flex justify-between">
              {statusSteps.map((step, index) => (
                <div key={step.key} className="flex flex-col items-center">
                  <div className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl mb-3 transition-all duration-300 ${
                    index <= currentStatusIndex
                      ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white shadow-lg scale-110'
                      : 'bg-gray-200 text-gray-400'
                  }`}>
                    {step.icon}
                  </div>
                  <div className={`text-center text-sm font-semibold ${
                    index <= currentStatusIndex ? 'text-gray-800' : 'text-gray-400'
                  }`}>
                    {step.label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {tracking && (
            <div className="mt-8 p-4 bg-blue-50 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-blue-800">Estimated Delivery</p>
                  <p className="text-blue-600">{tracking.estimated_time || 'Calculating...'}</p>
                </div>
                {tracking.driver_name && (
                  <div className="text-right">
                    <p className="font-semibold text-blue-800">Delivery Driver</p>
                    <p className="text-blue-600">{tracking.driver_name}</p>
                    {tracking.driver_phone && (
                      <p className="text-sm text-blue-500">{tracking.driver_phone}</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Order Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">🍽️ Order Items</h2>

            <div className="space-y-4">
              {order.items.map((item: OrderItem, index: number) => (
                <div key={index} className="flex justify-between items-center py-3 border-b border-gray-100 last:border-b-0">
                  <div>
                    <h3 className="font-semibold text-gray-800">{item.name}</h3>
                    <p className="text-sm text-gray-600">Quantity: {item.quantity}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-orange-600">${(item.price * item.quantity).toFixed(2)}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 pt-4 border-t border-gray-200">
              <div className="flex justify-between text-lg font-bold">
                <span>Total:</span>
                <span className="text-orange-600">${order.total.toFixed(2)}</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">📍 Delivery Details</h2>

            <div className="space-y-4">
              <div>
                <p className="font-semibold text-gray-700">Delivery Address</p>
                <p className="text-gray-600">{order.delivery_address}</p>
              </div>

              <div>
                <p className="font-semibold text-gray-700">Order Time</p>
                <p className="text-gray-600">{new Date(order.created_at).toLocaleString()}</p>
              </div>

              {order.estimated_delivery && (
                <div>
                  <p className="font-semibold text-gray-700">Estimated Delivery</p>
                  <p className="text-gray-600">{new Date(order.estimated_delivery).toLocaleString()}</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex justify-center space-x-4">
          <Link
            href="/menu"
            className="bg-orange-500 hover:bg-orange-600 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
          >
            Order More Food
          </Link>
          <Link
            href="/feedback"
            className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
          >
            Leave Feedback
          </Link>
        </div>
      </div>
    </div>
  );
}