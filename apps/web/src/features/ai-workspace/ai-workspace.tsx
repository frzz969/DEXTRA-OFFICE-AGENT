'use client';

import { useState } from 'react';
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  FileText,
  Layers,
  Loader2,
  Printer,
  Send,
  ShieldAlert,
  Terminal,
} from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function AIWorkspace() {
  const { activeSession, isOrchestrating, runWorkBuddyPrompt, handleApprove, setCurrentView } =
    useDextra();

  const [promptInput, setPromptInput] = useState('');

  const samplePrompts = [
    {
      title: 'Monthly Attendance, Payroll & Anomaly Audit',
      prompt:
        'Prepare a monthly employee attendance report, calculate payroll estimates, and identify departments with unusual attendance patterns.',
      tag: 'HR + Finance',
    },
    {
      title: 'Supply Chain Depletion & Reorder Dispatch',
      prompt:
        'Audit warehouse component inventory, evaluate reorder thresholds, and prepare a procurement purchase order for low-stock edge nodes.',
      tag: 'Inventory + SCM',
    },
    {
      title: 'Quarterly Operating Expenditure Variance Check',
      prompt:
        'Reconcile Q4 operating expenses against department allocations and flag transactions exceeding the $5,000 policy threshold.',
      tag: 'Finance + Governance',
    },
    {
      title: 'Engineering Capacity & Attendance Rebalancing',
      prompt:
        'Assess engineering sprint velocity and recommend shift rebalancing for engineers with approved sick leave.',
      tag: 'HR + Operations',
    },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!promptInput.trim() || isOrchestrating) return;
    void runWorkBuddyPrompt(promptInput);
    setPromptInput('');
  };

  const handleSelectPreset = (p: string) => {
    void runWorkBuddyPrompt(p);
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold text-indigo-600">
            <Bot className="h-4 w-4" />
            <span>Multi-Agent Orchestration Engine</span>
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 lg:text-3xl">
            WorkBuddy Orchestrator
          </h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Instruct the central orchestrator to decompose enterprise operations across
            specialized agents with strict human governance.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-500 shadow-2xs">
            <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
            <span className="font-mono text-slate-700">4 Agents Ready</span>
          </span>
        </div>
      </div>

      {/* Preset Prompts Row */}
      <div className="space-y-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Enterprise Instruction Templates
        </span>
        <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2 lg:grid-cols-4">
          {samplePrompts.map((item, idx) => (
            <button
              key={idx}
              onClick={() => handleSelectPreset(item.prompt)}
              disabled={isOrchestrating}
              className="group flex flex-col justify-between rounded-xl border border-slate-200/90 bg-white p-3 text-left shadow-2xs transition-all hover:border-indigo-300 hover:bg-indigo-50/40"
            >
              <div>
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600 transition-colors group-hover:bg-indigo-100 group-hover:text-indigo-800">
                    {item.tag}
                  </span>
                  <ArrowRight className="h-3.5 w-3.5 text-slate-400 transition-all group-hover:translate-x-0.5 group-hover:text-indigo-600" />
                </div>
                <h4 className="text-xs font-bold text-slate-900 group-hover:text-indigo-950">
                  {item.title}
                </h4>
              </div>
              <p className="mt-2 line-clamp-2 text-[11px] leading-relaxed text-slate-500">
                &quot;{item.prompt}&quot;
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Main Orchestration & Conversation Area */}
      <div className="flex flex-col overflow-hidden rounded-xl border border-slate-200/90 bg-white shadow-2xs">
        {/* Active Prompt Banner */}
        <div className="flex items-center justify-between gap-4 bg-slate-900 p-4 text-white lg:p-5">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-600">
              <Bot className="h-5 w-5 text-white" />
            </div>
            <div className="min-w-0">
              <span className="block text-[10px] font-bold uppercase tracking-wider text-indigo-400">
                Active Orchestration Session
              </span>
              <p className="truncate text-xs font-medium text-slate-100 lg:text-sm">
                {activeSession?.prompt ||
                  'Enter an instruction below to trigger autonomous coordination...'}
              </p>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {isOrchestrating ? (
              <span className="flex items-center gap-1.5 rounded-full border border-indigo-400/30 bg-indigo-500/30 px-3 py-1 text-xs font-medium text-indigo-300">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Orchestrating Agents...</span>
              </span>
            ) : activeSession?.status === 'awaiting_approval' ? (
              <span className="flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/20 px-3 py-1 text-xs font-medium text-amber-300">
                <ShieldAlert className="h-3.5 w-3.5" />
                <span>Governance Gate Active</span>
              </span>
            ) : (
              <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/20 px-3 py-1 text-xs font-medium text-emerald-300">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Execution Bounded & Complete</span>
              </span>
            )}
          </div>
        </div>

        {/* Live Multi-Agent Delegation Pipeline Board */}
        <div className="border-b border-slate-200 bg-slate-50/70 p-5 lg:p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-700">
              <Layers className="h-4 w-4 text-indigo-600" />
              <span>Multi-Agent Task Decomposition & Delegation Pipeline</span>
            </h3>
            <span className="font-mono text-[11px] text-slate-400">
              Trace ID: {activeSession?.id || 'DX-SESSION-READY'}
            </span>
          </div>

          {/* Steps Timeline Grid */}
          <div className="space-y-3">
            {activeSession?.steps.map((step, idx) => {
              const isRunning = step.status === 'running';
              const isRequiresReview = step.status === 'requires_human_review';
              const isCompleted = step.status === 'completed';

              return (
                <div
                  key={step.id}
                  className={`rounded-xl border p-4 transition-all ${
                    isRunning
                      ? 'border-indigo-300 bg-indigo-50/80 shadow-xs'
                      : isRequiresReview
                        ? 'border-amber-300 bg-amber-50/70 shadow-xs'
                        : 'border-slate-200/90 bg-white'
                  }`}
                >
                  <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
                    <div className="flex items-center gap-3">
                      <div
                        className={`flex h-7 w-7 items-center justify-center rounded-lg font-mono text-xs font-bold ${
                          isRunning
                            ? 'bg-indigo-600 text-white'
                            : isRequiresReview
                              ? 'bg-amber-600 text-white'
                              : 'bg-emerald-600 text-white'
                        }`}
                      >
                        {idx + 1}
                      </div>

                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-xs font-bold text-slate-900">{step.title}</h4>
                          <span className="font-mono text-[10px] text-slate-500">
                            [{step.agentName}]
                          </span>
                        </div>
                        <p className="mt-0.5 text-[11px] text-slate-600">{step.description}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-start pl-10 sm:self-center sm:pl-0">
                      {isRunning && (
                        <span className="flex items-center gap-1 text-[11px] font-semibold text-indigo-700">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          <span>Processing...</span>
                        </span>
                      )}
                      {isCompleted && (
                        <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-700">
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                          <span>Completed</span>
                        </span>
                      )}
                      {isRequiresReview && (
                        <span className="flex items-center gap-1 rounded bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-800">
                          <ShieldAlert className="h-3.5 w-3.5 text-amber-600" />
                          <span>Approval Required</span>
                        </span>
                      )}
                      <span className="font-mono text-[10px] text-slate-400">
                        {step.timestamp}
                      </span>
                    </div>
                  </div>

                  {step.outputSummary && (
                    <div className="mt-3 flex items-start gap-2 border-t border-slate-200/60 pl-10 pt-2.5">
                      <Terminal className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
                      <div className="w-full rounded border border-slate-200 bg-slate-50 px-2.5 py-1 font-mono text-xs text-slate-800">
                        {step.outputSummary}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Consolidated Structured Report Result Card */}
        {activeSession?.consolidatedReport && (
          <div className="space-y-6 p-6">
            <div className="flex flex-col justify-between gap-4 border-b border-slate-200 pb-4 md:flex-row md:items-center">
              <div>
                <div className="mb-1 flex items-center gap-2 text-xs font-semibold text-emerald-600">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Consolidated Multi-Agent Output</span>
                </div>
                <h3 className="text-lg font-bold text-slate-900">
                  {activeSession.consolidatedReport.title}
                </h3>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-2xs hover:bg-slate-50"
                >
                  <Printer className="h-3.5 w-3.5 text-slate-500" />
                  <span>Print Report</span>
                </button>
                <button
                  onClick={() => setCurrentView('reports')}
                  className="flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-600 hover:bg-indigo-100"
                >
                  <FileText className="h-3.5 w-3.5" />
                  <span>View in Reports Center</span>
                </button>
              </div>
            </div>

            {/* Executive Summary Paragraph */}
            <p className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs leading-relaxed text-slate-700 lg:text-sm">
              {activeSession.consolidatedReport.summary}
            </p>

            {/* Metrics Breakdown Grid */}
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {activeSession.consolidatedReport.metrics.map((m, i) => (
                <div key={i} className="rounded-lg border border-slate-200 bg-white p-3.5">
                  <span className="block text-[11px] font-medium text-slate-500">{m.label}</span>
                  <div className="mt-1 font-mono text-base font-bold tabular-nums text-slate-900 lg:text-lg">
                    {m.value}
                  </div>
                  {m.change && (
                    <span className="mt-0.5 block text-[10px] font-medium text-indigo-600">
                      {m.change}
                    </span>
                  )}
                </div>
              ))}
            </div>

            {/* Strategic Recommendations */}
            <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Coordinated Agent Recommendations
              </h4>
              <ul className="space-y-1.5">
                {activeSession.consolidatedReport.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs text-slate-700">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-600" />
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Human-In-The-Loop Approval Card if gated */}
            {activeSession.consolidatedReport.approvalRequestId && (
              <div className="flex flex-col justify-between gap-4 rounded-xl border border-amber-300 bg-amber-50/60 p-4 md:flex-row md:items-center lg:p-5">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="h-4 w-4 text-amber-700" />
                    <span className="text-xs font-bold uppercase tracking-wide text-amber-900">
                      Mandatory Human Approval Gate
                    </span>
                    <span className="rounded bg-amber-100 px-1.5 py-0.5 font-mono text-[10px] text-amber-800">
                      {activeSession.consolidatedReport.approvalRequestId}
                    </span>
                  </div>
                  <p className="text-xs text-amber-900">
                    {activeSession.consolidatedReport.actionRequired}
                  </p>
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  <button
                    onClick={() => {
                      if (activeSession.consolidatedReport?.approvalRequestId) {
                        handleApprove(activeSession.consolidatedReport.approvalRequestId);
                      }
                    }}
                    className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-xs transition-colors hover:bg-emerald-700"
                  >
                    Authorize Operation
                  </button>
                  <button
                    onClick={() => setCurrentView('approvals')}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50"
                  >
                    Inspect in Approval Center
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Prompt Input Form Bar */}
        <form
          onSubmit={handleSubmit}
          className="flex items-center gap-3 border-t border-slate-200 bg-slate-50 p-4"
        >
          <input
            type="text"
            value={promptInput}
            onChange={(e) => setPromptInput(e.target.value)}
            disabled={isOrchestrating}
            placeholder="Type any natural language instruction for WorkBuddy to orchestrate across agents..."
            className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-xs text-slate-900 shadow-2xs outline-none placeholder:text-slate-400 focus:border-indigo-600 lg:text-sm"
          />
          <button
            type="submit"
            disabled={!promptInput.trim() || isOrchestrating}
            className="flex shrink-0 items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-xs transition-colors hover:bg-indigo-700 disabled:bg-slate-300"
          >
            {isOrchestrating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span className="hidden sm:inline">Coordinate Agents</span>
          </button>
        </form>
      </div>
    </div>
  );
}
