'use client';

import { useState } from 'react';
import { BarChart3, Sparkles } from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function BusinessAnalytics() {
  const { runWorkBuddyPrompt } = useDextra();
  const [timeRange, setTimeRange] = useState<'30d' | '90d' | 'ytd'>('30d');

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-600 mb-1">
            <BarChart3 className="w-4 h-4" />
            <span>Enterprise Business Intelligence & ROI</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-slate-900 tracking-tight">
            Workforce & Operations Analytics
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Holistic metrics comparing human operational throughput, autonomous agent efficiency,
            and capital ROI.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center p-1 bg-white rounded-lg border border-slate-200">
            {(['30d', '90d', 'ytd'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1 text-xs font-medium rounded-md uppercase transition-colors ${
                  timeRange === range
                    ? 'bg-slate-900 text-white font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {range}
              </button>
            ))}
          </div>

          <button
            onClick={() =>
              runWorkBuddyPrompt(
                'Generate an executive business intelligence report analyzing autonomous agent ROI and department efficiency.'
              )
            }
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs transition-colors"
          >
            <Sparkles className="w-4 h-4" />
            <span>AI Executive Brief</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase">
            Agent Hours Saved
          </span>
          <div className="mt-2 text-2xl font-bold font-mono text-indigo-600 tabular-nums">
            1,840 hrs
          </div>
          <span className="text-[11px] text-emerald-600 font-medium block mt-1">
            ~11.5 FTE equivalent capacity
          </span>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase">
            Estimated Cost Savings
          </span>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-900 tabular-nums">
            $142,600
          </div>
          <span className="text-[11px] text-emerald-600 font-medium block mt-1">
            +22.4% vs traditional manual BPO
          </span>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase">
            Approval Turnaround
          </span>
          <div className="mt-2 text-2xl font-bold font-mono text-emerald-600 tabular-nums">
            18 mins
          </div>
          <span className="text-[11px] text-slate-500 block mt-1">
            Median human decision latency
          </span>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase">
            Policy Compliance
          </span>
          <div className="mt-2 text-2xl font-bold font-mono text-indigo-600 tabular-nums">100%</div>
          <span className="text-[11px] text-emerald-600 font-medium block mt-1">
            Zero unauthorized disbursements
          </span>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Agent vs Human Task Throughput (7 cols) */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 shadow-2xs p-5">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Weekly Task Orchestration Pacing
              </h3>
              <p className="text-xs text-slate-500">
                Autonomous tasks resolved vs human reviews authorized.
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-indigo-600 font-medium">
                <span className="w-2.5 h-2.5 rounded-full bg-indigo-600" />
                AI Agent
              </span>
              <span className="flex items-center gap-1.5 text-slate-500 font-medium">
                <span className="w-2.5 h-2.5 rounded-full bg-slate-300" />
                Human Review
              </span>
            </div>
          </div>

          {/* Clean CSS Bar Chart */}
          <div className="mt-6 space-y-4">
            {[
              { day: 'Mon', agent: 84, human: 12 },
              { day: 'Tue', agent: 112, human: 18 },
              { day: 'Wed', agent: 96, human: 14 },
              { day: 'Thu', agent: 135, human: 22 },
              { day: 'Fri', agent: 124, human: 19 },
              { day: 'Sat', agent: 48, human: 4 },
              { day: 'Sun', agent: 32, human: 2 },
            ].map((d) => (
              <div key={d.day} className="flex items-center gap-3 text-xs">
                <span className="w-8 font-mono text-slate-400 font-medium">{d.day}</span>
                <div className="flex-1 flex items-center gap-1 h-5">
                  <div
                    className="bg-indigo-600 h-5 rounded-l flex items-center justify-end px-2 text-[10px] text-white font-mono font-bold"
                    style={{ width: `${(d.agent / 150) * 80}%` }}
                  >
                    {d.agent}
                  </div>
                  <div
                    className="bg-slate-300 h-5 rounded-r flex items-center px-2 text-[10px] text-slate-700 font-mono font-medium"
                    style={{ width: `${(d.human / 150) * 80}%` }}
                  >
                    {d.human}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Department Delegation Load (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 shadow-2xs p-5 flex flex-col justify-between">
          <div>
            <div className="pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900">Agent Workload by Domain</h3>
              <p className="text-xs text-slate-500">
                Distribution of machine compute across business functions.
              </p>
            </div>

            <div className="mt-5 space-y-3.5">
              {[
                { name: 'Corporate Finance (Ledger & Payroll)', share: 38, count: '3,890 ops' },
                { name: 'Supply Chain & Inventory', share: 28, count: '2,184 ops' },
                { name: 'People Ops & Attendance', share: 20, count: '1,420 ops' },
                { name: 'Operations & SLA Tracking', share: 14, count: '5,120 ops' },
              ].map((item) => (
                <div key={item.name} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-800">{item.name}</span>
                    <span className="font-mono text-slate-500">{item.share}%</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-indigo-600 h-2 rounded-full"
                      style={{ width: `${item.share}%` }}
                    />
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono">{item.count}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-500">
            Computed in real-time across all 4 autonomous micro-agents.
          </div>
        </div>
      </div>
    </div>
  );
}
