'use client';

import { usePathname } from 'next/navigation';
import { Bell, ChevronRight, Command, Play, Search, ShieldAlert } from 'lucide-react';
import type { ViewMode } from '@dextra/contracts';
import { useDextra } from '@/providers/dextra-provider';
import { AVATAR_URLS } from '@/data/mock-store';

const BREADCRUMBS: Record<ViewMode, string> = {
  overview: 'Executive Overview',
  'ai-workspace': 'AI Workspace · WorkBuddy Orchestrator',
  tasks: 'Operations · Tasks & Workflows',
  agents: 'AI Workforce · Specialized Agents',
  hr: 'Business Operations · Human Resources',
  finance: 'Business Operations · Corporate Finance',
  inventory: 'Business Operations · Inventory & Procurement',
  operations: 'Business Operations · Operations & SLAs',
  analytics: 'Intelligence · Business Analytics',
  reports: 'Intelligence · Executive Reports',
  approvals: 'Governance · Human Approval Center',
  governance: 'Governance · Policies & Boundaries',
  'audit-logs': 'Governance · Audit Logs & Traceability',
  integrations: 'System · Integrations & Sync',
  settings: 'System · Platform Settings',
};

export function TopNav() {
  const pathname = usePathname();
  const {
    currentView,
    setCurrentView,
    setIsCommandPaletteOpen,
    isNotificationOpen,
    setIsNotificationOpen,
    notifications,
    approvals,
    triggerJourney,
    currentJourney,
  } = useDextra();

  const unreadCount = notifications.filter((n) => !n.isRead).length;
  const pendingApprovalsCount = approvals.filter((a) => a.status === 'pending').length;

  // Derive the breadcrumb from the actual route; fall back to context state.
  const breadcrumb =
    (Object.keys(BREADCRUMBS) as ViewMode[]).find(
      (view) => pathname === `/${view}`
    ) ?? currentView;

  const getBreadcrumbTitle = () => BREADCRUMBS[breadcrumb] ?? 'Dashboard';

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between gap-6 border-b border-slate-200/90 bg-white px-6">
      {/* Zone 1: Breadcrumb & Context */}
      <div className="flex shrink-0 items-center gap-2 whitespace-nowrap text-xs font-medium text-slate-500">
        <span className="font-semibold tracking-tight text-slate-900">DEXTRA</span>
        <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
        <span className="font-semibold text-slate-800">{getBreadcrumbTitle()}</span>
      </div>

      {/* Zone 2: Guided Journeys Switcher (Quick interactive access) */}
      <div className="hidden items-center gap-1.5 rounded-lg border border-slate-200/60 bg-slate-100/90 p-1 lg:flex">
        <span className="flex items-center gap-1 px-2 text-[11px] font-semibold text-slate-500">
          <Play className="h-3 w-3 text-indigo-600" />
          Test Journey:
        </span>
        <button
          onClick={() => triggerJourney(1)}
          className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors ${
            currentJourney === 1
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-700 hover:bg-white hover:text-slate-900'
          }`}
          title="Journey 1: Multi-Agent Orchestration (WorkBuddy delegates to HR & Finance)"
        >
          1. Multi-Agent AI
        </button>
        <button
          onClick={() => triggerJourney(2)}
          className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors ${
            currentJourney === 2
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-700 hover:bg-white hover:text-slate-900'
          }`}
          title="Journey 2: Human Approval (Approve / Reject high-risk procurement & payroll)"
        >
          2. Human Approval ({pendingApprovalsCount})
        </button>
        <button
          onClick={() => triggerJourney(3)}
          className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors ${
            currentJourney === 3
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-700 hover:bg-white hover:text-slate-900'
          }`}
          title="Journey 3: HR Attendance & Leave Workflow"
        >
          3. HR Workflow
        </button>
        <button
          onClick={() => triggerJourney(4)}
          className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors ${
            currentJourney === 4
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-700 hover:bg-white hover:text-slate-900'
          }`}
          title="Journey 4: Inventory Low Stock Detection & Reorder"
        >
          4. Inventory Alert
        </button>
      </div>

      {/* Zone 3: Global Search, Command Palette, Notification Bell, User */}
      <div className="flex shrink-0 items-center gap-3">
        {/* Command Palette Trigger */}
        <button
          onClick={() => setIsCommandPaletteOpen(true)}
          className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-500 transition-colors hover:bg-slate-100"
        >
          <Search className="h-3.5 w-3.5 text-slate-400" />
          <span className="hidden sm:inline">Search & Actions...</span>
          <kbd className="hidden items-center gap-0.5 rounded border border-slate-200 bg-white px-1.5 py-0.5 font-mono text-[10px] text-slate-500 shadow-2xs sm:inline-flex">
            <Command className="h-2.5 w-2.5" /> K
          </kbd>
        </button>

        {/* Approvals Quick Access if pending */}
        {pendingApprovalsCount > 0 && (
          <button
            onClick={() => setCurrentView('approvals')}
            className="flex items-center gap-1.5 rounded-lg border border-amber-200/90 bg-amber-50 px-2.5 py-1.5 text-xs font-semibold text-amber-900 transition-colors hover:bg-amber-100"
          >
            <ShieldAlert className="h-3.5 w-3.5 text-amber-600" />
            <span className="tabular-nums">{pendingApprovalsCount}</span>
            <span className="hidden md:inline">Pending</span>
          </button>
        )}

        {/* Notification Bell */}
        <button
          onClick={() => setIsNotificationOpen(!isNotificationOpen)}
          className="relative rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-indigo-600" />
          )}
        </button>

        {/* User Avatar */}
        <div className="flex items-center gap-2 border-l border-slate-200 pl-2">
          <img
            src={AVATAR_URLS.user}
            alt="Elena Rostova"
            referrerPolicy="no-referrer"
            className="h-8 w-8 rounded-full border border-slate-200 object-cover"
          />
        </div>
      </div>
    </header>
  );
}
