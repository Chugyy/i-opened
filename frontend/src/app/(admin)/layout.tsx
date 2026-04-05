'use client';

import { useState, useEffect, createContext, useContext } from 'react';
import { useRouter } from 'next/navigation';
import { AppSidebar } from '@/components/layout/sidebar';
import { Header } from '@/components/layout/header';
import { getToken } from '@/lib/auth';

export const SidebarContext = createContext({ collapsed: false, toggle: () => {} });
export const useSidebar = () => useContext(SidebarContext);

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [ready, setReady] = useState(false);
  const toggle = () => setCollapsed((c) => !c);

  useEffect(() => {
    if (!getToken()) {
      router.replace('/login');
    } else {
      setReady(true);
    }
  }, [router]);

  if (!ready) return null;

  return (
    <SidebarContext value={{ collapsed, toggle }}>
      <div className="flex h-screen overflow-hidden bg-background">
        <AppSidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header />
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto w-full max-w-5xl px-6 py-6">{children}</div>
          </main>
        </div>
      </div>
    </SidebarContext>
  );
}
