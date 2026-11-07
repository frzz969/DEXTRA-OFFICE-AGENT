'use client';

import { Calendar, Mail, MapPin, Phone, ShieldAlert, X } from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function EmployeeModal() {
  const { selectedEmployee, setSelectedEmployee, leaveRequests } = useDextra();

  if (!selectedEmployee) return null;

  const employeeLeaves = leaveRequests.filter((l) => l.employeeId === selectedEmployee.id);
  const isAnomaly = selectedEmployee.attendanceRate < 90;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-xs"
      onClick={() => setSelectedEmployee(null)}
    >
      <div
        className="flex w-full max-w-lg flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-200 bg-slate-50 p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full border border-indigo-200 bg-indigo-100 text-base font-bold text-indigo-700">
              {selectedEmployee.fullName
                .split(' ')
                .map((n) => n[0])
                .join('')}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900">
                  {selectedEmployee.fullName}
                </h3>
                <span
                  className={`rounded px-2 py-0.5 text-[10px] font-semibold ${
                    selectedEmployee.status === 'active'
                      ? 'border border-emerald-200 bg-emerald-50 text-emerald-700'
                      : 'border border-amber-200 bg-amber-50 text-amber-700'
                  }`}
                >
                  {selectedEmployee.status.replace('_', ' ').toUpperCase()}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                {selectedEmployee.role} · {selectedEmployee.department}
              </p>
            </div>
          </div>
          <button
            onClick={() => setSelectedEmployee(null)}
            className="rounded-md p-1 text-slate-400 hover:text-slate-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-5 p-6">
          {/* Contact Details */}
          <div className="grid grid-cols-2 gap-3 text-xs text-slate-600">
            <div className="flex items-center gap-2">
              <Mail className="h-3.5 w-3.5 text-slate-400" />
              <span>{selectedEmployee.email}</span>
            </div>
            <div className="flex items-center gap-2">
              <Phone className="h-3.5 w-3.5 text-slate-400" />
              <span>{selectedEmployee.phone}</span>
            </div>
            <div className="flex items-center gap-2">
              <MapPin className="h-3.5 w-3.5 text-slate-400" />
              <span>{selectedEmployee.location}</span>
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="h-3.5 w-3.5 text-slate-400" />
              <span>Joined {selectedEmployee.joinDate}</span>
            </div>
          </div>

          {/* Performance & Attendance */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <span className="text-[10px] font-semibold uppercase text-slate-400">
                Attendance
              </span>
              <div className="mt-1 flex items-baseline gap-1">
                <span
                  className={`font-mono text-lg font-bold ${
                    isAnomaly ? 'text-amber-600' : 'text-slate-900'
                  }`}
                >
                  {selectedEmployee.attendanceRate}%
                </span>
              </div>
              {isAnomaly && (
                <span className="mt-0.5 flex items-center gap-1 text-[10px] font-medium text-amber-700">
                  <ShieldAlert className="h-3 w-3 text-amber-600" />
                  Anomaly Flagged
                </span>
              )}
            </div>

            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <span className="text-[10px] font-semibold uppercase text-slate-400">Rating</span>
              <div className="mt-1 flex items-baseline gap-1">
                <span className="font-mono text-lg font-bold text-emerald-600">
                  {selectedEmployee.performanceScore}
                </span>
                <span className="text-xs text-slate-400">/ 5.0</span>
              </div>
              <span className="mt-0.5 block text-[10px] text-slate-400">Top Performer</span>
            </div>

            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <span className="text-[10px] font-semibold uppercase text-slate-400">
                Base Compensation
              </span>
              <div className="mt-1 flex items-baseline gap-1">
                <span className="font-mono text-base font-bold text-slate-900">
                  ${(selectedEmployee.salary / 1000).toFixed(0)}k
                </span>
                <span className="text-[10px] text-slate-400">/ yr</span>
              </div>
              <span className="mt-0.5 block text-[10px] text-slate-400">Semi-monthly ACH</span>
            </div>
          </div>

          {/* Leave History */}
          <div>
            <h4 className="mb-2 text-xs font-semibold text-slate-800">Leave History & Requests</h4>
            {employeeLeaves.length === 0 ? (
              <p className="text-xs italic text-slate-500">No recent leave requests logged.</p>
            ) : (
              <div className="space-y-2">
                {employeeLeaves.map((l) => (
                  <div
                    key={l.id}
                    className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-2.5 text-xs"
                  >
                    <div>
                      <div className="font-medium text-slate-900">
                        {l.type} ({l.days} days)
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {l.startDate} to {l.endDate} · {l.reason}
                      </div>
                    </div>
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-semibold ${
                        l.status === 'approved'
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-amber-50 text-amber-700'
                      }`}
                    >
                      {l.status.toUpperCase()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 p-4">
          <span className="font-mono text-[11px] text-slate-400">ID: {selectedEmployee.id}</span>
          <button
            onClick={() => setSelectedEmployee(null)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
