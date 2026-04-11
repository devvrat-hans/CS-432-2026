'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect, useRef } from 'react';
import { Upload, Download, Shield, LogIn, LayoutDashboard, Menu, X, User, LogOut, ChevronDown } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? (typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8080/api`
  : 'http://127.0.0.1:8080/api');

interface UserInfo {
  id: number;
  username: string;
  role: string;
  full_name: string;
  email: string;
  member_group: string;
}

function getCookieToken() {
  if (typeof document === 'undefined') return '';
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith('blinddrop_token='));
  return match ? match.split('=')[1] : '';
}

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [user, setUser] = useState<UserInfo | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = window.localStorage.getItem('blinddrop_token') || getCookieToken();
    if (!token) {
      setUser(null);
      return;
    }

    // Try cached user first
    const cached = window.localStorage.getItem('blinddrop_user');
    if (cached) {
      try {
        setUser(JSON.parse(cached));
        return;
      } catch { /* fall through */ }
    }

    // Fetch from API
    fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => {
        if (data.member) {
          setUser(data.member);
          window.localStorage.setItem('blinddrop_user', JSON.stringify(data.member));
        }
      })
      .catch(() => {
        setUser(null);
      });
  }, [pathname]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  // Don't render navbar on admin, dashboard, or profile pages (they have their own Header)
  if (pathname?.startsWith('/admin') || pathname?.startsWith('/dashboard') || pathname?.startsWith('/profile')) {
    return null;
  }

  const handleSignOut = () => {
    const token = window.localStorage.getItem('blinddrop_token') || getCookieToken();
    if (token) {
      fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => {});
    }
    window.localStorage.removeItem('blinddrop_token');
    window.localStorage.removeItem('blinddrop_user');
    document.cookie = 'blinddrop_token=; path=/; max-age=0';
    setUser(null);
    setDropdownOpen(false);
    setMenuOpen(false);
    router.push('/');
  };

  const navLinks = [
    { href: '/upload', label: 'Upload', icon: Upload },
    { href: '/download', label: 'Download', icon: Download },
  ];

  const isActive = (href: string) => pathname === href;

  const displayName = user?.full_name || user?.username || 'User';
  const initials = displayName
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  return (
    <nav className="bg-white border-b border-neutral-900 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Brand */}
          <Link href="/" className="flex items-center gap-2.5">
            <div className="p-1.5 border border-neutral-900 bg-neutral-100">
              <Shield size={16} className="text-neutral-900" />
            </div>
            <span className="text-lg font-extrabold tracking-tight text-neutral-900 uppercase">
              Blind Drop
            </span>
          </Link>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`
                  inline-flex items-center gap-2 px-4 py-2 text-xs font-bold uppercase tracking-widest transition-colors
                  ${isActive(link.href)
                    ? 'bg-neutral-900 text-white'
                    : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900'
                  }
                `}
              >
                <link.icon size={14} />
                {link.label}
              </Link>
            ))}

            <div className="w-px h-6 bg-neutral-300 mx-2" />

            {user ? (
              /* ── User dropdown ── */
              <div ref={dropdownRef} className="relative">
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="inline-flex items-center gap-2.5 px-3 py-1.5 text-xs font-bold uppercase tracking-widest text-neutral-700 hover:bg-neutral-100 transition-colors rounded-sm"
                >
                  <span className="w-7 h-7 bg-neutral-900 text-white text-[10px] font-bold flex items-center justify-center rounded-full">
                    {initials}
                  </span>
                  <span className="max-w-[120px] truncate">{displayName}</span>
                  <ChevronDown size={12} className={`transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
                </button>

                {dropdownOpen && (
                  <div className="absolute right-0 mt-1 w-56 bg-white border border-neutral-900 shadow-lg z-50">
                    {/* User info header */}
                    <div className="px-4 py-3 border-b border-neutral-200">
                      <p className="text-xs font-bold uppercase tracking-widest text-neutral-900 truncate">
                        {displayName}
                      </p>
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-400 mt-0.5">
                        {user.role}
                      </p>
                    </div>

                    {/* Menu items */}
                    <div className="py-1">
                      {user.role === 'admin' && (
                        <Link
                          href="/admin"
                          onClick={() => setDropdownOpen(false)}
                          className="flex items-center gap-3 px-4 py-2.5 text-xs font-bold uppercase tracking-widest text-neutral-700 hover:bg-neutral-100 transition-colors"
                        >
                          <LayoutDashboard size={14} />
                          Admin Panel
                        </Link>
                      )}
                      <Link
                        href="/profile"
                        onClick={() => setDropdownOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-xs font-bold uppercase tracking-widest text-neutral-700 hover:bg-neutral-100 transition-colors"
                      >
                        <User size={14} />
                        Profile
                      </Link>
                    </div>

                    <div className="border-t border-neutral-200">
                      <button
                        onClick={handleSignOut}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-xs font-bold uppercase tracking-widest text-red-600 hover:bg-red-50 transition-colors"
                      >
                        <LogOut size={14} />
                        Sign Out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <Link
                href="/login"
                className={`
                  inline-flex items-center gap-2 px-4 py-2 text-xs font-bold uppercase tracking-widest transition-colors
                  ${isActive('/login')
                    ? 'bg-neutral-900 text-white'
                    : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900'
                  }
                `}
              >
                <LogIn size={14} />
                Login
              </Link>
            )}
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden p-2 text-neutral-900 hover:bg-neutral-100 transition-colors"
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-neutral-900 bg-white">
          <div className="px-4 py-3 space-y-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMenuOpen(false)}
                className={`
                  flex items-center gap-3 px-3 py-3 text-xs font-bold uppercase tracking-widest transition-colors
                  ${isActive(link.href)
                    ? 'bg-neutral-900 text-white'
                    : 'text-neutral-700 hover:bg-neutral-100'
                  }
                `}
              >
                <link.icon size={16} />
                {link.label}
              </Link>
            ))}

            <div className="border-t border-neutral-200 my-2" />

            {user ? (
              <>
                {/* Mobile user info */}
                <div className="px-3 py-2.5 flex items-center gap-3">
                  <span className="w-8 h-8 bg-neutral-900 text-white text-xs font-bold flex items-center justify-center rounded-full flex-shrink-0">
                    {initials}
                  </span>
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest text-neutral-900 truncate">
                      {displayName}
                    </p>
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-400">
                      {user.role}
                    </p>
                  </div>
                </div>

                {user.role === 'admin' && (
                  <Link
                    href="/admin"
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-3 px-3 py-3 text-xs font-bold uppercase tracking-widest text-neutral-700 hover:bg-neutral-100 transition-colors"
                  >
                    <LayoutDashboard size={16} />
                    Admin Panel
                  </Link>
                )}
                <Link
                  href="/profile"
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-3 px-3 py-3 text-xs font-bold uppercase tracking-widest text-neutral-700 hover:bg-neutral-100 transition-colors"
                >
                  <User size={16} />
                  Profile
                </Link>
                <button
                  onClick={handleSignOut}
                  className="w-full flex items-center gap-3 px-3 py-3 text-xs font-bold uppercase tracking-widest text-red-600 hover:bg-red-50 transition-colors"
                >
                  <LogOut size={16} />
                  Sign Out
                </button>
              </>
            ) : (
              <Link
                href="/login"
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-3 px-3 py-3 text-xs font-bold uppercase tracking-widest text-neutral-700 hover:bg-neutral-100 transition-colors"
              >
                <LogIn size={16} />
                Login
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
