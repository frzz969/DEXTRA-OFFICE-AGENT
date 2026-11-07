'use client';

import {
  ArrowRight,
  Bot,
  CheckCircle2,
  DollarSign,
  Package,
  Play,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
} from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function ExecutiveOverview() {
  const {
    employees,
    agents,
    tasks,
    approvals,
    inventory,
    budgets,
    handleApprove,
    setCurrentView,
    triggerJourney,
    setSelectedAgent,
  } = useDextra();

  const pendingApprovals = approvals.filter((a) => a.status === 'pending');
  const completedTasks = tasks.filter((t) => t.status === 'completed').length;
  const criticalInventoryCount = inventory.filter(
    (i) => i.status === 'critical' || i.status === 'low_stock'
  ).length;

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6 lg:p-8">
      {/* 1. Welcome & Enterprise Context Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold text-indigo-600">
            <span>Enterprise Operations Center</span>
            <span>·</span>
            <span>Apex Industrial Global</span>
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 lg:text-3xl">
            Executive Operations Overview
          </h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Real-time status of multi-agent workforce orchestration, ERP pipelines, and human
            governance.
          </p>
        </div>

        {/* Action button cluster */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setCurrentView('ai-workspace')}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs transition-colors hover:bg-indigo-700"
          >
            <Bot className="h-4 w-4" />
            <span>Open WorkBuddy AI</span>
          </button>
          <button
            onClick={() => setCurrentView('approvals')}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs transition-colors hover:bg-slate-50"
          >
            <ShieldCheck className="h-4 w-4 text-amber-600" />
            <span>Review Approvals ({pendingApprovals.length})</span>
          </button>
        </div>
      </div>

      {/* 2. Key Business KPI Cards */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
        <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Workforce
            </span>
            <Users className="h-4 w-4 text-slate-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="font-mono text-2xl font-bold tabular-nums text-slate-900">
              {employees.length}
            </span>
            <span className="text-[11px] text-slate-400">FTEs</span>
          </div>
          <span className="mt-1 block text-[11px] font-medium text-emerald-600">
            96.6% attendance
          </span>
        </div>

        <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              AI Agents
            </span>
            <Bot className="h-4 w-4 text-indigo-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="font-mono text-2xl font-bold tabular-nums text-slate-900">
              {agents.length}
            </span>
            <span className="text-[11px] font-medium text-emerald-600">Online</span>
          </div>
          <span className="mt-1 block text-[11px] text-slate-500">99.7% execution rate</span>
        </div>

        <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Completed
            </span>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="font-mono text-2xl font-bold tabular-nums text-slate-900">
              {completedTasks + 38}
            </span>
            <span className="text-[11px] text-slate-400">tasks</span>
          </div>
          <span className="mt-1 block text-[11px] text-slate-500">87.5% sprint pacing</span>
        </div>

        <div className="rounded-xl border border-amber-200/90 bg-amber-50/20 p-4 shadow-2xs">
          <div className="flex items-center justify-between text-amber-700">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-800">
              Approvals
            </span>
            <ShieldAlert className="h-4 w-4 text-amber-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="font-mono text-2xl font-bold tabular-nums text-amber-900">
              {pendingApprovals.length}
            </span>
            <span className="text-[11px] font-medium text-amber-700">Pending</span>
          </div>
          <span className="mt-1 block font-mono text-[11px] text-amber-700">$427,050 gated</span>
        </div>

        <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Efficiency
            </span>
            <TrendingUp className="h-4 w-4 text-indigo-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="font-mono text-2xl font-bold tabular-nums text-slate-900">94.2%</span>
          </div>
          <span className="mt-1 block text-[11px] font-medium text-emerald-600">
            +3.8% vs last month
          </span>
        </div>

        <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Monthly Exp
            </span>
            <DollarSign className="h-4 w-4 text-slate-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="font-mono text-xl font-bold tabular-nums text-slate-900">$472k</span>
          </div>
          <span className="mt-1 block text-[11px] text-slate-500">Within 2.1% forecast</span>
        </div>

        <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Inventory
            </span>
            <Package className="h-4 w-4 text-slate-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span
              className={`font-mono text-2xl font-bold tabular-nums ${
                criticalInventoryCount > 0 ? 'text-rose-600' : 'text-slate-900'
              }`}
            >
              {criticalInventoryCount}
            </span>
            <span className="text-[11px] text-slate-400">critical</span>
          </div>
          <span className="mt-1 block text-[11px] font-medium text-rose-600">
            Edge Gateway deficit
          </span>
        </div>
      </div>

      {/* 3. Prominent WorkBuddy AI Executive Insight Card */}
      <div className="relative overflow-hidden rounded-xl border border-slate-200/90 bg-white p-5 shadow-xs lg:p-6">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
          <div className="max-w-3xl space-y-2">
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-indigo-600">
                <Sparkles className="h-4 w-4" />
                WorkBuddy AI Orchestrator Synthesis
              </span>
              <span className="text-slate-300">·</span>
              <span className="font-mono text-xs text-slate-500">Synced 5m ago</span>
            </div>
            <h3 className="text-lg font-bold text-slate-900">
              2 Autonomous Recommendations Require Executive Human Authorization
            </h3>
            <p className="text-xs leading-relaxed text-slate-600">
              HR Agent identified a remote attendance variance in Mobile Engineering (Marcus Vance
              post-op recovery), while Inventory Agent flagged a critical stock deficit on
              Enterprise Edge Gateway V3 (14 units vs 50 baseline). Finance Agent has computed
              payroll estimate ($412,850.00). All executions remain securely bounded under
              enterprise governance policies POL-01 and POL-02.
            </p>
          </div>

          <div className="flex shrink-0 flex-wrap gap-2 lg:flex-col">
            <button
              onClick={() => triggerJourney(1)}
              className="flex items-center justify-center gap-2 whitespace-nowrap rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-xs transition-colors hover:bg-indigo-700"
            >
              <Play className="h-3.5 w-3.5" />
              <span>Launch Multi-Agent Orchestration</span>
            </button>
            <button
              onClick={() => triggerJourney(2)}
              className="flex items-center justify-center gap-2 whitespace-nowrap rounded-lg bg-slate-100 px-4 py-2 text-xs font-semibold text-slate-700 transition-colors hover:bg-slate-200"
            >
              <ShieldAlert className="h-3.5 w-3.5 text-amber-600" />
              <span>Review Pending Approvals ({pendingApprovals.length})</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4. Two-Column Core Layout: Active Agent Workforce & Pending Approvals Queue */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Active AI Agent Workforce Panel (7 cols) */}
        <div className="flex flex-col justify-between rounded-xl border border-slate-200/90 bg-white p-5 shadow-2xs lg:col-span-7">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Active AI Workforce Dispatch</h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  Autonomous agents executing specialized domain operations under governance.
                </p>
              </div>
              <button
                onClick={() => setCurrentView('agents')}
                className="flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-700"
              >
                <span>View All Agents</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>

            <div className="mt-4 divide-y divide-slate-100">
              {agents.map((agent) => (
                <div
                  key={agent.id}
                  onClick={() => setSelectedAgent(agent)}
                  className="flex cursor-pointer items-center justify-between gap-4 rounded-lg px-2 py-3.5 transition-colors hover:bg-slate-50/80"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <img
                      src={agent.avatarUrl}
                      alt={agent.name}
                      referrerPolicy="no-referrer"
                      className="h-10 w-10 shrink-0 rounded-lg border border-slate-200 object-cover shadow-2xs"
                    />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-xs font-bold text-slate-900">
                          {agent.name}
                        </span>
                        <span className="text-[10px] font-medium text-slate-400">
                          {agent.department}
                        </span>
                      </div>
                      <p className="mt-0.5 truncate text-[11px] text-slate-600">
                        {agent.currentTask}
                      </p>
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-4">
                    <div className="hidden text-right sm:block">
                      <div className="font-mono text-xs font-bold text-slate-900">
                        {agent.workloadPercent}% Load
                      </div>
                      <div className="font-mono text-[10px] text-emerald-600">
                        {agent.successRate}% Success
                      </div>
                    </div>
                    <span className="text-xs font-medium text-indigo-600 hover:underline">
                      Inspect
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-[11px] text-slate-500">
            <span>Orchestrator: WorkBuddy v3.8</span>
            <span className="font-mono text-slate-600">Total Delegated Ops: 12,614</span>
          </div>
        </div>

        {/* Pending Approvals Queue (5 cols) */}
        <div className="flex flex-col justify-between rounded-xl border border-slate-200/90 bg-white p-5 shadow-2xs lg:col-span-5">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900">Pending Approval Queue</h3>
                  <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-800">
                    {pendingApprovals.length} Gated
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-slate-500">
                  Human-in-the-loop sign-offs required by enterprise policy.
                </p>
              </div>
              <button
                onClick={() => setCurrentView('approvals')}
                className="flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-700"
              >
                <span>Center</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>

            <div className="mt-4 space-y-3">
              {pendingApprovals.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500">
                  All requests cleared. Zero blocking actions.
                </div>
              ) : (
                pendingApprovals.map((req) => (
                  <div
                    key={req.id}
                    className="space-y-2 rounded-lg border border-slate-200 bg-slate-50/50 p-3.5 transition-colors hover:border-slate-300"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <span className="font-mono text-[10px] font-semibold text-slate-400">
                          {req.id} · {req.requestingAgentName}
                        </span>
                        <h4 className="truncate text-xs font-bold leading-snug text-slate-900">
                          {req.title}
                        </h4>
                      </div>
                      <span
                        className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-bold uppercase ${
                          req.riskLevel === 'critical'
                            ? 'bg-rose-100 text-rose-800'
                            : req.riskLevel === 'high'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {req.riskLevel}
                      </span>
                    </div>

                    <p className="line-clamp-2 text-[11px] text-slate-600">
                      {req.businessJustification}
                    </p>

                    <div className="flex items-center justify-between border-t border-slate-200/60 pt-2 text-xs">
                      {req.amount ? (
                        <span className="font-mono font-bold tabular-nums text-slate-900">
                          ${req.amount.toLocaleString()}.00 USD
                        </span>
                      ) : (
                        <span className="text-[11px] text-slate-500">Policy Exception</span>
                      )}

                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleApprove(req.id)}
                          className="rounded border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 transition-colors hover:bg-emerald-100"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => setCurrentView('approvals')}
                          className="rounded border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 transition-colors hover:text-slate-900"
                        >
                          Details
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-[11px] text-slate-500">
            <span>Strict Policy POL-01 Enforced</span>
            <span className="font-semibold text-amber-700">Zero Bypass Permitted</span>
          </div>
        </div>
      </div>

      {/* 5. Business Performance Trends & Department Spending */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Department Spending vs Budget (6 cols) */}
        <div className="rounded-xl border border-slate-200/90 bg-white p-5 shadow-2xs lg:col-span-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Department Capital & Budget Allocation
              </h3>
              <p className="text-xs text-slate-500">
                Live general ledger variance monitored by Finance Agent.
              </p>
            </div>
            <button
              onClick={() => setCurrentView('finance')}
              className="flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-700"
            >
              <span>Finance Ops</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="mt-4 space-y-3.5">
            {budgets.map((b) => {
              const percentUsed = Math.min(100, Math.round((b.spent / b.allocated) * 100));
              return (
                <div key={b.department} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-800">{b.department}</span>
                    <span className="font-mono tabular-nums text-slate-600">
                      ${(b.spent / 1000).toFixed(0)}k / ${(b.allocated / 1000).toFixed(0)}k (
                      {percentUsed}%)
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={`h-2 rounded-full ${
                        percentUsed > 85 ? 'bg-amber-500' : 'bg-indigo-600'
                      }`}
                      style={{ width: `${percentUsed}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Task Completion & SLA Compliance (6 cols) */}
        <div className="rounded-xl border border-slate-200/90 bg-white p-5 shadow-2xs lg:col-span-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Operations SLA & Task Velocity</h3>
              <p className="text-xs text-slate-500">
                Coordination speed between human team members and AI workers.
              </p>
            </div>
            <button
              onClick={() => setCurrentView('tasks')}
              className="flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-700"
            >
              <span>Workflows</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <span className="text-[11px] font-semibold uppercase text-slate-500">
                AI Agent Tasks
              </span>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="font-mono text-2xl font-bold tabular-nums text-indigo-600">
                  34
                </span>
                <span className="text-xs text-slate-500">in flight</span>
              </div>
              <span className="mt-2 block text-[11px] text-slate-500">
                Avg completion:{' '}
                <span className="font-mono font-medium text-slate-800">4.2 mins</span>
              </span>
            </div>

            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <span className="text-[11px] font-semibold uppercase text-slate-500">
                Human Escalations
              </span>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="font-mono text-2xl font-bold tabular-nums text-slate-900">6</span>
                <span className="text-xs text-slate-500">active</span>
              </div>
              <span className="mt-2 block text-[11px] text-slate-500">
                SLA Compliance:{' '}
                <span className="font-mono font-medium text-emerald-600">99.1%</span>
              </span>
            </div>
          </div>

          <div className="mt-4 flex items-center justify-between rounded-lg border border-slate-200 bg-white p-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span className="font-medium text-slate-800">
                Enterprise SLA: All Systems Nominal
              </span>
            </div>
            <span className="font-mono text-[11px] text-slate-400">0 breaches in 30d</span>
          </div>
        </div>
      </div>
    </div>
  );
}
