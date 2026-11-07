'use client';

import { Activity, ExternalLink, Users } from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function AgentWorkforce() {
  const { agents, setSelectedAgent } = useDextra();

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold text-indigo-600">
            <Users className="h-4 w-4" />
            <span>Autonomous Intelligence Fleet</span>
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 lg:text-3xl">
            Specialized AI Agent Workforce
          </h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Manage domain-specific AI agents, configure governance boundaries, and monitor
            autonomous task loads.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 font-mono text-xs text-emerald-700">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span>4 / 4 Autonomous Agents Online</span>
          </span>
        </div>
      </div>

      {/* Agents Grid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="flex flex-col justify-between overflow-hidden rounded-xl border border-slate-200/90 bg-white shadow-2xs transition-colors hover:border-slate-300"
          >
            {/* Top Card Info */}
            <div className="space-y-4 p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <img
                    src={agent.avatarUrl}
                    alt={agent.name}
                    referrerPolicy="no-referrer"
                    className="h-14 w-14 rounded-xl border border-slate-200 object-cover shadow-2xs"
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-slate-900">{agent.name}</h3>
                      <span className="rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                        {agent.status.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-xs font-medium text-slate-500">
                      {agent.department} · {agent.role}
                    </p>
                    <span className="mt-0.5 block font-mono text-[11px] text-indigo-600">
                      Tier: {agent.config.modelTier}
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => setSelectedAgent(agent)}
                  className="rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-600 transition-colors hover:bg-indigo-100"
                >
                  Inspect RBAC
                </button>
              </div>

              {/* Workload and Success Gauges */}
              <div className="grid grid-cols-3 gap-2.5 border-t border-slate-100 pt-2">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                  <span className="text-[10px] font-semibold uppercase text-slate-400">Load</span>
                  <div className="mt-0.5 font-mono text-base font-bold text-slate-900">
                    {agent.workloadPercent}%
                  </div>
                  <div className="mt-1 h-1 w-full rounded-full bg-slate-200">
                    <div
                      className="h-1 rounded-full bg-indigo-600"
                      style={{ width: `${agent.workloadPercent}%` }}
                    />
                  </div>
                </div>

                <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                  <span className="text-[10px] font-semibold uppercase text-slate-400">
                    Success
                  </span>
                  <div className="mt-0.5 font-mono text-base font-bold text-emerald-600">
                    {agent.successRate}%
                  </div>
                  <span className="mt-0.5 block text-[10px] text-slate-400">
                    {agent.executionCount} runs
                  </span>
                </div>

                <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                  <span className="text-[10px] font-semibold uppercase text-slate-400">
                    Spend Cap
                  </span>
                  <div className="mt-0.5 font-mono text-base font-bold text-slate-900">
                    $
                    {agent.config.maxDailySpendLimit
                      ? `${(agent.config.maxDailySpendLimit / 1000).toFixed(0)}k`
                      : '0'}
                  </div>
                  <span className="mt-0.5 block text-[10px] text-slate-400">Daily limit</span>
                </div>
              </div>

              {/* Current Task */}
              <div className="space-y-1 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
                <div className="flex items-center gap-1.5 font-semibold text-slate-700">
                  <Activity className="h-3.5 w-3.5 text-indigo-600" />
                  <span>Current Autonomous Task</span>
                </div>
                <p className="pl-5 text-[11px] font-medium leading-relaxed text-slate-800">
                  {agent.currentTask}
                </p>
              </div>

              {/* Permissions Pills (Read, Analyze, Prepare, Execute) */}
              <div className="space-y-1.5">
                <span className="block text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Enforced Boundaries
                </span>
                <div className="flex flex-wrap gap-1 text-[11px]">
                  <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-slate-700">
                    Read ({agent.permissions.read.length})
                  </span>
                  <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-slate-700">
                    Analyze ({agent.permissions.analyze.length})
                  </span>
                  <span className="rounded bg-indigo-50 px-2 py-0.5 font-mono text-indigo-700">
                    Recommend ({agent.permissions.recommend.length})
                  </span>
                  <span className="rounded bg-amber-50 px-2 py-0.5 font-mono text-amber-700">
                    Prepare ({agent.permissions.prepare.length})
                  </span>
                  <span className="rounded bg-rose-50 px-2 py-0.5 font-mono text-rose-700">
                    Execute (Gated: {agent.permissions.execute.length})
                  </span>
                </div>
              </div>
            </div>

            {/* Bottom Card Footer */}
            <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50 p-4">
              <span className="font-mono text-[11px] text-slate-500">
                Tools: {agent.tools.slice(0, 2).join(', ')} +{agent.tools.length - 2} more
              </span>
              <button
                onClick={() => setSelectedAgent(agent)}
                className="flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-700"
              >
                <span>View Full Spec</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
