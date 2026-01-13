'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface Order {
  id: number;
  status: string;
  total: number;
  created_at: string;
  restaurant_name: string;
}

export default function Orders() {
  const [orders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        // For now, show login required message
        setError('Please log in to view your orders');
      } catch (err) {
        setError('Please log in to view your orders');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchOrders();
  }, []);

  const getStatusIcon = (status: string) => {
    switch(status?.toLowerCase()) {
      case 'completed': return '✓';
      case 'cancelled': return '✕';
      case 'pending': return '⏳';
      default: return '📦';
    }
  };

  const getStatusColor = (status: string) => {
    switch(status?.toLowerCase()) {
      case 'completed': return 'from-green-500 to-emerald-600';
      case 'cancelled': return 'from-red-500 to-rose-600';
      case 'pending': return 'from-yellow-500 to-amber-600';
      default: return 'from-blue-500 to-cyan-600';
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-b from-orange-50 to-white">
        <div className="text-center">
          <div className="text-6xl mb-4 animate-bounce">📦</div>
          <div className="text-2xl text-orange-600 font-semibold">Loading your orders...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-b from-orange-50 via-white to-slate-50 min-h-screen">
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-12">
        <h1 className="text-5xl md:text-6xl font-bold text-gray-800 mb-4">📦 My Orders</h1>
        <p className="text-lg text-gray-600 mb-12">Track and manage your orders</p>

        {error && (
          <div className="bg-gradient-to-r from-red-100 to-red-50 border-l-4 border-red-500 text-red-700 px-6 py-4 rounded-lg mb-8 shadow-lg">
            <p className="font-semibold">⚠️ {error}</p>
          </div>
        )}

        {orders.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-7xl mb-4">🛍️</div>
            <p className="text-2xl text-gray-600 font-semibold mb-6">No orders yet</p>
            <Link href="/menu" className="inline-block bg-gradient-to-r from-orange-600 to-red-600 text-white px-8 py-4 rounded-xl font-bold hover:shadow-lg transition transform hover:scale-105">
              🍔 Place your first order
            </Link>
          </div>
        ) : (
          <div className="space-y-6">
            {orders.map((order, idx) => (
              <div key={order.id} className="bg-white rounded-2xl shadow-lg overflow-hidden hover:shadow-xl transition transform hover:-translate-y-1 animate-fadeInUp" style={{ animationDelay: `${idx * 50}ms` }}>
                <div className="bg-gradient-to-r from-orange-500 to-red-500 px-6 py-4 text-white flex justify-between items-center">
                  <div>
                    <h3 className="text-xl font-bold">Order #{order.id}</h3>
                    <p className="text-orange-100 text-sm">📅 {new Date(order.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
                  </div>
                  <div className={`bg-gradient-to-r ${getStatusColor(order.status)} text-white px-6 py-3 rounded-xl font-semibold shadow-lg text-center`}>
                    <span className="text-2xl">{getStatusIcon(order.status)}</span>
                    <p className="text-sm mt-1 capitalize">{order.status}</p>
                  </div>
                </div>
                <div className="px-6 py-4">
                  <div className="flex justify-between items-end">
                    <div>
                      <p className="text-gray-600 text-sm">Order Total</p>
                      <p className="text-3xl font-bold bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">${order.total.toFixed(2)}</p>
                    </div>
                    <Link href={`/orders/${order.id}`} className="bg-gradient-to-r from-orange-500 to-red-600 text-white px-6 py-3 rounded-lg font-semibold hover:shadow-lg transition transform hover:scale-105">
                      View Details →
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
