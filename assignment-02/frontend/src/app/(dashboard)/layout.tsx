import Sidebar from '../../components/Sidebar';
import Header from '../../components/Header';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();
  const token = cookieStore.get('blinddrop_token')?.value;

  if (!token) {
    redirect('/login');
  }

  return (
    <>
      <Header />
      <div className="flex w-full flex-1">
        <Sidebar />
        <div className="flex-1 flex flex-col w-full h-[calc(100vh-4rem)] overflow-y-auto">
          {children}
        </div>
      </div>
    </>
  );
}
