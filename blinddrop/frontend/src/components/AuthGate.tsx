'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';

type Props = {
  children: React.ReactNode;
};

function getCookieToken() {
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith('blinddrop_token='));
  return match ? match.split('=')[1] : '';
}

const PUBLIC_ROUTES = ['/', '/upload', '/download', '/login'];

export default function AuthGate({ children }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const isPublic = PUBLIC_ROUTES.some(
      (r) => pathname === r || pathname.startsWith('/download/')
    );

    const safetyTimer = window.setTimeout(() => {
      setReady(true);
    }, 2000);

    // Skip auth check entirely for public routes.
    if (isPublic) {
      setReady(true);
      window.clearTimeout(safetyTimer);
      return;
    }

    const localToken = window.localStorage.getItem('blinddrop_token') || '';
    const cookieToken = getCookieToken();
    const token = localToken || cookieToken;

    if (!token && pathname !== '/login') {
      setReady(true);
      router.replace('/login');
      window.clearTimeout(safetyTimer);
      return;
    }

    // Prevent loops: only treat cookie-backed session as authenticated for login-page redirect.
    if (cookieToken && pathname === '/login') {
      setReady(true);
      router.replace('/');
      window.clearTimeout(safetyTimer);
      return;
    }

    setReady(true);
    window.clearTimeout(safetyTimer);

    return () => {
      window.clearTimeout(safetyTimer);
    };
  }, [pathname, router]);

  if (!ready) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center min-h-screen bg-neutral-100">
        <svg className="animate-spin h-8 w-8 text-indigo-600 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <div className="text-sm font-medium text-neutral-500">Checking session...</div>
      </div>
    );
  }

  return <>{children}</>;
}
