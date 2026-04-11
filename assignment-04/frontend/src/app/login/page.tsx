'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? (typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8080/api`
  : 'http://127.0.0.1:8080/api');

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (loading) return;
    handleLogin();
  };

  const handleLogin = async () => {
    setLoading(true);
    setError('');

    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.error || 'Login failed');
        setLoading(false);
        return;
      }

      const token = data.token || '';
      window.localStorage.setItem('blinddrop_token', token);
      document.cookie = `blinddrop_token=${token}; path=/; max-age=28800; samesite=lax`;
      if (data.member) {
        window.localStorage.setItem('blinddrop_user', JSON.stringify(data.member));
      }
      router.replace('/');
    } catch (e) {
      setError('Could not reach backend API');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex text-neutral-900 bg-white">
      {/* Left decorative panel */}
      <div className="hidden lg:flex w-1/2 bg-neutral-900 flex-col items-start justify-center p-16 relative overflow-hidden">
        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1620121692029-d088224ddc74?q=80&w=1932&auto=format&fit=crop')] bg-cover bg-center opacity-20 filter grayscale"></div>
        <div className="relative z-10 space-y-6 max-w-xl">
          <div className="flex items-center gap-3">
            
            <h1 className="text-3xl font-bold tracking-tight text-white uppercase">BLIND DROP</h1>
          </div>
          <p className="text-neutral-400 text-lg leading-relaxed">
            Privacy-focused file transfer portal. Transfer files securely without requiring sign-ins, account creation, or leaving risky traces on public devices.
          </p>
        </div>
      </div>

      {/* Right login panel */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-neutral-50/50">
        <div className="w-full max-w-sm space-y-10">
          <div className="space-y-3">
            <h2 className="text-4xl font-bold tracking-tighter text-neutral-900">Sign in</h2>
            <p className="text-neutral-500 font-medium tracking-wide">Enter your credentials to continue</p>
          </div>
          
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-neutral-600 uppercase tracking-widest">Username</label>
              <input
                className="w-full px-4 py-3.5 bg-white border border-neutral-300 focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900 transition-colors outline-none text-neutral-900"
                placeholder="Enter username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-neutral-600 uppercase tracking-widest">Password</label>
              <input
                className="w-full px-4 py-3.5 bg-white border border-neutral-300 focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900 transition-colors outline-none text-neutral-900"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            {error && (
              <div className="p-4 border border-red-500 bg-red-50 text-red-700 text-sm font-medium">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-4 bg-neutral-900 text-white font-bold uppercase tracking-widest hover:bg-black disabled:opacity-50 transition-colors mt-4"
            >
              {loading ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>
          
          <div className="flex justify-between items-center text-xs font-semibold text-neutral-500 tracking-wider">
            <span>MODULE B</span>
            <span>SECURE ACCESS</span>
          </div>
        </div>
      </div>
    </div>
  );
}
