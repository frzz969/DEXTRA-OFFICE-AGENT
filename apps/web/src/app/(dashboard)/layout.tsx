import { DextraProvider } from '@/providers/dextra-provider';
import { Sidebar } from '@/components/layout/sidebar';
import { TopNav } from '@/components/layout/top-nav';
import { CommandPalette } from '@/components/common/command-palette';
import { NotificationDrawer } from '@/components/common/notification-drawer';
import { AgentInspectorModal } from '@/components/common/agent-inspector-modal';
import { EmployeeModal } from '@/components/common/employee-modal';
import { JourneyGuideBar } from '@/components/common/journey-guide-bar';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <DextraProvider>
      <div className="flex h-screen w-screen overflow-hidden bg-[#F8FAFC]">
        {/* Persistent Left Sidebar */}
        <Sidebar />

        {/* Main Dynamic Viewport */}
        <div className="flex h-full flex-1 flex-col overflow-hidden">
          <TopNav />
          <main className="flex-1 overflow-y-auto pb-24">{children}</main>
        </div>

        {/* Modals & Overlays */}
        <CommandPalette />
        <NotificationDrawer />
        <AgentInspectorModal />
        <EmployeeModal />
        <JourneyGuideBar />
      </div>
    </DextraProvider>
  );
}
