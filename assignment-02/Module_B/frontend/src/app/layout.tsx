import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Blind Drop Management',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased text-neutral-900 bg-neutral-100 flex flex-col min-h-screen">
        <main className="flex-1 flex flex-col">{children}</main>
      </body>
    </html>
  );
}
