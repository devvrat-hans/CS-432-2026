'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { LayoutDashboard, Users, ShieldAlert, UserCircle2, ChevronUp, LogOut, ArrowLeft, Database, Menu, X, Activity, HardDrive } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? (typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8080/api`
  : 'http://127.0.0.1:8080/api');

type SessionMember = {
  username?: string;
  full_name?: string;
  role: 'admin' | 'user';
};

function getCookieToken() {
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith('blinddrop_token='));
  return match ? match.split('=')[1] : '';
}

export default function AdminSidebar() {
  const router = useRouter();
  const [isAdmin, setIsAdmin] = useState(true);
  const [member, setMember] = useState<SessionMember | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const loadRole = async () => {
      const localToken = window.localStorage.getItem('blinddrop_token') || '';
      const token = localToken || getCookieToken();
      if (!token) {
        setIsAdmin(false);
        setMember(null);
        return;
      }

      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }).catch(() => null);

      if (!res || !res.ok) {
        setIsAdmin(false);
        setMember(null);
        return;
      }

      const data = await res.json().catch(() => ({}));
      const member = (data.member || null) as SessionMember | null;
      setMember(member);
      setIsAdmin(member?.role === 'admin');
    };

    loadRole();
  }, []);

  const handleLogout = async () => {
    const localToken = window.localStorage.getItem('blinddrop_token') || '';
    const token = localToken || getCookieToken();

    if (token) {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => null);
    }

    window.localStorage.removeItem('blinddrop_token');
    document.cookie = 'blinddrop_token=; path=/; max-age=0; samesite=lax';
    setMenuOpen(false);
    router.replace('/login');
  };

  return (
    <aside className="w-full md:w-64 bg-neutral-900 border-b md:border-b-0 md:border-r border-neutral-800 flex flex-col text-neutral-300 relative md:min-h-[calc(100vh-4rem)]">
      <div className="md:hidden flex items-center justify-between px-4 py-3 border-b border-neutral-800">
        <span className="text-xs font-bold tracking-widest uppercase text-neutral-300">Admin Menu</span>
        <button
          onClick={() => setMobileOpen((prev) => !prev)}
          className="p-2 text-white hover:bg-neutral-800 transition-colors"
          aria-label="Toggle admin sidebar menu"
        >
          {mobileOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      <div className={`flex-1 px-4 py-6 space-y-2 ${mobileOpen ? 'block' : 'hidden'} md:block`}>
        <Link 
          href="/" 
          className="flex items-center gap-3 px-4 py-3 text-sm font-bold tracking-widest uppercase hover:bg-neutral-800 hover:text-white transition-colors"
          onClick={() => setMobileOpen(false)}
        >
          <ArrowLeft size={18} />
          Back to App
        </Link>
        <Link 
          href="/admin" 
          className="flex items-center gap-3 px-4 py-3 text-sm font-bold tracking-widest uppercase hover:bg-neutral-800 hover:text-white transition-colors"
          onClick={() => setMobileOpen(false)}
        >
          <LayoutDashboard size={18} />
          Overview
        </Link>
        <Link 
          href="/admin/databases" 
          className="flex items-center gap-3 px-4 py-3 text-sm font-bold tracking-widest uppercase hover:bg-neutral-800 hover:text-white transition-colors"
          onClick={() => setMobileOpen(false)}
        >
          <Database size={18} />
          Databases
        </Link>
        <Link 
          href="/admin/members" 
          className="flex items-center gap-3 px-4 py-3 text-sm font-bold tracking-widest uppercase hover:bg-neutral-800 hover:text-white transition-colors"
          onClick={() => setMobileOpen(false)}
        >
          <Users size={18} />
          Members
        </Link>
        <Link 
          href="/admin/audit-logs" 
          className="flex items-center gap-3 px-4 py-3 text-sm font-bold tracking-widest uppercase hover:bg-neutral-800 hover:text-white transition-colors"
          onClick={() => setMobileOpen(false)}
        >
          <ShieldAlert size={18} />
          Audit Logs
        </Link>
        <Link 
          href="/admin/api-latencies" 
          className="flex items-center gap-3 px-4 py-3 text-sm font-bold tracking-widest uppercase hover:bg-neutral-800 hover:text-white transition-colors"
          onClick={() => setMobileOpen(false)}
        >
          <Activity size={18} />
          API Latencies
        </Link>
        <Link 
          href="/admin/sharding" 
          className="flex items-center gap-3 px-4 py-3 text-sm font-bold tracking-widest uppercase hover:bg-neutral-800 hover:text-white transition-colors"
          onClick={() => setMobileOpen(false)}
        >
          <HardDrive size={18} />
          Sharding
        </Link>
      </div>

      <div className={`p-4 border-t border-neutral-800 relative bg-neutral-950 ${mobileOpen ? 'block' : 'hidden'} md:block`}>
        <button
          onClick={() => setMenuOpen((open) => !open)}
          className="w-full flex items-center justify-between gap-3 px-4 py-3 hover:bg-neutral-800 text-white transition-colors"
        >
          <span className="flex items-center gap-3 min-w-0">
            <UserCircle2 size={18} className="text-white" />
            <span className="truncate font-medium text-sm tracking-wide uppercase">{member?.full_name || member?.username || 'SYS_ADMIN'}</span>
          </span>
          <ChevronUp size={16} className={menuOpen ? 'rotate-180 transition-transform text-white' : 'transition-transform text-white'} />
        </button>

        {menuOpen && (
           <div className="mt-2 md:mt-0 md:absolute md:bottom-[calc(100%+8px)] left-4 right-4 bg-neutral-900 border border-neutral-700 p-2 space-y-1 shadow-xl z-10">
            <div className="text-[10px] font-bold px-3 py-2 uppercase tracking-widest text-neutral-500 mb-1">
              Actions
            </div>
            <Link 
              href="/profile" 
              onClick={() => setMenuOpen(false)} 
              className="block px-3 py-2 text-neutral-300 font-bold tracking-wider hover:bg-neutral-800 hover:text-white transition-colors uppercase text-xs"
            >
              View Profile
            </Link>
            <div className="border-t border-neutral-800 my-1"></div>
            <button
              onClick={handleLogout}
              className="w-full text-left px-3 py-2 text-red-500 font-bold tracking-wider hover:bg-neutral-800 transition-colors uppercase text-xs flex items-center gap-2"
            >
              <LogOut size={14} />
              Sign Out
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
