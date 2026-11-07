'use client';

import { useState } from 'react';
import { Activity, Bot, CheckCircle2, Sparkles, User } from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function OperationsTasks() {
  const { tasks, runWorkBuddyPrompt } = useDextra();
  const [filterType, setFilterType] = useState<'all' | 'agent' | 'human'>('all');

  const filteredTasks = tasks.filter((t) => {
    if (filterType !== 'all' && t.assigneeType !== filterType) return false;
    return true;
  });

  const agentTasks = tasks.filter((t) => t.assigneeType === 'agent');
  const humanTasks = tasks.filter((t) => t.assigneeType === 'human');

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold text-indigo-600">
            <Activity className="h-4 w-4" />
            <span>Task Orchestration & Workflow Engine</span>
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 lg:text-3xl">
            Operations & Task Workforce
          </h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Synchronized execution across human operational specialists and autonomous AI agent
            workers.
          </p>
        </div>

        <button
          onClick={() =>
            void runWorkBuddyPrompt(
              'Coordinate engineering sprint capacity with active AI agents and reassign blocked tasks.'
            )
          }
          className="flex items-center gap-2 self-start rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs transition-colors hover:bg-indigo-700 md:self-auto"
        >
          <Sparkles className="h-4 w-4" />
          <span>Optimize Sprints With Ops Agent</span>
        </button>
      </div>

      {/* Workforce Distribution Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Autonomous AI Tasks
            </span>
            <Bot className="h-4 w-4 text-indigo-600" />
          </div>
          <div className="mt-2 font-mono text-2xl font-bold tabular-nums text-slate-900">
            {agentTasks.length} Active
          </div>
          <span className="mt-1 block text-[11px] text-slate-500">
            Average turnaround: 4.2 minutes
          </span>
        </div>

        <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Human Team Tasks
            </span>
            <User className="h-4 w-4 text-slate-700" />
          </div>
          <div className="mt-2 font-mono text-2xl font-bold tabular-nums text-slate-900">
            {humanTasks.length} Assigned
          </div>
          <span className="mt-1 block text-[11px] text-slate-500">
            Executive review & facility logistics
          </span>
        </div>

        <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              SLA Delivery Velocity
            </span>
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="mt-2 font-mono text-2xl font-bold tabular-nums text-emerald-600">
            99.2%
          </div>
          <span className="mt-1 block text-[11px] font-medium text-emerald-600">
            Zero SLA breaches this quarter
          </span>
        </div>
      </div>

      {/* Segmented Filter Control */}
      <div className="flex w-fit items-center gap-1.5 rounded-lg border border-slate-200/60 bg-slate-100 p-1">
        <button
          onClick={() => setFilterType('all')}
          className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
            filterType === 'all'
              ? 'bg-white font-semibold text-slate-900 shadow-2xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          All Tasks ({tasks.length})
        </button>
        <button
          onClick={() => setFilterType('agent')}
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
            filterType === 'agent'
              ? 'bg-white font-semibold text-indigo-900 shadow-2xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <Bot className="h-3.5 w-3.5 text-indigo-600" />
          <span>AI Agent Tasks ({agentTasks.length})</span>
        </button>
        <button
          onClick={() => setFilterType('human')}
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
            filterType === 'human'
              ? 'bg-white font-semibold text-slate-900 shadow-2xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <User className="h-3.5 w-3.5 text-slate-700" />
          <span>Human Tasks ({humanTasks.length})</span>
        </button>
      </div>

      {/* Task Cards List */}
      <div className="space-y-3">
        {filteredTasks.map((t) => {
          const isAgent = t.assigneeType === 'agent';
          return (
            <div
              key={t.id}
              className="flex flex-col justify-between gap-4 rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs transition-colors hover:border-slate-300 md:flex-row md:items-center"
            >
              <div className="flex min-w-0 items-start gap-3">
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                    isAgent ? 'bg-indigo-50 text-indigo-600' : 'bg-slate-100 text-slate-700'
                  }`}
                >
                  {isAgent ? <Bot className="h-5 w-5" /> : <User className="h-5 w-5" />}
                </div>

                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-semibold text-slate-400">{t.id}</span>
                    <span className="text-slate-300">·</span>
                    <span className="text-xs font-medium text-slate-600">{t.department}</span>
                    <span className="text-slate-300">·</span>
                    <span className="font-mono text-xs text-slate-500">Due {t.dueDate}</span>
                  </div>

                  <h3 className="mt-0.5 text-sm font-bold text-slate-900">{t.title}</h3>

                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {t.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[10px] text-slate-600"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Progress & Assignee Info */}
              <div className="flex shrink-0 items-center gap-6 self-start pl-12 md:self-center md:pl-0">
                <div className="text-right">
                  <div className="flex items-center justify-end gap-1.5 text-xs font-semibold text-slate-900">
                    {isAgent ? (
                      <Bot className="h-3.5 w-3.5 text-indigo-600" />
                    ) : (
                      <User className="h-3.5 w-3.5 text-slate-700" />
                    )}
                    <span>{t.assigneeName}</span>
                  </div>
                  <div className="font-mono text-[11px] text-slate-400">
                    Priority:{' '}
                    <span className="font-semibold uppercase text-slate-700">{t.priority}</span>
                  </div>
                </div>

                <div className="w-24">
                  <div className="mb-1 flex items-center justify-between font-mono text-[11px] text-slate-600">
                    <span>{t.progress}%</span>
                    <span className="text-[10px] capitalize text-slate-400">
                      {t.status.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-slate-100">
                    <div
                      className={`h-1.5 rounded-full ${
                        t.status === 'completed'
                          ? 'bg-emerald-500'
                          : t.status === 'pending_approval'
                            ? 'bg-amber-500'
                            : 'bg-indigo-600'
                      }`}
                      style={{ width: `${t.progress}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
