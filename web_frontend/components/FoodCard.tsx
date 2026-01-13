'use client';

import { useState } from 'react';

interface Food {
  id: number;
  name: string;
  description: string;
  price: number;
  image_url: string;
  category: string;
  available: boolean;
}

export default function FoodCard({ food, onAddToCart }: { food: Food; onAddToCart: (food: Food) => void }) {
  const [isAdded, setIsAdded] = useState(false);

  const handleAddToCart = () => {
    onAddToCart(food);
    setIsAdded(true);
    setTimeout(() => setIsAdded(false), 1500);
  };

  return (
    <div className={`bg-white rounded-2xl shadow-lg overflow-hidden hover:shadow-2xl transition transform duration-300 ${
      food.available ? 'hover:-translate-y-2' : ''
    } group relative`}>
      {/* Image Container */}
      <div className="relative h-56 bg-gradient-to-br from-orange-100 to-red-100 flex items-center justify-center text-6xl overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-orange-500 to-red-500 opacity-0 group-hover:opacity-10 transition duration-300"></div>
        <div className="relative group-hover:scale-110 transition transform duration-300">
          {food.image_url || '🍽️'}
        </div>
        {!food.available && (
          <div className="absolute inset-0 bg-black bg-opacity-40 flex items-center justify-center">
            <span className="text-white font-bold text-lg">Unavailable</span>
          </div>
        )}
        {food.available && (
          <div className="absolute top-3 right-3 bg-gradient-to-r from-orange-500 to-red-500 text-white px-3 py-1 rounded-full text-xs font-bold">
            Fresh
          </div>
        )}
      </div>

      {/* Content Container */}
      <div className="p-5">
        <h3 className="text-lg font-bold text-gray-800 line-clamp-2 group-hover:text-orange-600 transition">
          {food.name}
        </h3>
        <p className="text-gray-600 text-sm mt-2 line-clamp-2 leading-relaxed">
          {food.description}
        </p>

        {/* Footer with Price and Button */}
        <div className="flex justify-between items-center mt-5 pt-4 border-t border-gray-100">
          <div>
            <span className="text-2xl font-bold bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">
              ${food.price.toFixed(2)}
            </span>
          </div>
          <button
            onClick={handleAddToCart}
            disabled={!food.available}
            className={`px-5 py-2 rounded-xl font-semibold transition transform duration-300 flex items-center gap-2 ${
              food.available
                ? isAdded
                  ? 'bg-green-500 text-white scale-105'
                  : 'bg-gradient-to-r from-orange-500 to-red-600 text-white hover:shadow-lg hover:-translate-y-1 active:scale-95'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            {isAdded ? (
              <>
                <span>✓</span> Added
              </>
            ) : (
              <>
                <span>+</span> Add
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
