'use client';

import { useState } from 'react';
import { DollarSign, Lock, CheckCircle2, Sparkles } from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function FinanceManagement() {
  const { payroll, transactions, budgets, handleApprove, runWorkBuddyPrompt } = useDextra();

  const [activeTab, setActiveTab] = useState<'overview' | 'payroll' | 'ledger'>('overview');

  const totalAllocated = budgets.reduce((acc, b) => acc + b.allocated, 0);
  const totalSpent = budgets.reduce((acc, b) => acc + b.spent, 0);
  const remainingBudget = totalAllocated - totalSpent;

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-700 mb-1">
            <DollarSign className="w-4 h-4" />
            <span>Corporate Finance & Treasury Operations</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-slate-900 tracking-tight">
            Financial Ledger & Payroll Management
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Governed enterprise treasury, automated payroll batches, and policy expenditure
            enforcement.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() =>
              runWorkBuddyPrompt(
                'Audit current month operating expenses, payroll tax withholdings, and flag any transactions above the $5,000 policy threshold.'
              )
            }
            className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs transition-colors"
          >
            <Sparkles className="w-4 h-4" />
            <span>Audit Finances With AI</span>
          </button>
        </div>
      </div>

      {/* Top Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 bg-white rounded-xl border border-slate-200/90 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Total Annual Budget
          </span>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-900 tabular-nums">
            ${(totalAllocated / 1000000).toFixed(2)}M
          </div>
          <span className="text-[11px] text-slate-500 block mt-1">
            Approved FY26 Operating Pool
          </span>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200/90 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            YTD Executed Spend
          </span>
          <div className="mt-2 text-2xl font-bold font-mono text-indigo-600 tabular-nums">
            ${(totalSpent / 1000000).toFixed(2)}M
          </div>
          <span className="text-[11px] text-slate-500 block mt-1">
            {Math.round((totalSpent / totalAllocated) * 100)}% of pool utilized
          </span>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200/90 shadow-2xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Remaining Headroom
          </span>
          <div className="mt-2 text-2xl font-bold font-mono text-emerald-600 tabular-nums">
            ${(remainingBudget / 1000).toFixed(0)}k
          </div>
          <span className="text-[11px] text-emerald-600 font-medium block mt-1">
            +3.4% favorable variance
          </span>
        </div>

        <div className="p-4 bg-amber-50/50 rounded-xl border border-amber-200 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-amber-800 uppercase tracking-wider">
              Gated Disbursements
            </span>
            <Lock className="w-4 h-4 text-amber-700" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-amber-950 tabular-nums">
            ${(payroll.totalGross / 1000).toFixed(1)}k
          </div>
          <span className="text-[11px] text-amber-800 font-medium block mt-1">
            {payroll.status === 'pending_approval'
              ? 'Awaiting Human Sign-off'
              : 'Authorized'}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
            activeTab === 'overview'
              ? 'bg-slate-900 text-white'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          Department Budgets & Variance
        </button>
        <button
          onClick={() => setActiveTab('payroll')}
          className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center gap-2 ${
            activeTab === 'payroll'
              ? 'bg-slate-900 text-white'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <span>Payroll Batch Authorization</span>
          {payroll.status === 'pending_approval' && (
            <span className="w-2 h-2 rounded-full bg-amber-500" />
          )}
        </button>
        <button
          onClick={() => setActiveTab('ledger')}
          className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
            activeTab === 'ledger'
              ? 'bg-slate-900 text-white'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          General Ledger Transactions
        </button>
      </div>

      {/* Tab: Overview (Budgets) */}
      {activeTab === 'overview' && (
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden">
          <div className="p-5 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-900">
              Department Budget Allocation & Forecast Variance
            </h3>
            <p className="text-xs text-slate-500">
              Continuous monitoring by Finance & Ledger Agent against historical burn rates.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase text-[10px] tracking-wider">
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4 text-right">Allocated</th>
                  <th className="py-3 px-4 text-right">Actual Spent</th>
                  <th className="py-3 px-4 text-right">Remaining</th>
                  <th className="py-3 px-4 text-right">Burn Rate</th>
                  <th className="py-3 px-4 text-right">Projected Variance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {budgets.map((b) => {
                  const percent = Math.round((b.spent / b.allocated) * 100);
                  return (
                    <tr key={b.department} className="hover:bg-slate-50/60">
                      <td className="py-3.5 px-4 font-bold text-slate-900">{b.department}</td>
                      <td className="py-3.5 px-4 text-right font-mono text-slate-700 tabular-nums">
                        ${b.allocated.toLocaleString()}.00
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono font-bold text-slate-900 tabular-nums">
                        ${b.spent.toLocaleString()}.00
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono text-emerald-600 font-medium tabular-nums">
                        ${b.remaining.toLocaleString()}.00
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <span className="font-mono text-slate-700">{percent}%</span>
                          <div className="w-16 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-indigo-600 h-1.5 rounded-full"
                              style={{ width: `${percent}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono font-semibold tabular-nums">
                        <span
                          className={
                            b.projectedVariance > 0 ? 'text-amber-600' : 'text-emerald-600'
                          }
                        >
                          {b.projectedVariance > 0
                            ? `+${b.projectedVariance}%`
                            : `${b.projectedVariance}%`}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab: Payroll Management */}
      {activeTab === 'payroll' && (
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-6 space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900">{payroll.month}</h3>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                    payroll.status === 'approved'
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {payroll.status.replace('_', ' ')}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Batch ID: <span className="font-mono">{payroll.id}</span> · Reconciled by Finance &
                Ledger Agent
              </p>
            </div>

            {payroll.status === 'pending_approval' ? (
              <button
                onClick={() => handleApprove('APR-1050')}
                className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs transition-colors"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Executive Authorize ACH Release</span>
              </button>
            ) : (
              <span className="text-xs font-semibold text-emerald-700 flex items-center gap-1.5 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Disbursed & Logged at {payroll.processedDate}</span>
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-[10px] font-bold uppercase text-slate-500">Gross Payroll</span>
              <div className="text-xl font-bold font-mono text-slate-900 mt-1 tabular-nums">
                ${payroll.totalGross.toLocaleString()}.00
              </div>
              <span className="text-[11px] text-slate-500 block mt-1">
                +0.8% planned overtime
              </span>
            </div>

            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-[10px] font-bold uppercase text-slate-500">
                Tax Withholding
              </span>
              <div className="text-xl font-bold font-mono text-slate-700 mt-1 tabular-nums">
                $104,430.00
              </div>
              <span className="text-[11px] text-slate-500 block mt-1">Fed / State / FICA</span>
            </div>

            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-[10px] font-bold uppercase text-slate-500">
                Net ACH Direct Deposit
              </span>
              <div className="text-xl font-bold font-mono text-emerald-600 mt-1 tabular-nums">
                ${payroll.netPay.toLocaleString()}.00
              </div>
              <span className="text-[11px] text-slate-500 block mt-1">8 Employee Accounts</span>
            </div>

            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-[10px] font-bold uppercase text-slate-500">
                Governance Policy
              </span>
              <div className="text-xs font-semibold text-slate-900 mt-1">POL-02 Enforced</div>
              <span className="text-[11px] text-amber-700 font-medium block mt-1">
                Zero agent auto-disbursement
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Tab: General Ledger */}
      {activeTab === 'ledger' && (
        <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900">General Ledger Audit Trail</h3>
              <p className="text-xs text-slate-500">
                All disbursements and incoming revenue streams verified against corporate accounts.
              </p>
            </div>
            <span className="text-xs text-slate-400 font-mono">SAP S/4HANA Synced</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase text-[10px] tracking-wider">
                  <th className="py-3 px-4">TX ID</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Description</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4 text-right">Amount</th>
                  <th className="py-3 px-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {transactions.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-50/60">
                    <td className="py-3.5 px-4 font-mono font-medium text-slate-500">{tx.id}</td>
                    <td className="py-3.5 px-4 text-slate-600 font-mono">{tx.date}</td>
                    <td className="py-3.5 px-4 font-bold text-slate-900">{tx.description}</td>
                    <td className="py-3.5 px-4 text-slate-600">{tx.department}</td>
                    <td className="py-3.5 px-4 font-mono text-slate-500">{tx.category}</td>
                    <td
                      className={`py-3.5 px-4 text-right font-mono font-bold tabular-nums ${
                        tx.type === 'income' ? 'text-emerald-600' : 'text-slate-900'
                      }`}
                    >
                      {tx.type === 'income' ? '+' : '-'}${tx.amount.toLocaleString()}.00
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 uppercase">
                        {tx.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
