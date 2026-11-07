'use client';

import { Lock, Shield, Scale } from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function GovernancePolicies() {
  const { policies, togglePolicy } = useDextra();

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-600 mb-1">
            <Lock className="w-4 h-4" />
            <span>Enterprise Guardrails & Access Control</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-slate-900 tracking-tight">
            Policies & Agent Execution Boundaries
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Define what autonomous agents can read, analyze, recommend, prepare, and execute without
            human approval.
          </p>
        </div>

        <span className="text-xs text-indigo-700 bg-indigo-50 border border-indigo-200 px-3 py-1.5 rounded-lg font-mono flex items-center gap-2">
          <Shield className="w-3.5 h-3.5 text-indigo-600" />
          <span>Governance Level: Maximum Strict</span>
        </span>
      </div>

      {/* 5-Tier Boundary Explainer Banner */}
      <div className="p-5 bg-white rounded-xl border border-slate-200/90 shadow-2xs space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
          <Scale className="w-4 h-4 text-indigo-600" />
          <span>The DEXTRA 5-Tier Autonomous Agent Governance Hierarchy</span>
        </h3>
        <p className="text-xs text-slate-600 leading-relaxed">
          DEXTRA implements a mathematical execution ladder. Every agent operation falls into one of
          five strictly policed levels. Autonomous operations automatically drop into the Human
          Approval Center if they cross the configured expenditure, statutory, or safety threshold.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 pt-2">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[10px] font-bold text-slate-500 uppercase font-mono">
              Tier 1 · Read
            </span>
            <div className="text-xs font-bold text-slate-900 mt-1">Ingestion</div>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Read-only ERP queries & timesheet parsing.
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[10px] font-bold text-slate-500 uppercase font-mono">
              Tier 2 · Analyze
            </span>
            <div className="text-xs font-bold text-slate-900 mt-1">Diagnostics</div>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Anomaly detection & variance calculations.
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[10px] font-bold text-indigo-600 uppercase font-mono">
              Tier 3 · Recommend
            </span>
            <div className="text-xs font-bold text-slate-900 mt-1">Advisory</div>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Stock replenishment & shift suggestions.
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[10px] font-bold text-amber-600 uppercase font-mono">
              Tier 4 · Prepare
            </span>
            <div className="text-xs font-bold text-slate-900 mt-1">Staging Drafts</div>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Drafting POs, contracts, and payroll batches.
            </p>
          </div>

          <div className="p-3 bg-rose-50 rounded-lg border border-rose-200">
            <span className="text-[10px] font-bold text-rose-700 uppercase font-mono">
              Tier 5 · Execute
            </span>
            <div className="text-xs font-bold text-rose-950 mt-1">Commit to Ledger</div>
            <p className="text-[11px] text-rose-800 mt-0.5">
              Requires explicit human operator sign-off.
            </p>
          </div>
        </div>
      </div>

      {/* Policies Enforced List */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Active Enterprise Governance Guardrails
            </h3>
            <p className="text-xs text-slate-500">
              Enforced by kernel proxy prior to tool invocation.
            </p>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {policies.filter((p) => p.isEnforced).length} / {policies.length} Enforced
          </span>
        </div>

        <div className="divide-y divide-slate-100">
          {policies.map((pol) => (
            <div
              key={pol.id}
              className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50/50 transition-colors"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-slate-400">{pol.id}</span>
                  <span className="text-slate-300">·</span>
                  <h4 className="text-sm font-bold text-slate-900">{pol.name}</h4>
                  <span className="text-[10px] font-bold uppercase px-1.5 py-0.2 rounded bg-indigo-50 text-indigo-700 font-mono">
                    {pol.boundaryType} boundary
                  </span>
                </div>
                <p className="text-xs text-slate-600 font-medium">
                  {pol.humanApprovalThreshold}
                </p>
                <div className="text-[11px] text-slate-400">
                  Target Scope: <span className="font-mono text-slate-600">{pol.scope}</span> ·
                  Updated: {pol.lastUpdated}
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <button
                  onClick={() => togglePolicy(pol.id)}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                    pol.isEnforced
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100'
                      : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                  }`}
                >
                  {pol.isEnforced ? 'Enforced' : 'Disabled'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
