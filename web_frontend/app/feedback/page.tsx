'use client';

import { useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { apiClient } from '@/lib/api';

interface FeedbackForm {
  order_id?: string;
  restaurant_rating: number;
  delivery_rating: number;
  food_quality_rating: number;
  comments: string;
  would_recommend: boolean;
}

function Feedback() {
  const searchParams = useSearchParams();
  const orderId = searchParams.get('order_id');

  const [form, setForm] = useState<FeedbackForm>({
    order_id: orderId || undefined,
    restaurant_rating: 0,
    delivery_rating: 0,
    food_quality_rating: 0,
    comments: '',
    would_recommend: true
  });

  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRatingChange = (field: keyof FeedbackForm, rating: number) => {
    setForm(prev => ({ ...prev, [field]: rating }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (form.restaurant_rating === 0 || form.delivery_rating === 0 || form.food_quality_rating === 0) {
      setError('Please provide ratings for all categories');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post('/api/feedback', form as unknown as Record<string, unknown>);

      if (response.success) {
        setSubmitted(true);
      } else {
        setError('Failed to submit feedback. Please try again.');
      }
    } catch (err) {
      setError('Failed to submit feedback. Please check your connection and try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const StarRating = ({
    rating,
    onRatingChange,
    label
  }: {
    rating: number;
    onRatingChange: (rating: number) => void;
    label: string;
  }) => (
    <div className="mb-6">
      <label className="block text-lg font-semibold text-gray-800 mb-3">{label}</label>
      <div className="flex space-x-2">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => onRatingChange(star)}
            className={`text-3xl transition-colors ${
              star <= rating ? 'text-yellow-400' : 'text-gray-300'
            } hover:text-yellow-400`}
          >
            ⭐
          </button>
        ))}
      </div>
      <p className="text-sm text-gray-600 mt-1">
        {rating === 0 ? 'Click to rate' : `${rating} star${rating !== 1 ? 's' : ''}`}
      </p>
    </div>
  );

  if (submitted) {
    return (
      <div className="bg-gradient-to-b from-green-50 via-white to-slate-50 min-h-screen">
        <div className="max-w-2xl mx-auto px-4 md:px-6 py-12">
          <div className="text-center">
            <div className="text-8xl mb-6">🙏</div>
            <h1 className="text-4xl font-bold text-green-800 mb-4">Thank You for Your Feedback!</h1>
            <p className="text-xl text-gray-600 mb-8">
              Your feedback helps us improve our service and make every meal better.
            </p>

            <div className="space-x-4">
              <Link
                href="/menu"
                className="bg-orange-500 hover:bg-orange-600 text-white px-8 py-3 rounded-lg font-semibold transition-colors inline-block"
              >
                Order Again
              </Link>
              <Link
                href="/"
                className="bg-gray-500 hover:bg-gray-600 text-white px-6 py-3 rounded-lg font-semibold transition-colors inline-block"
              >
                Go Home
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-b from-orange-50 via-white to-slate-50 min-h-screen">
      <div className="max-w-2xl mx-auto px-4 md:px-6 py-12">
        <div className="text-center mb-8">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-800 mb-4">💬 Share Your Feedback</h1>
          <p className="text-lg text-gray-600">Help us improve by sharing your experience</p>
        </div>

        <div className="bg-white rounded-xl shadow-lg p-8">
          <form onSubmit={handleSubmit}>
            {orderId && (
              <div className="mb-6 p-4 bg-blue-50 rounded-lg">
                <p className="text-blue-800 font-semibold">Providing feedback for Order #{orderId}</p>
              </div>
            )}

            {error && (
              <div className="bg-gradient-to-r from-red-100 to-red-50 border-l-4 border-red-500 text-red-700 px-4 py-3 rounded-lg mb-6">
                <p className="font-semibold">⚠️ {error}</p>
              </div>
            )}

            <StarRating
              rating={form.restaurant_rating}
              onRatingChange={(rating) => handleRatingChange('restaurant_rating', rating)}
              label="🏪 How would you rate the restaurant?"
            />

            <StarRating
              rating={form.delivery_rating}
              onRatingChange={(rating) => handleRatingChange('delivery_rating', rating)}
              label="🚴 How was the delivery experience?"
            />

            <StarRating
              rating={form.food_quality_rating}
              onRatingChange={(rating) => handleRatingChange('food_quality_rating', rating)}
              label="🍽️ How was the food quality?"
            />

            <div className="mb-6">
              <label className="block text-lg font-semibold text-gray-800 mb-3">
                📝 Additional Comments
              </label>
              <textarea
                value={form.comments}
                onChange={(e) => setForm(prev => ({ ...prev, comments: e.target.value }))}
                placeholder="Tell us more about your experience... (optional)"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent resize-none"
                rows={4}
              />
            </div>

            <div className="mb-8">
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.would_recommend}
                  onChange={(e) => setForm(prev => ({ ...prev, would_recommend: e.target.checked }))}
                  className="mr-3 h-5 w-5 text-orange-600 focus:ring-orange-500 border-gray-300 rounded"
                />
                <span className="text-lg font-semibold text-gray-800">
                  👍 Would you recommend this restaurant to others?
                </span>
              </label>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 disabled:from-gray-400 disabled:to-gray-500 text-white py-4 px-6 rounded-lg font-bold text-lg transition-all transform hover:scale-105 disabled:hover:scale-100 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white mr-2"></div>
                  Submitting Feedback...
                </div>
              ) : (
                'Submit Feedback'
              )}
            </button>
          </form>
        </div>

        <div className="mt-8 text-center">
          <Link
            href="/menu"
            className="text-orange-600 hover:text-orange-800 font-semibold"
          >
            ← Back to Menu
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function FeedbackPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Feedback />
    </Suspense>
  );
}