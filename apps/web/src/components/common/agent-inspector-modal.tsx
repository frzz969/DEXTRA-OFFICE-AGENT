'use client';

import { Activity, CheckCircle2, Shield, Wrench, X } from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function AgentInspectorModal() {
  const { selectedAgent, setSelectedAgent, runWorkBuddyPrompt } = useDextra();

  if (!selectedAgent) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-xs"
      onClick={() => setSelectedAgent(null)}
    >
      <div
        className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-200 bg-slate-50/70 p-5">
          <div className="flex items-center gap-3">
            <img
              src={selectedAgent.avatarUrl}
              alt={selectedAgent.name}
              referrerPolicy="no-referrer"
              className="h-12 w-12 rounded-lg border border-slate-200 object-cover shadow-xs"
            />
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900">{selectedAgent.name}</h3>
                <span className="rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                  {selectedAgent.status.toUpperCase()}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                {selectedAgent.department} · {selectedAgent.role}
              </p>
            </div>
          </div>
          <button
            onClick={() => setSelectedAgent(null)}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-200/50 hover:text-slate-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content body */}
        <div className="space-y-6 overflow-y-auto p-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <span className="text-[11px] font-medium text-slate-500">Workload Load</span>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="font-mono text-lg font-bold text-slate-900">
                  {selectedAgent.workloadPercent}%
                </span>
                <span className="text-[10px] text-slate-400">capacity</span>
              </div>
              <div className="mt-1.5 h-1.5 w-full rounded-full bg-slate-100">
                <div
                  className="h-1.5 rounded-full bg-indigo-600"
                  style={{ width: `${selectedAgent.workloadPercent}%` }}
                />
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <span className="text-[11px] font-medium text-slate-500">Execution Success</span>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="font-mono text-lg font-bold text-emerald-600">
                  {selectedAgent.successRate}%
                </span>
                <span className="text-[10px] text-slate-400">verified</span>
              </div>
              <span className="mt-1 block font-mono text-[10px] text-slate-400">
                {selectedAgent.executionCount.toLocaleString()} total ops
              </span>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <span className="text-[11px] font-medium text-slate-500">Foundation Engine</span>
              <div className="mt-1 truncate text-xs font-semibold text-slate-800">
                {selectedAgent.config.modelTier}
              </div>
              <span className="mt-1 block text-[10px] text-slate-400">
                Confidence threshold: {selectedAgent.config.autoApprovalConfidence * 100}%
              </span>
            </div>
          </div>

          {/* Current Task & Recent Activity */}
          <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50/50 p-3.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-900">
              <Activity className="h-3.5 w-3.5 text-indigo-600" />
              <span>Current Assigned Operation</span>
            </div>
            <p className="pl-5 text-xs font-medium text-slate-700">{selectedAgent.currentTask}</p>
            <div className="pl-5 text-[11px] text-slate-500">
              Recent Trace: {selectedAgent.recentActivity}
            </div>
          </div>

          {/* Governance Permission Matrix (Read, Analyze, Recommend, Prepare, Execute) */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-700">
                <Shield className="h-4 w-4 text-indigo-600" />
                <span>Governance & Execution Boundaries</span>
              </h4>
              <span className="font-mono text-[11px] text-slate-400">RBAC Policy Enforced</span>
            </div>

            <div className="grid grid-cols-1 gap-2 text-xs md:grid-cols-2">
              <div className="rounded-lg border border-slate-200 p-3">
                <span className="mb-1 block text-[11px] font-bold uppercase text-slate-800">
                  1. Read & Ingestion
                </span>
                <div className="space-y-1">
                  {selectedAgent.permissions.read.map((p) => (
                    <div
                      key={p}
                      className="flex items-center gap-1.5 font-mono text-[11px] text-slate-600"
                    >
                      <CheckCircle2 className="h-3 w-3 shrink-0 text-emerald-500" />
                      <span>{p}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 p-3">
                <span className="mb-1 block text-[11px] font-bold uppercase text-slate-800">
                  2. Analysis & Diagnostics
                </span>
                <div className="space-y-1">
                  {selectedAgent.permissions.analyze.map((p) => (
                    <div
                      key={p}
                      className="flex items-center gap-1.5 font-mono text-[11px] text-slate-600"
                    >
                      <CheckCircle2 className="h-3 w-3 shrink-0 text-emerald-500" />
                      <span>{p}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 p-3">
                <span className="mb-1 block text-[11px] font-bold uppercase text-slate-800">
                  3. Recommend & Advisory
                </span>
                <div className="space-y-1">
                  {selectedAgent.permissions.recommend.map((p) => (
                    <div
                      key={p}
                      className="flex items-center gap-1.5 font-mono text-[11px] text-slate-600"
                    >
                      <CheckCircle2 className="h-3 w-3 shrink-0 text-indigo-500" />
                      <span>{p}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 p-3">
                <span className="mb-1 block text-[11px] font-bold uppercase text-slate-800">
                  4. Prepare (Draft Staging)
                </span>
                <div className="space-y-1">
                  {selectedAgent.permissions.prepare.map((p) => (
                    <div
                      key={p}
                      className="flex items-center gap-1.5 font-mono text-[11px] text-slate-600"
                    >
                      <CheckCircle2 className="h-3 w-3 shrink-0 text-amber-500" />
                      <span>{p}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-amber-200 bg-amber-50/40 p-3">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase text-amber-900">
                  5. Autonomous Execute Boundary
                </span>
                <span className="text-[10px] font-semibold text-amber-700">Strict Limits</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {selectedAgent.permissions.execute.map((p) => (
                  <span
                    key={p}
                    className="rounded border border-amber-200 bg-white px-2 py-0.5 font-mono text-[11px] text-amber-900"
                  >
                    {p}
                  </span>
                ))}
              </div>
              <p className="mt-2 text-[11px] leading-normal text-amber-800">
                Any transaction exceeding spend limit ($
                {selectedAgent.config.maxDailySpendLimit.toLocaleString()}) or statutory record
                edits automatically halts and defers to Human Approval Center.
              </p>
            </div>
          </div>

          {/* Connected Tools */}
          <div>
            <h4 className="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-700">
              <Wrench className="h-3.5 w-3.5 text-slate-500" />
              <span>Integrated Systems & Tooling</span>
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {selectedAgent.tools.map((t) => (
                <span
                  key={t}
                  className="rounded border border-slate-200 bg-slate-100 px-2.5 py-1 font-mono text-xs text-slate-700"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 p-4">
          <span className="text-xs text-slate-500">
            Agent ID: <span className="font-mono text-slate-700">{selectedAgent.id}</span>
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSelectedAgent(null)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              Close
            </button>
            <button
              onClick={() => {
                const agentName = selectedAgent.name;
                setSelectedAgent(null);
                void runWorkBuddyPrompt(
                  `Request ${agentName} to run an immediate diagnostics and audit summary.`
                );
              }}
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-indigo-700"
            >
              Dispatch Agent In WorkBuddy
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
