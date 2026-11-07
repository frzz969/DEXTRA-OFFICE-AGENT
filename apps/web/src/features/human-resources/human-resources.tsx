'use client';

import { useState } from 'react';
import {
  Users,
  Search,
  ShieldAlert,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function HumanResources() {
  const { employees, leaveRequests, setSelectedEmployee, runWorkBuddyPrompt, handleApprove } =
    useDextra();

  const [searchQuery, setSearchQuery] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('all');

  const filteredEmployees = employees.filter((emp) => {
    if (departmentFilter !== 'all' && emp.department !== departmentFilter) return false;
    if (
      searchQuery &&
      !emp.fullName.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !emp.role.toLowerCase().includes(searchQuery.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  const departments = ['all', 'Engineering', 'Finance', 'Operations', 'Human Resources'];

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-600 mb-1">
            <Users className="w-4 h-4" />
            <span>Human Capital Management & HRIS</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-slate-900 tracking-tight">
            Workforce Directory & Attendance
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Integrated employee directory, AI attendance anomaly tracking, and leave entitlement
            workflows.
          </p>
        </div>

        <button
          onClick={() =>
            runWorkBuddyPrompt(
              'Run complete workforce attendance audit across all departments and isolate anomalies.'
            )
          }
          className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs transition-colors self-start md:self-auto"
        >
          <Sparkles className="w-4 h-4" />
          <span>Audit Attendance With HR Agent</span>
        </button>
      </div>

      {/* AI HR Intelligence Anomaly Insight Box */}
      <div className="p-4 lg:p-5 rounded-xl border border-amber-200 bg-amber-50/50 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-2xs">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-amber-100 flex items-center justify-center shrink-0">
            <ShieldAlert className="w-5 h-5 text-amber-700" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-amber-900">
                HR Intelligence Agent · Attendance Anomaly Detected
              </h3>
              <span className="text-[10px] bg-amber-200/80 text-amber-900 px-1.5 py-0.5 rounded font-mono">
                EMP-1002
              </span>
            </div>
            <p className="text-xs text-amber-900 mt-1 leading-relaxed">
              <strong>Marcus Vance (Senior Staff Data Architect)</strong> has recorded an 86.2%
              attendance rate over the last 14 days. Cross-referencing tickets indicates pending
              medical sick leave request (LR-3082) covering post-op recovery. Lead architect
              coverage is verified with Elena Rostova.
            </p>
          </div>
        </div>

        <button
          onClick={() => {
            const vance = employees.find((e) => e.id === 'EMP-1002');
            if (vance) setSelectedEmployee(vance);
          }}
          className="px-3.5 py-1.5 text-xs font-semibold text-amber-900 bg-amber-100 hover:bg-amber-200 border border-amber-300 rounded-lg shrink-0 transition-colors"
        >
          Inspect Record
        </button>
      </div>

      {/* Top Search & Filter Strip */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-white rounded-xl border border-slate-200 shadow-2xs">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 shrink-0 ml-1" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search employees by name, title, or skills..."
            className="w-full text-xs text-slate-900 bg-transparent outline-none placeholder:text-slate-400"
          />
        </div>

        <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0">
          <span className="text-xs text-slate-400 px-2 shrink-0">Department:</span>
          {departments.map((dept) => (
            <button
              key={dept}
              onClick={() => setDepartmentFilter(dept)}
              className={`px-3 py-1 text-xs font-medium rounded-lg capitalize whitespace-nowrap transition-colors ${
                departmentFilter === dept
                  ? 'bg-slate-900 text-white font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              {dept}
            </button>
          ))}
        </div>
      </div>

      {/* Employee Directory Table */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase text-[10px] tracking-wider">
                <th className="py-3 px-4">Employee</th>
                <th className="py-3 px-4">Department</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Attendance</th>
                <th className="py-3 px-4 text-right">Rating</th>
                <th className="py-3 px-4 text-right">Compensation</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredEmployees.map((emp) => {
                const isAnomaly = emp.attendanceRate < 90;
                return (
                  <tr
                    key={emp.id}
                    onClick={() => setSelectedEmployee(emp)}
                    className="hover:bg-slate-50/80 cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center font-bold text-slate-700">
                          {emp.fullName
                            .split(' ')
                            .map((n) => n[0])
                            .join('')}
                        </div>
                        <div>
                          <div className="font-bold text-slate-900 flex items-center gap-1.5">
                            <span>{emp.fullName}</span>
                            {isAnomaly && (
                              <span className="text-[9px] font-semibold bg-amber-100 text-amber-800 px-1.5 py-0.2 rounded">
                                Anomaly
                              </span>
                            )}
                          </div>
                          <span className="text-[11px] text-slate-500">{emp.role}</span>
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-medium text-slate-700">{emp.department}</td>

                    <td className="py-3.5 px-4">
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                          emp.status === 'active'
                            ? 'bg-emerald-50 text-emerald-700'
                            : 'bg-amber-50 text-amber-700'
                        }`}
                      >
                        {emp.status.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <span
                        className={`font-mono font-bold tabular-nums ${
                          isAnomaly ? 'text-amber-700' : 'text-slate-900'
                        }`}
                      >
                        {emp.attendanceRate}%
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-right font-mono font-bold text-slate-900 tabular-nums">
                      {emp.performanceScore} / 5.0
                    </td>

                    <td className="py-3.5 px-4 text-right font-mono text-slate-700 tabular-nums">
                      ${(emp.salary / 1000).toFixed(0)}k/yr
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <span className="text-indigo-600 font-semibold hover:underline">Profile</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Leave Management Queue */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-5">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Leave Requests & Absence Entitlements
            </h3>
            <p className="text-xs text-slate-500">
              Verified by HR Intelligence Agent; awaiting operator confirmation.
            </p>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {leaveRequests.length} Active Records
          </span>
        </div>

        <div className="mt-4 space-y-3">
          {leaveRequests.map((lr) => (
            <div
              key={lr.id}
              className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-900">{lr.employeeName}</span>
                  <span className="text-slate-400 font-mono">({lr.department})</span>
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.2 rounded uppercase ${
                      lr.status === 'approved'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {lr.status}
                  </span>
                </div>
                <div className="text-slate-600 mt-1">
                  <strong>{lr.type}</strong> ({lr.days} days): {lr.startDate} to {lr.endDate} · &quot;{lr.reason}&quot;
                </div>
              </div>

              {lr.status === 'pending' ? (
                <button
                  onClick={() => handleApprove('APR-1051')}
                  className="px-3 py-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-lg transition-colors shrink-0"
                >
                  Approve Leave
                </button>
              ) : (
                <span className="text-emerald-700 font-medium flex items-center gap-1 shrink-0">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Approved</span>
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
