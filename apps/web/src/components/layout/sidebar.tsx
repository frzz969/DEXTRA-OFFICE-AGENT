'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Bot,
  ListTodo,
  Users,
  Building2,
  DollarSign,
  Package,
  Activity,
  BarChart3,
  FileText,
  ShieldCheck,
  Lock,
  ScrollText,
  Puzzle,
  Settings,
  ChevronDown,
  Sparkles,
} from 'lucide-react';
import { viewPath, type ViewMode } from '@dextra/contracts';
import { useDextra } from '@/providers/dextra-provider';
import { AVATAR_URLS } from '@/data/mock-store';

interface NavSection {
  title: string;
  items: {
    id: ViewMode;
    label: string;
    icon: React.ElementType;
    badge?: number | string;
  }[];
}

export function Sidebar() {
  const pathname = usePathname();
  const { approvals, agents } = useDextra();

  const pendingApprovalsCount = approvals.filter((a) => a.status === 'pending').length;
  const activeAgentsCount = agents.filter(
    (a) => a.status === 'online' || a.status === 'busy'
  ).length;

  const navSections: NavSection[] = [
    {
      title: 'WORKSPACE',
      items: [
        { id: 'overview', label: 'Executive Overview', icon: LayoutDashboard },
        { id: 'ai-workspace', label: 'AI Workspace (WorkBuddy)', icon: Bot, badge: 'Orchestrator' },
        { id: 'tasks', label: 'Tasks & Workflows', icon: ListTodo },
        {
          id: 'agents',
          label: 'Agent Workforce',
          icon: Users,
          badge: `${activeAgentsCount} Online`,
        },
      ],
    },
    {
      title: 'BUSINESS OPERATIONS',
      items: [
        { id: 'hr', label: 'Human Resources', icon: Building2 },
        { id: 'finance', label: 'Corporate Finance', icon: DollarSign },
        { id: 'inventory', label: 'Inventory & Procurement', icon: Package },
        { id: 'operations', label: 'Operations & SLAs', icon: Activity },
      ],
    },
    {
      title: 'INTELLIGENCE',
      items: [
        { id: 'analytics', label: 'Business Analytics', icon: BarChart3 },
        { id: 'reports', label: 'Executive Reports', icon: FileText },
      ],
    },
    {
      title: 'GOVERNANCE',
      items: [
        {
          id: 'approvals',
          label: 'Approval Center',
          icon: ShieldCheck,
          badge: pendingApprovalsCount > 0 ? `${pendingApprovalsCount} Pending` : undefined,
        },
        { id: 'governance', label: 'Policies & Permissions', icon: Lock },
        { id: 'audit-logs', label: 'Audit Logs & Transparency', icon: ScrollText },
      ],
    },
    {
      title: 'SYSTEM',
      items: [
        { id: 'integrations', label: 'Integrations & ERP Sync', icon: Puzzle },
        { id: 'settings', label: 'Platform Settings', icon: Settings },
      ],
    },
  ];

  return (
    <aside className="sticky top-0 flex h-screen w-64 shrink-0 select-none flex-col justify-between border-r border-[#1E293B] bg-[#0B0F19] text-slate-300">
      {/* Top Organization Header */}
      <div className="flex flex-col">
        <div className="flex h-16 items-center justify-between border-b border-[#1E293B] px-5">
          <Link href={viewPath('overview')} className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold tracking-wider text-white shadow-sm">
              DX
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-semibold leading-tight tracking-tight text-white">
                DEXTRA
              </span>
              <span className="text-[10px] font-normal text-slate-400">Enterprise AI OS</span>
            </div>
          </Link>
          <button
            title="Active Organization: Apex Industrial Global"
            className="flex items-center gap-1 rounded border border-slate-700/60 bg-[#151D2E] px-2 py-1 text-[11px] text-slate-400 transition-colors hover:text-white"
          >
            <span className="max-w-[70px] truncate">Apex Global</span>
            <ChevronDown className="h-3 w-3 text-slate-400" />
          </button>
        </div>

        {/* Navigation Sections */}
        <div className="max-h-[calc(100vh-140px)] space-y-6 overflow-y-auto px-3 py-4">
          {navSections.map((section) => (
            <div key={section.title} className="space-y-1">
              <div className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                {section.title}
              </div>
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === viewPath(item.id);
                return (
                  <Link
                    key={item.id}
                    href={viewPath(item.id)}
                    aria-current={isActive ? 'page' : undefined}
                    className={`flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-indigo-600 font-semibold text-white shadow-sm'
                        : 'text-slate-400 hover:bg-[#151D2E] hover:text-slate-100'
                    }`}
                  >
                    <div className="flex min-w-0 items-center gap-2.5 truncate">
                      <Icon
                        className={`h-4 w-4 shrink-0 ${isActive ? 'text-white' : 'text-slate-400'}`}
                      />
                      <span className="truncate">{item.label}</span>
                    </div>

                    {item.badge && (
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                          isActive
                            ? 'bg-indigo-500 text-white'
                            : item.id === 'approvals' && pendingApprovalsCount > 0
                              ? 'border border-amber-500/30 bg-amber-500/20 text-amber-300'
                              : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Profile and Governance Status */}
      <div className="border-t border-[#1E293B] bg-[#0E1424] p-3">
        <div className="flex items-center gap-3 px-2 py-1.5">
          <img
            src={AVATAR_URLS.user}
            alt="Elena Rostova"
            referrerPolicy="no-referrer"
            className="h-8 w-8 shrink-0 rounded-full border border-slate-700 object-cover"
          />
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-xs font-medium text-slate-200">Elena Rostova</span>
            <span className="truncate text-[10px] text-slate-400">VP Platform & Operations</span>
          </div>
        </div>

        <div className="mt-2 flex items-center justify-between border-t border-slate-800/80 px-2 pt-2 text-[11px] text-slate-400">
          <div className="flex items-center gap-1.5">
            <Sparkles className="h-3 w-3 text-indigo-400" />
            <span>Governance Enforced</span>
          </div>
          <span className="font-mono text-[10px] text-emerald-400">100% Traceable</span>
        </div>
      </div>
    </aside>
  );
}
