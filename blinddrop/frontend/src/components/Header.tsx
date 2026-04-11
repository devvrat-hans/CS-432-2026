'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Header() {
  const pathname = usePathname();
  
  let pageTitle = 'System Workspace';
  if (pathname === '/login') pageTitle = 'System Entry';
  else if (pathname?.startsWith('/admin/databases')) pageTitle = 'Database Modules';
  else if (pathname?.startsWith('/admin/members')) pageTitle = 'Access Control';
  else if (pathname?.startsWith('/admin/audit-logs')) pageTitle = 'Audit Telemetry';
  else if (pathname?.startsWith('/admin/api-latencies')) pageTitle = 'API Latencies';
  else if (pathname?.startsWith('/admin')) pageTitle = 'Administrative Core';
  else if (pathname?.startsWith('/profile')) pageTitle = 'User Profile';

  return (
    <header className="bg-white border-b border-neutral-300 sticky top-0 z-50">
      <div className="w-full flex h-16 items-center">
        {/* Left Branding Area */}
        <div className="hidden md:flex items-center gap-3 w-64 flex-shrink-0 px-6 border-r border-neutral-800 h-full bg-neutral-900">
          <Link href="/">
            <span className="text-xl font-bold tracking-tight text-white uppercase mt-0.5">
              BLIND DROP
            </span>
          </Link>
        </div>
        
        {/* Page Title Area */}
        <div className="flex items-center gap-4 px-4 md:px-8">
          <Link href="/" className="md:hidden">
            <span className="text-sm font-bold tracking-widest text-neutral-900 uppercase">Blind Drop</span>
          </Link>
          <h1 className="text-sm font-bold text-neutral-900 uppercase tracking-widest mt-0.5">
            {pageTitle}
          </h1>
        </div>
      </div>
    </header>
  );
}
