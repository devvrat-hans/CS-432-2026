import AdminSidebar from '../../components/AdminSidebar';
import Header from '../../components/Header';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();
  const token = cookieStore.get('blinddrop_token')?.value;

  if (!token) {
    redirect('/login');
  }

  // Check role via API
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8080/api';
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: 'no-store'
    });
    
    if (!res.ok) {
      redirect('/login');
    }
    
    const data = await res.json();
    if (data.member?.role !== 'admin') {
      redirect('/');
    }
  } catch (error) {
    redirect('/');
  }

  return (
    <>
      <Header />
      <div className="flex w-full flex-1 bg-white">
        <AdminSidebar />
        <div className="flex-1 flex flex-col w-full h-[calc(100vh-4rem)] overflow-y-auto">
          {children}
        </div>
      </div>
    </>
  );
}
