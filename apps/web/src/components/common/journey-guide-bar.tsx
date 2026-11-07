'use client';

import { useState } from 'react';
import {
  Bot,
  Building2,
  ChevronDown,
  ChevronUp,
  Package,
  ShieldCheck,
  X,
} from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function JourneyGuideBar() {
  const { triggerJourney, currentJourney, approvals } = useDextra();
  const [isMinimized, setIsMinimized] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  const pendingApprovalsCount = approvals.filter((a) => a.status === 'pending').length;

  if (isDismissed) return null;

  return (
    <div className="fixed bottom-4 left-1/2 z-40 w-11/12 max-w-4xl -translate-x-1/2 transition-all">
      <div className="flex flex-col gap-2 rounded-xl border border-slate-700/80 bg-slate-900/95 p-3 text-white shadow-2xl backdrop-blur-md">
        {/* Top Header */}
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-500" />
            <span className="flex items-center gap-1.5 text-xs font-bold tracking-tight text-slate-100">
              <span>Interactive Verification Guide</span>
              <span className="font-normal text-slate-400">
                · Test 4 End-to-End Enterprise Flows
              </span>
            </span>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="rounded p-1 text-slate-400 hover:text-slate-200"
              title={isMinimized ? 'Expand' : 'Collapse'}
            >
              {isMinimized ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
            </button>
            <button
              onClick={() => setIsDismissed(true)}
              className="rounded p-1 text-slate-400 hover:text-slate-200"
              title="Close guide"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Buttons strip */}
        {!isMinimized && (
          <div className="grid grid-cols-2 gap-2 border-t border-slate-800 pt-1 md:grid-cols-4">
            <button
              onClick={() => triggerJourney(1)}
              className={`flex items-start gap-2 rounded-lg p-2 text-left transition-colors ${
                currentJourney === 1
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800'
              }`}
            >
              <Bot className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
              <div className="min-w-0">
                <div className="truncate text-[11px] font-bold text-white">
                  Journey 1: Multi-Agent AI
                </div>
                <div className="truncate text-[10px] text-slate-400">
                  Decompose HR & Finance
                </div>
              </div>
            </button>

            <button
              onClick={() => triggerJourney(2)}
              className={`flex items-start gap-2 rounded-lg p-2 text-left transition-colors ${
                currentJourney === 2
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800'
              }`}
            >
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
              <div className="min-w-0">
                <div className="truncate text-[11px] font-bold text-white">
                  Journey 2: Human Sign-Off
                </div>
                <div className="truncate text-[10px] text-amber-400">
                  {pendingApprovalsCount} Gated Decisions
                </div>
              </div>
            </button>

            <button
              onClick={() => triggerJourney(3)}
              className={`flex items-start gap-2 rounded-lg p-2 text-left transition-colors ${
                currentJourney === 3
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800'
              }`}
            >
              <Building2 className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
              <div className="min-w-0">
                <div className="truncate text-[11px] font-bold text-white">
                  Journey 3: HR Workflow
                </div>
                <div className="truncate text-[10px] text-slate-400">
                  Attendance Anomaly Check
                </div>
              </div>
            </button>

            <button
              onClick={() => triggerJourney(4)}
              className={`flex items-start gap-2 rounded-lg p-2 text-left transition-colors ${
                currentJourney === 4
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800'
              }`}
            >
              <Package className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
              <div className="min-w-0">
                <div className="truncate text-[11px] font-bold text-white">
                  Journey 4: Inventory Alert
                </div>
                <div className="truncate text-[10px] text-slate-400">Low Stock & Reorder PO</div>
              </div>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
