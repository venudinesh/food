'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useCart } from '@/lib/cart-context';
import { apiClient } from '@/lib/api';

export default function Cart() {
  const { items, removeItem, updateQuantity, total, clearCart } = useCart();
  const [loading, setLoading] = useState(false);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-b from-orange-50 to-white">
        <div className="text-center">
          <div className="text-6xl mb-4 animate-bounce">🛒</div>
          <div className="text-2xl text-orange-600 font-semibold">Loading your cart...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-b from-orange-50 via-white to-slate-50 min-h-screen">
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-12">
        <h1 className="text-5xl md:text-6xl font-bold text-gray-800 mb-4">🛒 Shopping Cart</h1>
        <p className="text-lg text-gray-600 mb-12">Review and manage your items</p>

        {items.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-7xl mb-4">📭</div>
            <p className="text-2xl text-gray-600 font-semibold mb-6">Your cart is empty</p>
            <Link href="/menu" className="inline-block bg-gradient-to-r from-orange-600 to-red-600 text-white px-8 py-4 rounded-xl font-bold hover:shadow-lg transition transform hover:scale-105">
              🍔 Continue shopping
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-4">
              {items.map((item, idx) => (
                <div key={item.id} className="bg-white rounded-2xl shadow-lg p-6 hover:shadow-xl transition transform hover:-translate-y-1 animate-fadeInUp" style={{ animationDelay: `${idx * 50}ms` }}>
                  <div className="flex justify-between items-center">
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-gray-800">{item.name}</h3>
                      <div className="flex items-center gap-3 mt-2">
                        <button
                          onClick={() => updateQuantity(item.id, item.quantity - 1)}
                          className="w-8 h-8 bg-orange-100 hover:bg-orange-200 text-orange-600 rounded-full flex items-center justify-center font-bold transition"
                        >
                          -
                        </button>
                        <span className="font-semibold text-orange-600 min-w-[2rem] text-center">{item.quantity}</span>
                        <button
                          onClick={() => updateQuantity(item.id, item.quantity + 1)}
                          className="w-8 h-8 bg-orange-100 hover:bg-orange-200 text-orange-600 rounded-full flex items-center justify-center font-bold transition"
                        >
                          +
                        </button>
                      </div>
                    </div>
                    <div className="text-right ml-4">
                      <button
                        onClick={() => removeItem(item.id)}
                        className="text-red-500 hover:text-red-700 mb-2 block ml-auto"
                      >
                        🗑️
                      </button>
                      <p className="text-2xl font-bold bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent\">${(item.price * item.quantity).toFixed(2)}</p>
                      <p className="text-gray-500 text-sm mt-1\">${item.price.toFixed(2)} each</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="lg:col-span-1">
              <div className="bg-white rounded-2xl shadow-lg p-8 h-fit sticky top-24 border-2 border-orange-100">
                <h2 className="text-3xl font-bold text-gray-800 mb-6">Order Summary</h2>
                <div className="space-y-4 mb-8">
                  <div className="flex justify-between text-gray-700 pb-4 border-b">
                    <span className="font-semibold">Subtotal:</span>
                    <span className="text-lg">${total.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-gray-700 pb-4 border-b">
                    <span className="font-semibold">Delivery:</span>
                    <span className="text-lg text-green-600 font-semibold">Free</span>
                  </div>
                  <div className="flex justify-between text-2xl font-bold text-gray-800 pt-4">
                    <span>Total:</span>
                    <span className="bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">${total.toFixed(2)}</span>
                  </div>
                </div>
                <Link
                  href="/checkout"
                  className="block w-full bg-gradient-to-r from-orange-600 to-red-600 text-white py-4 rounded-xl font-bold hover:shadow-lg transition transform hover:scale-105 mb-4 text-center"
                >
                  ✓ Proceed to Checkout
                </Link>
                <Link href="/menu" className="block w-full text-center text-orange-600 hover:text-orange-700 font-semibold py-3 rounded-xl hover:bg-orange-50 transition">
                  Continue shopping
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
