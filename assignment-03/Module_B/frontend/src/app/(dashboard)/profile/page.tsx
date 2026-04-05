'use client';

import { useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? (typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8080/api`
  : 'http://127.0.0.1:8080/api');

type SessionMember = {
  id: number;
  username: string;
  role: 'admin' | 'user';
  full_name: string;
  email: string;
  member_group: string;
};

function getCookieToken() {
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith('blinddrop_token='));
  return match ? match.split('=')[1] : '';
}

export default function ProfilePage() {
  const [member, setMember] = useState<SessionMember | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadProfile = async () => {
      const localToken = window.localStorage.getItem('blinddrop_token') || '';
      const token = localToken || getCookieToken();
      if (!token) {
        setError('Session not found. Please login again.');
        return;
      }

      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        setError(data.error || 'Could not load profile');
        return;
      }

      setMember(data.member || null);
    };

    loadProfile().catch(() => setError('Could not load profile'));
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-8 lg:p-16 bg-white min-h-full">
      <div className="max-w-4xl mx-auto space-y-16">
        
        {/* Header Block */}
        <div className="space-y-4">
          <div className="inline-flex px-3 py-1 bg-neutral-900 text-white text-xs font-bold tracking-widest uppercase mb-4">
            Identity & Access
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tighter text-neutral-900 uppercase">
            USER PROFILE
          </h1>
          <p className="text-xl text-neutral-500 max-w-2xl leading-relaxed mt-2 font-medium">
            View temporary access identity and metadata for your secure, trace-free session.
          </p>
        </div>

        {error && (
          <div className="border border-neutral-900 bg-neutral-100 p-4 text-sm font-bold uppercase tracking-widest text-neutral-900">
            {error}
          </div>
        )}

        {member && (
          <div className="border border-neutral-900 flex flex-col bg-white">
             <div className="p-6 md:p-8 border-b border-neutral-900">
               <h2 className="text-xl font-bold uppercase tracking-wide text-neutral-900">MEMBER DETAILS</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 text-sm p-6 md:p-8 gap-y-10 gap-x-12">
              <div>
                <p className="text-neutral-500 font-bold uppercase tracking-widest text-xs mb-1">Full Name</p>
                <p className="font-bold text-lg text-neutral-900 uppercase tracking-wide">{member.full_name}</p>
              </div>
              <div>
                <p className="text-neutral-500 font-bold uppercase tracking-widest text-xs mb-1">Username</p>
                <p className="font-bold text-lg text-neutral-900 uppercase tracking-wide">{member.username}</p>
              </div>
              <div>
                <p className="text-neutral-500 font-bold uppercase tracking-widest text-xs mb-1">Email</p>
                <p className="font-bold text-lg text-neutral-900 uppercase tracking-wide">{member.email}</p>
              </div>
              <div>
                <p className="text-neutral-500 font-bold uppercase tracking-widest text-xs mb-1">Role</p>
                <p className="font-bold text-lg text-neutral-900 uppercase tracking-wide">{member.role}</p>
              </div>
              <div>
                <p className="text-neutral-500 font-bold uppercase tracking-widest text-xs mb-1">Group</p>
                <p className="font-bold text-lg text-neutral-900 uppercase tracking-wide">{member.member_group || '-'}</p>
              </div>
              <div>
                <p className="text-neutral-500 font-bold uppercase tracking-widest text-xs mb-1">Member ID</p>
                <p className="font-bold text-lg text-neutral-900 uppercase tracking-wide">{member.id}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
