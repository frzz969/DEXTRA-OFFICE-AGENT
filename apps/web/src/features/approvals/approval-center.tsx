'use client';

import { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  XCircle,
  Lock,
  DollarSign,
  FileText,
  UserCheck,
  Hash,
} from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function ApprovalCenter() {
  const { approvals, handleApprove, handleReject, handleRequestChanges, setCurrentView } =
    useDextra();

  const [filterRisk, setFilterRisk] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [rejectReason, setRejectReason] = useState('');
  const [isRejectingId, setIsRejectingId] = useState<string | null>(null);

  const filteredApprovals = approvals.filter((a) => {
    if (filterRisk !== 'all' && a.riskLevel !== filterRisk) return false;
    if (filterStatus !== 'all' && a.status !== filterStatus) return false;
    return true;
  });

  const pendingCount = approvals.filter((a) => a.status === 'pending').length;
  const approvedCount = approvals.filter((a) => a.status === 'approved').length;
  const rejectedCount = approvals.filter((a) => a.status === 'rejected').length;

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-amber-700 mb-1">
            <Lock className="w-3.5 h-3.5" />
            <span>Human-in-the-Loop Governance</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-slate-900 tracking-tight">
            Central Approval Center
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Strict human oversight gateway. AI agents stage sensitive financial, payroll, and HR
            actions but cannot self-execute.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentView('audit-logs')}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 shadow-2xs"
          >
            <Hash className="w-3.5 h-3.5 text-slate-400" />
            <span>View Cryptographic Audit Trail</span>
          </button>
        </div>
      </div>

      {/* KPI & Status Overview Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 bg-amber-50/60 rounded-xl border border-amber-200 shadow-2xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold text-amber-800 uppercase tracking-wider">
              Pending Human Review
            </span>
            <div className="mt-1 text-2xl font-bold font-mono text-amber-950 tabular-nums">
              {pendingCount}
            </div>
            <span className="text-[11px] text-amber-700">Autonomous execution halted</span>
          </div>
          <ShieldAlert className="w-8 h-8 text-amber-600/80" />
        </div>

        <div className="p-4 bg-emerald-50/60 rounded-xl border border-emerald-200 shadow-2xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider">
              Authorized & Cleared
            </span>
            <div className="mt-1 text-2xl font-bold font-mono text-emerald-950 tabular-nums">
              {approvedCount}
            </div>
            <span className="text-[11px] text-emerald-700">Committed to immutable ledger</span>
          </div>
          <ShieldCheck className="w-8 h-8 text-emerald-600/80" />
        </div>

        <div className="p-4 bg-rose-50/60 rounded-xl border border-rose-200 shadow-2xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold text-rose-800 uppercase tracking-wider">
              Denied / Policy Blocked
            </span>
            <div className="mt-1 text-2xl font-bold font-mono text-rose-950 tabular-nums">
              {rejectedCount}
            </div>
            <span className="text-[11px] text-rose-700">Execution aborted by operator</span>
          </div>
          <XCircle className="w-8 h-8 text-rose-600/80" />
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-2 bg-white rounded-xl border border-slate-200 shadow-2xs">
        <div className="flex items-center gap-1">
          <span className="text-xs font-medium text-slate-500 px-3">Status:</span>
          {['all', 'pending', 'approved', 'rejected'].map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors capitalize ${
                filterStatus === st
                  ? 'bg-slate-900 text-white font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1">
          <span className="text-xs font-medium text-slate-500 px-3">Risk Level:</span>
          {['all', 'critical', 'high', 'medium', 'low'].map((risk) => (
            <button
              key={risk}
              onClick={() => setFilterRisk(risk)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors capitalize ${
                filterRisk === risk
                  ? 'bg-indigo-600 text-white font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              {risk}
            </button>
          ))}
        </div>
      </div>

      {/* Main Approval Requests List */}
      <div className="space-y-4">
        {filteredApprovals.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-xl border border-slate-200 text-slate-500 text-xs">
            No approval requests match the selected filters.
          </div>
        ) : (
          filteredApprovals.map((req) => {
            const isPending = req.status === 'pending';
            const isApproved = req.status === 'approved';

            return (
              <div
                key={req.id}
                className={`bg-white rounded-xl border shadow-2xs overflow-hidden transition-all ${
                  isPending
                    ? 'border-amber-300'
                    : isApproved
                    ? 'border-emerald-200 bg-emerald-50/10'
                    : 'border-slate-200 opacity-80'
                }`}
              >
                {/* Header row */}
                <div className="p-4 lg:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100">
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                        isPending
                          ? 'bg-amber-100 text-amber-800'
                          : isApproved
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {req.actionType === 'procurement_po' && <DollarSign className="w-5 h-5" />}
                      {req.actionType === 'payroll_disbursement' && (
                        <FileText className="w-5 h-5" />
                      )}
                      {req.actionType === 'leave_approval' && <UserCheck className="w-5 h-5" />}
                      {req.actionType !== 'procurement_po' &&
                        req.actionType !== 'payroll_disbursement' &&
                        req.actionType !== 'leave_approval' && (
                          <ShieldAlert className="w-5 h-5" />
                        )}
                    </div>

                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-slate-400">
                          {req.id}
                        </span>
                        <span className="text-slate-300">·</span>
                        <span className="text-xs font-medium text-slate-600">
                          {req.department}
                        </span>
                        <span className="text-slate-300">·</span>
                        <span className="text-xs text-slate-500">
                          Staged by{' '}
                          <strong className="text-slate-800">{req.requestingAgentName}</strong>
                        </span>
                      </div>

                      <h3 className="text-base font-bold text-slate-900 mt-0.5">{req.title}</h3>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-start md:self-center">
                    <span
                      className={`px-2.5 py-1 text-xs font-bold font-mono rounded uppercase ${
                        req.riskLevel === 'critical'
                          ? 'bg-rose-100 text-rose-800'
                          : req.riskLevel === 'high'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}
                    >
                      {req.riskLevel} Risk
                    </span>

                    <span
                      className={`px-2.5 py-1 text-xs font-bold rounded uppercase ${
                        isPending
                          ? 'bg-amber-500 text-white'
                          : isApproved
                          ? 'bg-emerald-600 text-white'
                          : 'bg-slate-600 text-white'
                      }`}
                    >
                      {req.status}
                    </span>
                  </div>
                </div>

                {/* Justification & Supporting Data */}
                <div className="p-4 lg:p-5 space-y-4">
                  <div>
                    <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                      Agent Business Justification
                    </span>
                    <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-200">
                      {req.businessJustification}
                    </p>
                  </div>

                  {/* Supporting Data Grid */}
                  <div>
                    <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-2">
                      Verified Supporting Telemetry & Parameters
                    </span>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
                      {Object.entries(req.supportingData).map(([key, value]) => (
                        <div
                          key={key}
                          className="p-2.5 rounded-lg border border-slate-200 bg-white text-xs"
                        >
                          <span className="text-[10px] text-slate-400 uppercase font-mono block">
                            {key.replace(/([A-Z])/g, ' $1')}
                          </span>
                          <span className="font-semibold font-mono text-slate-900 truncate block mt-0.5">
                            {typeof value === 'boolean'
                              ? value
                                ? 'Yes / Confirmed'
                                : 'No'
                              : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* If Approved or Rejected Details */}
                  {req.reviewedBy && (
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs flex items-center justify-between">
                      <div className="text-slate-600">
                        Reviewed by <strong className="text-slate-800">{req.reviewedBy}</strong> at{' '}
                        {req.reviewedAt}
                        {req.notes && (
                          <span className="block text-[11px] text-slate-500 mt-0.5">
                            Note: &quot;{req.notes}&quot;
                          </span>
                        )}
                      </div>
                      <span className="text-emerald-700 font-mono text-[11px] font-semibold">
                        Audit Log Hash Confirmed
                      </span>
                    </div>
                  )}

                  {/* Reject Prompt Drawer if triggered */}
                  {isRejectingId === req.id && (
                    <div className="p-3 bg-rose-50 rounded-lg border border-rose-200 space-y-2">
                      <span className="text-xs font-bold text-rose-900 block">
                        Specify Denial Rationale for Audit Log:
                      </span>
                      <input
                        type="text"
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="e.g. Budget ceiling reached / Vendor renegotiation requested"
                        className="w-full text-xs px-3 py-2 bg-white rounded border border-rose-300 text-slate-900 outline-none"
                      />
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setIsRejectingId(null)}
                          className="px-3 py-1 text-xs text-slate-600 hover:text-slate-900 bg-white border border-slate-200 rounded"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => {
                            handleReject(req.id, rejectReason);
                            setIsRejectingId(null);
                            setRejectReason('');
                          }}
                          className="px-3 py-1 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded shadow-xs"
                        >
                          Confirm Denial
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Action Toolbar */}
                {isPending && (
                  <div className="p-4 bg-slate-50/80 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span>Threshold Policy:</span>
                      <span className="font-semibold text-slate-700 font-mono">
                        {req.amount
                          ? `Requires human sign-off for >$5,000 USD`
                          : `Human Oversight Mandated`}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setIsRejectingId(req.id)}
                        className="px-3.5 py-1.5 text-xs font-semibold text-rose-700 bg-white hover:bg-rose-50 border border-rose-200 rounded-lg transition-colors"
                      >
                        Reject Action
                      </button>
                      <button
                        onClick={() =>
                          handleRequestChanges(
                            req.id,
                            'Please request supplier quote revision with 5% volume discount'
                          )
                        }
                        className="px-3.5 py-1.5 text-xs font-medium text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors"
                      >
                        Request Changes
                      </button>
                      <button
                        onClick={() => handleApprove(req.id)}
                        className="px-4 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs transition-colors"
                      >
                        Authorize & Execute
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
