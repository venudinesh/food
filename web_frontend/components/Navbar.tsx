'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { useCart } from '@/lib/cart-context';
import { useAuth } from '@/lib/auth-context';

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const [isHydrated, setIsHydrated] = useState(false);
  const pathname = usePathname();
  const { itemCount } = useCart();
  const { user, isAuthenticated, logout } = useAuth();

  useEffect(() => {
    setIsHydrated(true);
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const isActive = (href: string) => pathname === href;

  const authenticatedNavItems = [
    { href: '/menu', label: 'Menu', icon: '📋' },
    { href: '/cart', label: 'Cart', icon: '🛒' },
    { href: '/orders', label: 'Orders', icon: '📦' },
    { href: '/profile', label: 'Profile', icon: '👤' },
  ];

  const unauthenticatedNavItems = [
    { href: '/menu', label: 'Menu', icon: '📋' },
    { href: '/cart', label: 'Cart', icon: '🛒' },
  ];

  const navItems = isAuthenticated ? authenticatedNavItems : unauthenticatedNavItems;

  const handleLogout = () => {
    logout();
    setIsOpen(false);
  };

  return (
    <nav className={`sticky top-0 z-50 transition-all var(--transition-base) ${
      isScrolled
        ? 'bg-gradient-to-r from-orange-600 to-red-600 shadow-2xl backdrop-blur-md'
        : 'bg-gradient-to-r from-orange-500 to-red-500 shadow-lg'
    } text-white`}>
      <div className="max-w-7xl mx-auto px-4 md:px-6">
        <div className="flex justify-between items-center h-20">
          <Link
            href="/"
            className="text-3xl font-bold flex items-center gap-2 hover:scale-105 transition-transform var(--transition-base) shadow-glow"
          >
            🍔 <span className="hidden sm:inline">Smart Food</span>
          </Link>

          <div className="hidden md:flex gap-1 items-center">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`px-4 py-2 rounded-lg font-semibold flex items-center gap-1 transition-all var(--transition-base) relative ${
                  isActive(item.href)
                    ? 'bg-white text-orange-600 shadow-glow'
                    : 'hover:bg-white hover:bg-opacity-20 text-white hover:text-white'
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
                {item.href === '/cart' && isHydrated && itemCount > 0 && (
                  <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center font-bold animate-pulse-glow">
                    {itemCount}
                  </span>
                )}
              </Link>
            ))}

            {/* Authentication buttons */}
            <div className="ml-4 flex items-center gap-2">
              {isAuthenticated ? (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-orange-100">Welcome, {user?.username}!</span>
                  <button
                    onClick={handleLogout}
                    className="btn-primary hover:shadow-glow"
                  >
                    Logout
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Link
                    href="/login"
                    className="btn-primary hover:shadow-glow"
                  >
                    Login
                  </Link>
                  <Link
                    href="/register"
                    className="btn-secondary hover:shadow-glow"
                  >
                    Sign Up
                  </Link>
                </div>
              )}
            </div>
          </div>

          <button
            onClick={() => setIsOpen(!isOpen)}
            className="md:hidden p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition-colors var(--transition-base)"
            aria-label="Toggle menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>

        {isOpen && (
          <div className="md:hidden pb-4 space-y-2 bg-black bg-opacity-10 rounded-lg p-2 animate-slideInRight">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setIsOpen(false)}
                className={`block px-4 py-3 rounded-lg transition-all duration-300 relative ${
                  isActive(item.href)
                    ? 'bg-white text-orange-600 font-semibold'
                    : 'hover:bg-white hover:bg-opacity-20'
                }`}
              >
                <span>{item.icon}</span> {item.label}
                {item.href === '/cart' && isHydrated && itemCount > 0 && (
                  <span className="ml-2 bg-red-500 text-white text-xs rounded-full h-5 w-5 inline-flex items-center justify-center font-bold">
                    {itemCount}
                  </span>
                )}
              </Link>
            ))}

            {/* Mobile authentication buttons */}
            <div className="border-t border-white border-opacity-20 mt-4 pt-4">
              {isAuthenticated ? (
                <div className="space-y-2">
                  <div className="px-4 py-2 text-sm text-orange-100">
                    Welcome, {user?.username}!
                  </div>
                  <button
                    onClick={handleLogout}
                    className="block w-full text-left px-4 py-3 bg-white text-orange-600 rounded-lg font-semibold hover:bg-orange-50 transition-colors"
                  >
                    Logout
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Link
                    href="/login"
                    onClick={() => setIsOpen(false)}
                    className="block px-4 py-3 bg-white text-orange-600 rounded-lg font-semibold hover:bg-orange-50 transition-colors text-center"
                  >
                    Login
                  </Link>
                  <Link
                    href="/register"
                    onClick={() => setIsOpen(false)}
                    className="block px-4 py-3 bg-orange-700 text-white rounded-lg font-semibold hover:bg-orange-800 transition-colors text-center"
                  >
                    Sign Up
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
