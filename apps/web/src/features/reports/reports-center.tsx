'use client';

import { useState } from 'react';
import { FileText, Printer, Sparkles, CheckCircle2, Eye, X } from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

interface ReportDoc {
  id: string;
  title: string;
  category: string;
  generatedDate: string;
  authorAgent: string;
  status: 'Ready' | 'Archived';
  executiveSummary: string;
  metrics: { label: string; value: string }[];
}

export function ReportsCenter() {
  const { runWorkBuddyPrompt } = useDextra();
  const [selectedReport, setSelectedReport] = useState<ReportDoc | null>(null);

  const reports: ReportDoc[] = [
    {
      id: 'REP-2026-11-01',
      title: 'Executive Monthly Operations & AI Workforce Synthesis',
      category: 'Executive Briefing',
      generatedDate: '2026-11-07 05:20',
      authorAgent: 'WorkBuddy Central Orchestrator',
      status: 'Ready',
      executiveSummary:
        'DEXTRA orchestrated 4 specialized agents across 12,614 operations this cycle. 2 high-impact actions were held for human governance: November mid-cycle payroll ($412,850) and critical Edge Gateway replenishment ($14,200). Cross-department attendance averaged 96.6% with 1 flagged anomaly.',
      metrics: [
        { label: 'Total Operations Coordinated', value: '12,614' },
        { label: 'Autonomous Success Rate', value: '99.4%' },
        { label: 'Human Governance Approvals', value: '3 Active' },
        { label: 'Operating Efficiency Index', value: '94.2%' },
      ],
    },
    {
      id: 'REP-2026-10-31',
      title: 'Corporate Treasury & Q3 Ledger Reconciliation',
      category: 'Finance & Tax',
      generatedDate: '2026-10-31 18:00',
      authorAgent: 'Finance & Ledger Agent',
      status: 'Archived',
      executiveSummary:
        'All Q3 accounts payable and enterprise SaaS receivables reconciled against SAP S/4HANA. Net operating margin held at +24.8%. Statutory VAT and quarterly tax provisions computed with zero variance.',
      metrics: [
        { label: 'Total Cleared Volume', value: '$3.42M' },
        { label: 'Discrepancies Resolved', value: '0' },
        { label: 'Audit Log Hashes Verified', value: '1,420' },
      ],
    },
    {
      id: 'REP-2026-10-15',
      title: 'Warehouse Safety Stock & Supplier SLA Audit',
      category: 'Supply Chain',
      generatedDate: '2026-10-15 09:30',
      authorAgent: 'Inventory & Procurement Agent',
      status: 'Archived',
      executiveSummary:
        'Audit of Tier-1 component suppliers across Bay Area and European hubs. Recommended safety stock elevation on fiber transceivers and edge hardware.',
      metrics: [
        { label: 'SKUs Analyzed', value: '148' },
        { label: 'Stockout Risk Index', value: 'Low' },
        { label: 'Avg Supplier Lead Time', value: '4.8 Days' },
      ],
    },
  ];

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-600 mb-1">
            <FileText className="w-4 h-4" />
            <span>Executive Reporting & Documentation</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-slate-900 tracking-tight">
            Executive Reports & Audits
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Structured reports consolidated across multi-agent workflows ready for stakeholder
            distribution.
          </p>
        </div>

        <button
          onClick={() =>
            runWorkBuddyPrompt(
              'Draft an immediate comprehensive operations briefing covering HR attendance, payroll, and warehouse inventory.'
            )
          }
          className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs transition-colors self-start md:self-auto"
        >
          <Sparkles className="w-4 h-4" />
          <span>Generate New Report</span>
        </button>
      </div>

      {/* Reports Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {reports.map((doc) => (
          <div
            key={doc.id}
            className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-5 flex flex-col justify-between hover:border-slate-300 transition-colors"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                  {doc.category}
                </span>
                <span className="text-[11px] text-slate-400 font-mono">{doc.id}</span>
              </div>

              <h3 className="text-sm font-bold text-slate-900 leading-snug">{doc.title}</h3>

              <p className="text-xs text-slate-600 line-clamp-3 leading-relaxed">
                {doc.executiveSummary}
              </p>

              <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400">
                Author: <strong className="text-slate-700">{doc.authorAgent}</strong>
                <span className="block mt-0.5">{doc.generatedDate}</span>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
              <button
                onClick={() => setSelectedReport(doc)}
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Preview Document</span>
              </button>

              <button
                onClick={() => window.print()}
                className="p-1.5 text-slate-400 hover:text-slate-700 rounded"
                title="Print / Export PDF"
              >
                <Printer className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Report Preview Modal */}
      {selectedReport && (
        <div
          className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4"
          onClick={() => setSelectedReport(null)}
        >
          <div
            className="w-full max-w-2xl bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-5 border-b border-slate-200 flex items-start justify-between bg-slate-50">
              <div>
                <span className="text-[10px] font-mono font-bold text-indigo-600 uppercase">
                  {selectedReport.category} · {selectedReport.id}
                </span>
                <h3 className="text-base font-bold text-slate-900 mt-1">
                  {selectedReport.title}
                </h3>
                <span className="text-xs text-slate-500">
                  Consolidated by {selectedReport.authorAgent} on {selectedReport.generatedDate}
                </span>
              </div>
              <button
                onClick={() => setSelectedReport(null)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                  Executive Briefing & Synthesis
                </h4>
                <p className="text-xs leading-relaxed text-slate-800 bg-slate-50 p-4 rounded-lg border border-slate-200">
                  {selectedReport.executiveSummary}
                </p>
              </div>

              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                  Validated Key Performance Metrics
                </h4>
                <div className="grid grid-cols-2 gap-3">
                  {selectedReport.metrics.map((m, i) => (
                    <div key={i} className="p-3 bg-white rounded-lg border border-slate-200">
                      <span className="text-[11px] text-slate-500">{m.label}</span>
                      <div className="text-base font-bold font-mono text-slate-900 mt-1">
                        {m.value}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-4 bg-indigo-50/50 rounded-lg border border-indigo-200 text-xs text-indigo-950 space-y-1">
                <span className="font-bold flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-indigo-600" />
                  Regulatory & Compliance Stamp
                </span>
                <p className="text-[11px] text-indigo-900">
                  This document was automatically generated under DEXTRA Governance Kernel v3.8.
                  All sub-data points trace directly to cryptographic hashes in the Enterprise Audit
                  Trail.
                </p>
              </div>
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
              <button
                onClick={() => setSelectedReport(null)}
                className="px-3 py-1.5 text-xs text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
              >
                Close
              </button>
              <button
                onClick={() => window.print()}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print Official PDF</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
