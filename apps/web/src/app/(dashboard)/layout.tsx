'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import type { AuthSessionDto } from '@/lib/api-types';
import { DextraProvider } from '@/providers/dextra-provider';
import { Sidebar } from '@/components/layout/sidebar';
import { TopNav } from '@/components/layout/top-nav';
import { CommandPalette } from '@/components/common/command-palette';
import { NotificationDrawer } from '@/components/common/notification-drawer';
import { AgentInspectorModal } from '@/components/common/agent-inspector-modal';
import { EmployeeModal } from '@/components/common/employee-modal';
import { JourneyGuideBar } from '@/components/common/journey-guide-bar';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get<AuthSessionDto>('/api/v1/auth/session')
      .then((s) => {
        if (cancelled) return;
        if (!s.authenticated || s.pending_mfa) {
          router.replace('/login');
        } else {
          setChecking(false);
        }
      })
      .catch(() => {
        if (!cancelled) router.replace('/login');
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (checking) return null;

  return (
    <DextraProvider>
      <div className="flex h-screen w-screen overflow-hidden bg-[#F8FAFC]">
        <Sidebar />
        <div className="flex h-full flex-1 flex-col overflow-hidden">
          <TopNav />
          <main className="flex-1 overflow-y-auto pb-24">{children}</main>
        </div>
        <CommandPalette />
        <NotificationDrawer />
        <AgentInspectorModal />
        <EmployeeModal />
        <JourneyGuideBar />
      </div>
    </DextraProvider>
  );
}
