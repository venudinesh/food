'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';

export default function Home() {
  const [animateHero, setAnimateHero] = useState(false);

  useEffect(() => {
    // Small delay to ensure smooth animation
    const timer = setTimeout(() => {
      setAnimateHero(true);
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="bg-gradient-to-b from-orange-50 via-white to-slate-50 min-h-screen">
      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-16 md:py-24">
        <div className={`text-center mb-16 transition-all duration-1000 ${
          animateHero ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
        }`}>
          <div className="mb-6">
            <span className="text-7xl md:text-8xl inline-block animate-bounce-subtle">🍔</span>
          </div>
          <h1 className="text-5xl md:text-7xl font-bold mb-4 gradient-text leading-tight">
            Smart Food
          </h1>
          <p className="text-xl md:text-2xl text-gray-600 mb-8 font-light">
            Delicious meals delivered to your door in minutes
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link
              href="/menu"
              className="bg-gradient-to-r from-orange-600 to-red-600 text-white px-8 py-4 rounded-xl text-lg font-bold hover:shadow-glow-hover shadow-glow transition transform hover:scale-110 hover:shadow-2xl"
            >
              🛒 Order Now
            </Link>
            <Link
              href="/orders"
              className="border-2 border-orange-600 text-orange-600 px-8 py-4 rounded-xl text-lg font-bold hover:bg-orange-50 transition transform hover:scale-105 bg-white"
            >
              📦 Track Orders
            </Link>
          </div>
        </div>

        {/* Features Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8 mt-20 md:mt-32">
          {[
            { icon: '⚡', title: 'Fast Delivery', desc: 'Get your food delivered in 30 minutes or less', color: 'from-blue-500' },
            { icon: '🍽️', title: 'Fresh Quality', desc: 'We use only the freshest ingredients for every meal', color: 'from-green-500' },
            { icon: '💰', title: 'Best Prices', desc: 'Amazing food at affordable prices, always', color: 'from-purple-500' },
          ].map((feature, idx) => (
            <div
              key={idx}
              className="bg-white rounded-2xl shadow-lg p-8 text-center hover:shadow-2xl hover:-translate-y-2 transition transform duration-300 overflow-hidden group"
            >
              <div className={`absolute inset-0 bg-gradient-to-br ${feature.color} to-orange-500 opacity-0 group-hover:opacity-10 transition duration-300`}></div>
              <div className="relative">
                <div className="text-6xl mb-4 inline-block group-hover:scale-125 transition transform duration-300">{feature.icon}</div>
                <h3 className="text-xl font-bold text-gray-800 mb-2">{feature.title}</h3>
                <p className="text-gray-600 leading-relaxed">{feature.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Stats Section */}
        <div className="grid grid-cols-3 gap-4 mt-20 md:mt-32">
          {[
            { number: '50K+', label: 'Happy Customers' },
            { number: '1000+', label: 'Food Items' },
            { number: '100+', label: 'Restaurants' },
          ].map((stat, idx) => (
            <div key={idx} className="bg-gradient-to-br from-orange-500 to-red-600 rounded-2xl p-6 text-white text-center shadow-lg">
              <div className="text-3xl md:text-4xl font-bold">{stat.number}</div>
              <div className="text-sm md:text-base text-orange-100 mt-2">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* CTA Section */}
        <div className="mt-20 md:mt-32 bg-gradient-to-r from-orange-500 via-red-500 to-pink-500 rounded-3xl p-12 md:p-16 text-white text-center shadow-2xl relative overflow-hidden">
          <div className="absolute inset-0 opacity-20">
            <div className="absolute top-0 left-0 w-40 h-40 bg-white rounded-full -translate-x-1/2 -translate-y-1/2"></div>
            <div className="absolute bottom-0 right-0 w-40 h-40 bg-white rounded-full translate-x-1/2 translate-y-1/2"></div>
          </div>
          <div className="relative">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Ready to Taste Deliciousness?</h2>
            <p className="text-lg md:text-xl mb-8 text-orange-100">Browse our full menu and place your order in seconds!</p>
            <Link
              href="/menu"
              className="inline-block bg-white text-orange-600 px-10 py-4 rounded-xl font-bold hover:bg-gray-50 transition transform hover:scale-110 shadow-lg hover:shadow-2xl"
            >
              ✨ View Full Menu
            </Link>
          </div>
        </div>

        {/* Testimonial Section */}
        <div className="mt-20 md:mt-32">
          <h2 className="text-4xl font-bold text-center mb-12 gradient-text">What Our Customers Say</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { stars: 5, text: 'Amazing quality and super fast delivery!', author: 'Sarah M.' },
              { stars: 5, text: 'Best food I have ever ordered online.', author: 'John D.' },
              { stars: 5, text: 'Great prices and excellent service!', author: 'Emma K.' },
            ].map((review, idx) => (
              <div key={idx} className="bg-white rounded-2xl p-6 shadow-lg hover:shadow-2xl transition transform hover:-translate-y-1">
                <div className="flex gap-1 mb-4">
                  {[...Array(review.stars)].map((_, i) => (
                    <span key={i} className="text-2xl">⭐</span>
                  ))}
                </div>
                <p className="text-gray-600 mb-4 italic">&ldquo;{review.text}&rdquo;</p>
                <p className="text-gray-800 font-semibold">— {review.author}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
