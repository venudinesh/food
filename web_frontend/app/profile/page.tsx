'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';

interface User {
  id: number;
  username: string;
  email: string;
  created_at?: string;
}

interface Order {
  id: number;
  status: string;
  total: number;
  delivery_address: string;
  created_at: string;
  estimated_delivery?: string;
  restaurant_name: string;
  items_count: number;
  items: Array<{
    id: number;
    name: string;
    price: number;
    quantity: number;
    subtotal: number;
  }>;
}

interface Stream {
  room_id: string;
  order_id: number;
  chef_id: number;
  customer_id: number;
  status: string;
  participants: Array<{ id: number; username: string; role: string }>;
  created_at: string;
  stream_type: string;
  quality: string;
}

export default function Profile() {
  const { logout, isAuthenticated } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<User | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({ username: '', email: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [orders, setOrders] = useState<Order[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [streams, setStreams] = useState<Stream[]>([]);
  const [streamsLoading, setStreamsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('profile');
  const [message, setMessage] = useState('');
  
  // Settings state
  const [settings, setSettings] = useState({
    phone: '',
    address: '',
    full_name: '',
    notifications_enabled: true,
    order_notifications: true,
    promotional_emails: false,
    sms_notifications: false,
    dietary_preferences: [] as string[],
    default_payment_method: 'card',
    preferred_delivery_time: 'asap',
    saved_addresses: [] as Array<{ id: string; label: string; address: string }>,
  });
  const [settingsEditing, setSettingsEditing] = useState(false);

  const fetchOrders = async () => {
    setOrdersLoading(true);
    try {
      const response = await fetch('http://localhost:5000/api/orders/user', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setOrders(data.orders || []);
      } else {
        console.error('Failed to fetch orders');
      }
    } catch (error) {
      console.error('Error fetching orders:', error);
    } finally {
      setOrdersLoading(false);
    }
  };

  const fetchStreams = async () => {
    setStreamsLoading(true);
    try {
      const response = await fetch('http://localhost:5000/api/streams/user', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setStreams(data.streams || []);
      } else {
        console.error('Failed to fetch streams');
      }
    } catch (error) {
      console.error('Error fetching streams:', error);
    } finally {
      setStreamsLoading(false);
    }
  };

  const createStream = async (orderId: number) => {
    try {
      const response = await fetch('http://localhost:5000/api/streams/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({ order_id: orderId }),
      });

      if (response.ok) {
        const data = await response.json();
        router.push(data.stream_url);
      } else {
        const error = await response.json();
        setMessage(error.error || 'Failed to create stream');
      }
    } catch {
      setMessage('Error creating stream');
    }
  };

  useEffect(() => {
    if (activeTab === 'orders' && isAuthenticated) {
      fetchOrders();
    } else if (activeTab === 'streams' && isAuthenticated) {
      fetchStreams();
    }
  }, [activeTab, isAuthenticated]);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage('');

    try {
      const response = await fetch('http://localhost:5000/api/auth/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify(editForm),
      });

      const data = await response.json();

      if (data.success) {
        setProfile(data.user);
        setMessage('Profile updated successfully!');
        setIsEditing(false);
        // Update the auth context user
        window.location.reload(); // Simple way to refresh user data
      } else {
        setMessage(data.error || 'Failed to update profile');
      }
    } catch {
      setMessage('Failed to update profile. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target as HTMLFormElement);
    const currentPassword = formData.get('currentPassword') as string;
    const newPassword = formData.get('newPassword') as string;
    const confirmPassword = formData.get('confirmPassword') as string;

    if (newPassword !== confirmPassword) {
      setMessage('New passwords do not match');
      return;
    }

    setIsLoading(true);
    setMessage('');

    try {
      const response = await fetch('http://localhost:5000/api/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setMessage('Password changed successfully!');
        (e.target as HTMLFormElement).reset();
      } else {
        setMessage(data.error || 'Failed to change password');
      }
    } catch {
      setMessage('Failed to change password. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    setIsLoading(true);
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    
    try {
      const response = await fetch(`${API_URL}/api/auth/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          full_name: settings.full_name,
          phone: settings.phone,
          address: settings.address,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setMessage('Settings saved successfully!');
        setTimeout(() => setMessage(''), 3000);
      } else {
        setMessage(data.error || 'Failed to save settings');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      setMessage('Failed to save settings. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isAuthenticated || !profile) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-orange-50 via-white to-slate-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-orange-50 via-white to-slate-50">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-12">
        <div className="bg-white rounded-xl shadow-lg overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-orange-500 to-red-500 text-white px-6 py-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold">👤 My Profile</h1>
                <p className="text-orange-100 mt-1">Manage your account settings</p>
              </div>
              <button
                onClick={logout}
                className="bg-white text-orange-600 px-4 py-2 rounded-lg font-semibold hover:bg-orange-50 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="flex">
              <button
                onClick={() => setActiveTab('profile')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'profile'
                    ? 'border-orange-500 text-orange-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Profile Information
              </button>
              <button
                onClick={() => setActiveTab('security')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'security'
                    ? 'border-orange-500 text-orange-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Security
              </button>
              <button
                onClick={() => setActiveTab('orders')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'orders'
                    ? 'border-orange-500 text-orange-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Order History
              </button>
              <button
                onClick={() => setActiveTab('streams')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'streams'
                    ? 'border-orange-500 text-orange-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Live Streams
              </button>
              <button
                onClick={() => setActiveTab('settings')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'settings'
                    ? 'border-orange-500 text-orange-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                ⚙️ Settings
              </button>
            </nav>
          </div>

          {/* Content */}
          <div className="p-6">
            {message && (
              <div className={`mb-6 p-4 rounded-lg ${
                message.includes('successfully')
                  ? 'bg-green-50 border-l-4 border-green-400 text-green-700'
                  : 'bg-red-50 border-l-4 border-red-400 text-red-700'
              }`}>
                {message}
              </div>
            )}

            {activeTab === 'profile' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-gray-900">Profile Information</h2>
                  <button
                    onClick={() => setIsEditing(!isEditing)}
                    className="bg-orange-500 text-white px-4 py-2 rounded-lg font-semibold hover:bg-orange-600 transition-colors"
                  >
                    {isEditing ? 'Cancel' : 'Edit Profile'}
                  </button>
                </div>

                {isEditing ? (
                  <form onSubmit={handleUpdateProfile} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Username</label>
                      <input
                        type="text"
                        value={editForm.username}
                        onChange={(e) => setEditForm({ ...editForm, username: e.target.value })}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-orange-500 focus:border-orange-500"
                        minLength={3}
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Email</label>
                      <input
                        type="email"
                        value={editForm.email}
                        onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-orange-500 focus:border-orange-500"
                        required
                      />
                    </div>
                    <div className="flex space-x-4">
                      <button
                        type="submit"
                        disabled={isLoading}
                        className="bg-orange-500 text-white px-6 py-2 rounded-lg font-semibold hover:bg-orange-600 disabled:opacity-50"
                      >
                        {isLoading ? 'Saving...' : 'Save Changes'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setIsEditing(false)}
                        className="bg-gray-500 text-white px-6 py-2 rounded-lg font-semibold hover:bg-gray-600"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                ) : (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-500">Username</label>
                        <p className="mt-1 text-lg text-gray-900">{profile.username}</p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-500">Email</label>
                        <p className="mt-1 text-lg text-gray-900">{profile.email}</p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-500">Member Since</label>
                        <p className="mt-1 text-lg text-gray-900">
                          {profile.created_at ? new Date(profile.created_at).toLocaleDateString() : 'N/A'}
                        </p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-500">Account Status</label>
                        <p className="mt-1 text-lg text-green-600">Active</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'security' && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold text-gray-900">Change Password</h2>
                <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Current Password</label>
                    <input
                      type="password"
                      name="currentPassword"
                      required
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-orange-500 focus:border-orange-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">New Password</label>
                    <input
                      type="password"
                      name="newPassword"
                      required
                      minLength={6}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-orange-500 focus:border-orange-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Confirm New Password</label>
                    <input
                      type="password"
                      name="confirmPassword"
                      required
                      minLength={6}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-orange-500 focus:border-orange-500"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="bg-orange-500 text-white px-6 py-2 rounded-lg font-semibold hover:bg-orange-600 disabled:opacity-50"
                  >
                    {isLoading ? 'Changing...' : 'Change Password'}
                  </button>
                </form>
              </div>
            )}

            {activeTab === 'orders' && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold text-gray-900">Order History</h2>

                {ordersLoading ? (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto"></div>
                    <p className="text-gray-500 mt-4">Loading your orders...</p>
                  </div>
                ) : orders.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="text-6xl mb-4">📦</div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No orders yet</h3>
                    <p className="text-gray-500 mb-4">Your order history will appear here once you place your first order.</p>
                    <a
                      href="/menu"
                      className="bg-orange-500 text-white px-6 py-2 rounded-lg font-semibold hover:bg-orange-600 transition-colors inline-block"
                    >
                      Start Ordering
                    </a>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {orders.map((order) => (
                      <div key={order.id} className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                        <div className="flex justify-between items-start mb-4">
                          <div>
                            <h3 className="text-lg font-semibold text-gray-900">
                              Order #{order.id}
                            </h3>
                            <p className="text-sm text-gray-600">
                              {order.restaurant_name} • {new Date(order.created_at).toLocaleDateString()}
                            </p>
                          </div>
                          <div className="text-right">
                            <div className="text-lg font-bold text-gray-900">
                              ${order.total.toFixed(2)}
                            </div>
                            <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              order.status === 'delivered' ? 'bg-green-100 text-green-800' :
                              order.status === 'preparing' ? 'bg-yellow-100 text-yellow-800' :
                              order.status === 'out_for_delivery' ? 'bg-blue-100 text-blue-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {order.status.replace('_', ' ').toUpperCase()}
                            </div>
                          </div>
                        </div>

                        <div className="mb-4">
                          <p className="text-sm text-gray-600">
                            <span className="font-medium">Delivery to:</span> {order.delivery_address}
                          </p>
                          {order.estimated_delivery && (
                            <p className="text-sm text-gray-600">
                              <span className="font-medium">Estimated delivery:</span> {new Date(order.estimated_delivery).toLocaleString()}
                            </p>
                          )}
                        </div>

                        <div className="border-t pt-4">
                          <h4 className="text-sm font-medium text-gray-900 mb-2">
                            Items ({order.items_count})
                          </h4>
                          <div className="space-y-2">
                            {order.items.map((item, index) => (
                              <div key={index} className="flex justify-between text-sm">
                                <span className="text-gray-600">
                                  {item.quantity}x {item.name}
                                </span>
                                <span className="text-gray-900 font-medium">
                                  ${item.subtotal.toFixed(2)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="mt-4 flex space-x-2">
                          <button
                            onClick={() => router.push(`/order/${order.id}`)}
                            className="text-orange-600 hover:text-orange-800 text-sm font-medium"
                          >
                            View Details
                          </button>
                          <button
                            onClick={() => router.push(`/order/${order.id}/track`)}
                            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                          >
                            Track Order
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'streams' && (
              <div className="space-y-6">
                <div className="flex justify-between items-center">
                  <h2 className="text-xl font-semibold text-gray-900">Live Streams</h2>
                  <button
                    onClick={() => setActiveTab('orders')}
                    className="bg-orange-500 text-white px-4 py-2 rounded-lg font-semibold hover:bg-orange-600 transition-colors"
                  >
                    Create New Stream
                  </button>
                </div>

                {streamsLoading ? (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto"></div>
                    <p className="text-gray-500 mt-4">Loading your streams...</p>
                  </div>
                ) : streams.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="text-6xl mb-4">📹</div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No active streams</h3>
                    <p className="text-gray-500 mb-4">Create a live stream to interact with chefs during your orders.</p>
                    <button
                      onClick={() => setActiveTab('orders')}
                      className="bg-orange-500 text-white px-6 py-2 rounded-lg font-semibold hover:bg-orange-600 transition-colors inline-block"
                    >
                      View Orders to Stream
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {streams.map((stream) => (
                      <div key={stream.room_id} className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                        <div className="flex justify-between items-start mb-4">
                          <div>
                            <h3 className="text-lg font-semibold text-gray-900">
                              Stream for Order #{stream.order_id}
                            </h3>
                            <p className="text-sm text-gray-600">
                              Created {new Date(stream.created_at).toLocaleString()}
                            </p>
                          </div>
                          <div className="text-right">
                            <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              stream.status === 'active' ? 'bg-green-100 text-green-800' :
                              stream.status === 'waiting' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {stream.status.toUpperCase()}
                            </div>
                          </div>
                        </div>

                        <div className="mb-4">
                          <p className="text-sm text-gray-600">
                            <span className="font-medium">Participants:</span> {stream.participants.length}/2
                          </p>
                          <p className="text-sm text-gray-600">
                            <span className="font-medium">Quality:</span> {stream.quality.toUpperCase()}
                          </p>
                        </div>

                        <div className="flex space-x-2">
                          <button
                            onClick={() => router.push(`/stream/${stream.room_id}`)}
                            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-semibold text-sm"
                          >
                            Join Stream
                          </button>
                          <button
                            onClick={() => router.push(`/order/${stream.order_id}`)}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-semibold text-sm"
                          >
                            View Order
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Create Stream from Orders */}
                {activeTab === 'streams' && orders.length > 0 && (
                  <div className="mt-8">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Create Stream from Order</h3>
                    <div className="space-y-3">
                      {orders.slice(0, 3).map((order) => (
                        <div key={order.id} className="bg-white border border-gray-200 rounded-lg p-4 flex justify-between items-center">
                          <div>
                            <p className="font-medium">Order #{order.id}</p>
                            <p className="text-sm text-gray-600">{order.restaurant_name} • {new Date(order.created_at).toLocaleDateString()}</p>
                          </div>
                          <button
                            onClick={() => createStream(order.id)}
                            className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg font-semibold text-sm"
                          >
                            Start Live Stream
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'settings' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-gray-900">Account Settings</h2>
                  <button
                    onClick={() => {
                      if (settingsEditing) {
                        // Save settings when clicking "Done"
                        handleSaveSettings();
                      }
                      setSettingsEditing(!settingsEditing);
                    }}
                    className="bg-orange-500 text-white px-4 py-2 rounded-lg font-semibold hover:bg-orange-600 transition-colors"
                  >
                    {settingsEditing ? 'Save & Done' : 'Edit Settings'}
                  </button>
                </div>

                {/* Personal Information */}
                <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">📋 Personal Information</h3>
                  
                  {settingsEditing ? (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700">Full Name</label>
                        <input
                          type="text"
                          value={settings.full_name}
                          onChange={(e) => setSettings({ ...settings, full_name: e.target.value })}
                          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-orange-500 focus:border-orange-500"
                          placeholder="John Doe"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700">Phone Number</label>
                        <input
                          type="tel"
                          value={settings.phone}
                          onChange={(e) => setSettings({ ...settings, phone: e.target.value })}
                          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-orange-500 focus:border-orange-500"
                          placeholder="+91 9876543210"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700">Default Address</label>
                        <textarea
                          value={settings.address}
                          onChange={(e) => setSettings({ ...settings, address: e.target.value })}
                          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-orange-500 focus:border-orange-500"
                          placeholder="Enter your default delivery address"
                          rows={3}
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-gray-600">Full Name</p>
                        <p className="text-gray-900 font-medium">{settings.full_name || 'Not set'}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Phone Number</p>
                        <p className="text-gray-900 font-medium">{settings.phone || 'Not set'}</p>
                      </div>
                      <div className="md:col-span-2">
                        <p className="text-sm text-gray-600">Default Address</p>
                        <p className="text-gray-900 font-medium">{settings.address || 'Not set'}</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Delivery Preferences */}
                <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">🚚 Delivery Preferences</h3>
                  
                  {settingsEditing ? (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Preferred Delivery Time</label>
                        <select
                          value={settings.preferred_delivery_time}
                          onChange={(e) => setSettings({ ...settings, preferred_delivery_time: e.target.value })}
                          className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-orange-500 focus:border-orange-500"
                        >
                          <option value="asap">As Soon As Possible</option>
                          <option value="schedule">Schedule Later</option>
                          <option value="urgent">Urgent (Extra Charge)</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Default Payment Method</label>
                        <select
                          value={settings.default_payment_method}
                          onChange={(e) => setSettings({ ...settings, default_payment_method: e.target.value })}
                          className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-orange-500 focus:border-orange-500"
                        >
                          <option value="card">Credit/Debit Card</option>
                          <option value="upi">UPI</option>
                          <option value="cod">Cash on Delivery</option>
                          <option value="wallet">Digital Wallet</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-3">Dietary Preferences</label>
                        <div className="space-y-2">
                          {['Vegetarian', 'Vegan', 'Gluten-Free', 'Halal', 'Kosher', 'No Dairy'].map((pref) => (
                            <label key={pref} className="flex items-center">
                              <input
                                type="checkbox"
                                checked={settings.dietary_preferences.includes(pref)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSettings({
                                      ...settings,
                                      dietary_preferences: [...settings.dietary_preferences, pref]
                                    });
                                  } else {
                                    setSettings({
                                      ...settings,
                                      dietary_preferences: settings.dietary_preferences.filter(p => p !== pref)
                                    });
                                  }
                                }}
                                className="rounded border-gray-300 text-orange-600"
                              />
                              <span className="ml-2 text-gray-700">{pref}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-gray-600">Preferred Delivery Time</p>
                        <p className="text-gray-900 font-medium capitalize">{settings.preferred_delivery_time.replace(/_/g, ' ')}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Default Payment Method</p>
                        <p className="text-gray-900 font-medium capitalize">{settings.default_payment_method}</p>
                      </div>
                      <div className="md:col-span-2">
                        <p className="text-sm text-gray-600">Dietary Preferences</p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {settings.dietary_preferences.length > 0 ? (
                            settings.dietary_preferences.map((pref) => (
                              <span key={pref} className="bg-orange-100 text-orange-800 px-3 py-1 rounded-full text-sm">
                                {pref}
                              </span>
                            ))
                          ) : (
                            <p className="text-gray-500">None selected</p>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Notifications */}
                <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">🔔 Notifications</h3>
                  
                  {settingsEditing ? (
                    <div className="space-y-3">
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={settings.notifications_enabled}
                          onChange={(e) => setSettings({ ...settings, notifications_enabled: e.target.checked })}
                          className="rounded border-gray-300 text-orange-600"
                        />
                        <span className="ml-2 text-gray-700">Enable all notifications</span>
                      </label>
                      <label className="flex items-center opacity-60">
                        <input
                          type="checkbox"
                          checked={settings.order_notifications}
                          disabled={!settings.notifications_enabled}
                          onChange={(e) => setSettings({ ...settings, order_notifications: e.target.checked })}
                          className="rounded border-gray-300 text-orange-600"
                        />
                        <span className="ml-2 text-gray-700">Order status updates</span>
                      </label>
                      <label className="flex items-center opacity-60">
                        <input
                          type="checkbox"
                          checked={settings.promotional_emails}
                          disabled={!settings.notifications_enabled}
                          onChange={(e) => setSettings({ ...settings, promotional_emails: e.target.checked })}
                          className="rounded border-gray-300 text-orange-600"
                        />
                        <span className="ml-2 text-gray-700">Promotional offers & deals</span>
                      </label>
                      <label className="flex items-center opacity-60">
                        <input
                          type="checkbox"
                          checked={settings.sms_notifications}
                          disabled={!settings.notifications_enabled}
                          onChange={(e) => setSettings({ ...settings, sms_notifications: e.target.checked })}
                          className="rounded border-gray-300 text-orange-600"
                        />
                        <span className="ml-2 text-gray-700">SMS notifications</span>
                      </label>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-gray-700">Notifications</span>
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                          settings.notifications_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {settings.notifications_enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                      <div className="space-y-1 text-sm text-gray-600">
                        <p>✓ Order updates: {settings.order_notifications ? 'On' : 'Off'}</p>
                        <p>✓ Promotional: {settings.promotional_emails ? 'On' : 'Off'}</p>
                        <p>✓ SMS alerts: {settings.sms_notifications ? 'On' : 'Off'}</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Privacy & Security */}
                <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">🔒 Privacy & Security</h3>
                  <div className="space-y-3">
                    <button className="w-full text-left px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition">
                      <p className="font-medium text-gray-900">Change Password</p>
                      <p className="text-sm text-gray-600">Update your account password</p>
                    </button>
                    <button className="w-full text-left px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition">
                      <p className="font-medium text-gray-900">Two-Factor Authentication</p>
                      <p className="text-sm text-gray-600">Secure your account with 2FA</p>
                    </button>
                    <button className="w-full text-left px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition">
                      <p className="font-medium text-gray-900">Login Activity</p>
                      <p className="text-sm text-gray-600">View your recent login history</p>
                    </button>
                  </div>
                </div>

                {settingsEditing && (
                  <div className="flex space-x-4">
                    <button
                      onClick={() => {
                        setSettingsEditing(false);
                        setMessage('Settings saved successfully!');
                        setTimeout(() => setMessage(''), 3000);
                      }}
                      className="bg-orange-500 text-white px-6 py-2 rounded-lg font-semibold hover:bg-orange-600 transition-colors"
                    >
                      Save Settings
                    </button>
                    <button
                      onClick={() => setSettingsEditing(false)}
                      className="bg-gray-500 text-white px-6 py-2 rounded-lg font-semibold hover:bg-gray-600 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

