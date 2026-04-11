import type { Metadata } from 'next';
import './globals.css';
import Navbar from '@/components/Navbar';

export const metadata: Metadata = {
  title: 'Blind Drop — Secure File Transfer',
  description: 'Privacy-focused file transfer portal. No login. No trace. Auto-deleted after download.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased text-neutral-900 bg-neutral-100 flex flex-col min-h-screen" suppressHydrationWarning>
        <Navbar />
        <main className="flex-1 flex flex-col">{children}</main>
      </body>
    </html>
  );
}
