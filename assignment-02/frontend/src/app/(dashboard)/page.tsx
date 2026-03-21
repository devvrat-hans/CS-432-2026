'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';

export default function UserDashboard() {
  const [member, setMember] = useState<any>(null);

  useEffect(() => {
    const localToken = window.localStorage.getItem('blinddrop_token') || '';
    const token = localToken || document.cookie.split('; ').find(r => r.startsWith('blinddrop_token='))?.split('=')[1] || '';
    
    if (token) {
      fetch(`${process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8080/api'}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => res.json())
      .then(data => {
        if (data.member) setMember(data.member);
      })
      .catch(() => {});
    }
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-8 lg:p-16 bg-white min-h-full">
      <div className="max-w-6xl mx-auto space-y-16">
        
        {/* Header Block */}
        <div className="space-y-4">
          <div className="inline-flex px-3 py-1 bg-neutral-900 text-white text-xs font-bold tracking-widest uppercase mb-4">
            System Workspace
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tighter text-neutral-900 uppercase">
            BLIND DROP PORTAL
          </h1>
          <p className="text-xl text-neutral-500 max-w-2xl leading-relaxed mt-2 font-medium">
            Securely transfer files without leaving a trace on public devices. 
            {member ? ` Authenticated as ${member.username.toUpperCase()}` : ''}
          </p>
        </div>

      </div>
    </div>
  );
}
