'use client';

import { useEffect, useState } from 'react';
import {
  Search,
  LayoutDashboard,
  Bot,
  ListTodo,
  Users,
  Building2,
  DollarSign,
  Package,
  ShieldCheck,
  Lock,
  ScrollText,
  BarChart3,
  FileText,
  X,
  Sparkles,
} from 'lucide-react';
import type { ViewMode } from '@dextra/contracts';
import { useDextra } from '@/providers/dextra-provider';

export function CommandPalette() {
  const {
    isCommandPaletteOpen,
    setIsCommandPaletteOpen,
    setCurrentView,
    triggerJourney,
    approvals,
    handleApprove,
  } = useDextra();

  const [query, setQuery] = useState('');

  // Close on Escape (fixes the reference prototype bug).
  useEffect(() => {
    if (!isCommandPaletteOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsCommandPaletteOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isCommandPaletteOpen, setIsCommandPaletteOpen]);

  if (!isCommandPaletteOpen) return null;

  const navigationCommands: {
    id: ViewMode;
    label: string;
    icon: React.ElementType;
    section: string;
  }[] = [
    { id: 'overview', label: 'Go to Executive Overview', icon: LayoutDashboard, section: 'Navigation' },
    { id: 'ai-workspace', label: 'Go to AI Workspace (WorkBuddy)', icon: Bot, section: 'Navigation' },
    { id: 'approvals', label: 'Go to Human Approval Center', icon: ShieldCheck, section: 'Navigation' },
    { id: 'agents', label: 'Go to Agent Workforce Directory', icon: Users, section: 'Navigation' },
    { id: 'hr', label: 'Go to Human Resources (HRIS)', icon: Building2, section: 'Navigation' },
    { id: 'finance', label: 'Go to Corporate Finance & Payroll', icon: DollarSign, section: 'Navigation' },
    { id: 'inventory', label: 'Go to Inventory & Procurement', icon: Package, section: 'Navigation' },
    { id: 'tasks', label: 'Go to Tasks & Workflows', icon: ListTodo, section: 'Navigation' },
    { id: 'audit-logs', label: 'Go to Audit Logs & Traceability', icon: ScrollText, section: 'Navigation' },
    { id: 'governance', label: 'Go to Policies & Permissions', icon: Lock, section: 'Navigation' },
    { id: 'analytics', label: 'Go to Business Analytics', icon: BarChart3, section: 'Navigation' },
    { id: 'reports', label: 'Go to Executive Reports', icon: FileText, section: 'Navigation' },
  ];

  const journeyCommands = [
    {
      id: 1,
      label: 'Run Journey 1: Multi-Agent Attendance & Payroll Orchestration',
      description: 'WorkBuddy breaks request across HR & Finance agents',
    },
    {
      id: 2,
      label: 'Run Journey 2: Human Approval Governance Review',
      description: 'Review high-risk procurement PO and payroll authorization',
    },
    {
      id: 3,
      label: 'Run Journey 3: HR Attendance Anomaly Investigation',
      description: 'View Marcus Vance remote pattern deviation and leave status',
    },
    {
      id: 4,
      label: 'Run Journey 4: Inventory Low-Stock Detection & Procurement',
      description: 'Analyze Edge Gateway deficit and auto-reorder workflow',
    },
  ];

  const pendingApprovals = approvals.filter((a) => a.status === 'pending');

  const filteredNav = navigationCommands.filter((c) =>
    c.label.toLowerCase().includes(query.toLowerCase())
  );

  const filteredJourneys = journeyCommands.filter(
    (j) =>
      j.label.toLowerCase().includes(query.toLowerCase()) ||
      j.description.toLowerCase().includes(query.toLowerCase())
  );

  const filteredApprovals = pendingApprovals.filter((a) =>
    a.title.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/40 p-4 pt-20 backdrop-blur-xs"
      onClick={() => setIsCommandPaletteOpen(false)}
    >
      <div
        className="w-full max-w-xl overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 border-b border-slate-200 px-4 py-3.5">
          <Search className="h-4 w-4 shrink-0 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search commands, navigate modules, or run journeys..."
            className="w-full bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
            autoFocus
          />
          <button
            onClick={() => setIsCommandPaletteOpen(false)}
            className="rounded-md p-1 text-slate-400 hover:text-slate-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Command List */}
        <div className="max-h-96 space-y-4 overflow-y-auto p-2">
          {/* Quick Journeys */}
          <div>
            <div className="flex items-center gap-1.5 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              <Sparkles className="h-3 w-3 text-indigo-500" />
              Interactive DEXTRA Journeys
            </div>
            <div className="mt-1 space-y-0.5">
              {filteredJourneys.map((j) => (
                <button
                  key={j.id}
                  onClick={() => {
                    triggerJourney(j.id as 1 | 2 | 3 | 4);
                    setIsCommandPaletteOpen(false);
                  }}
                  className="group flex w-full flex-col rounded-lg px-3 py-2 text-left transition-colors hover:bg-slate-50"
                >
                  <span className="text-xs font-semibold text-slate-900 group-hover:text-indigo-600">
                    {j.label}
                  </span>
                  <span className="text-[11px] text-slate-500">{j.description}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Quick Pending Approvals */}
          {filteredApprovals.length > 0 && (
            <div>
              <div className="flex items-center justify-between px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-amber-600">
                <span>Pending Governance Approvals ({filteredApprovals.length})</span>
                <span className="text-[10px] font-normal text-slate-400">Instant 1-Click</span>
              </div>
              <div className="mt-1 space-y-0.5">
                {filteredApprovals.map((appr) => (
                  <div
                    key={appr.id}
                    className="flex items-center justify-between rounded-lg border border-transparent px-3 py-2 hover:border-amber-200 hover:bg-amber-50/50"
                  >
                    <div className="flex min-w-0 flex-col truncate pr-2">
                      <span className="truncate text-xs font-medium text-slate-900">
                        {appr.title}
                      </span>
                      <span className="text-[11px] text-slate-500">
                        {appr.requestingAgentName} · {appr.riskLevel.toUpperCase()} RISK
                      </span>
                    </div>
                    <button
                      onClick={() => {
                        handleApprove(appr.id);
                        setIsCommandPaletteOpen(false);
                      }}
                      className="shrink-0 rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-100"
                    >
                      Authorize
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Navigation */}
          <div>
            <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              Navigation
            </div>
            <div className="mt-1 space-y-0.5">
              {filteredNav.map((cmd) => {
                const Icon = cmd.icon;
                return (
                  <button
                    key={cmd.id}
                    onClick={() => {
                      setCurrentView(cmd.id);
                      setIsCommandPaletteOpen(false);
                    }}
                    className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-xs text-slate-700 transition-colors hover:bg-slate-50 hover:text-slate-900"
                  >
                    <Icon className="h-4 w-4 text-slate-400" />
                    <span>{cmd.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-4 py-2 text-[11px] text-slate-500">
          <span>Tip: Press ESC to close</span>
          <span className="font-mono text-[10px]">DEXTRA OS v3.8</span>
        </div>
      </div>
    </div>
  );
}
