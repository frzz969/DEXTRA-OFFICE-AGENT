'use client';

import { useState } from 'react';
import { ScrollText, Search, Download, Bot, User, Copy, Check } from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function AuditLogs() {
  const { auditLogs } = useDextra();
  const [search, setSearch] = useState('');
  const [actorFilter, setActorFilter] = useState<'all' | 'user' | 'agent'>('all');
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const filteredLogs = auditLogs.filter((log) => {
    if (actorFilter !== 'all' && log.actorType !== actorFilter) return false;
    if (
      search &&
      !log.action.toLowerCase().includes(search.toLowerCase()) &&
      !log.actorName.toLowerCase().includes(search.toLowerCase()) &&
      !log.details.toLowerCase().includes(search.toLowerCase()) &&
      !log.hash.toLowerCase().includes(search.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  const handleCopy = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleExportCSV = () => {
    const headers = 'ID,Timestamp,Actor,Action,Target,Risk,Result,Hash,Details\n';
    const rows = filteredLogs
      .map(
        (l) =>
          `"${l.id}","${l.timestamp}","${l.actorName}","${l.action}","${l.targetResource}","${l.riskLevel}","${l.result}","${l.hash}","${l.details}"`
      )
      .join('\n');
    const blob = new Blob([headers + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `dextra_audit_log_${Date.now()}.csv`;
    a.click();
  };

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-600 mb-1">
            <ScrollText className="w-4 h-4" />
            <span>Immutable Traceability & Regulatory Ledger</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-slate-900 tracking-tight">
            Audit Logs & Agent Activity Trace
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Cryptographically sealed timeline of all user authorizations, agent recommendations, and
            policy boundary checks.
          </p>
        </div>

        <button
          onClick={handleExportCSV}
          className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg shadow-2xs transition-colors self-start md:self-auto"
        >
          <Download className="w-4 h-4 text-slate-500" />
          <span>Export Audit CSV</span>
        </button>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-white rounded-xl border border-slate-200 shadow-2xs">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 shrink-0 ml-1" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search action, actor, resource, or cryptographic hash..."
            className="w-full text-xs text-slate-900 bg-transparent outline-none placeholder:text-slate-400"
          />
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-xs text-slate-400 px-2">Actor Type:</span>
          {(['all', 'user', 'agent'] as const).map((type) => (
            <button
              key={type}
              onClick={() => setActorFilter(type)}
              className={`px-3 py-1 text-xs font-medium rounded-lg capitalize transition-colors ${
                actorFilter === type
                  ? 'bg-slate-900 text-white font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase text-[10px] tracking-wider">
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">Action Event</th>
                <th className="py-3 px-4">Target Resource</th>
                <th className="py-3 px-4">Result</th>
                <th className="py-3 px-4">Cryptographic Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredLogs.map((log) => {
                const isAgent = log.actorType === 'agent';
                const isSuccess = log.result === 'success';
                const isRequiresApproval = log.result === 'requires_approval';

                return (
                  <tr key={log.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3.5 px-4 font-mono text-slate-500 whitespace-nowrap">
                      {log.timestamp}
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {isAgent ? (
                          <Bot className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                        ) : (
                          <User className="w-3.5 h-3.5 text-slate-700 shrink-0" />
                        )}
                        <span className="font-semibold text-slate-900">{log.actorName}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-mono font-bold text-slate-800">
                      {log.action}
                      <p className="text-[11px] text-slate-500 font-normal font-sans mt-0.5 max-w-sm leading-tight">
                        {log.details}
                      </p>
                    </td>

                    <td className="py-3.5 px-4 text-slate-600 font-mono text-[11px]">
                      {log.targetResource}
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono ${
                          isSuccess
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : isRequiresApproval
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-rose-50 text-rose-700 border border-rose-200'
                        }`}
                      >
                        {log.result.replace('_', ' ')}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <span className="truncate max-w-[120px]">{log.hash}</span>
                        <button
                          onClick={() => handleCopy(log.hash)}
                          className="p-1 hover:text-slate-700"
                          title="Copy full cryptographic SHA-256 hash"
                        >
                          {copiedHash === log.hash ? (
                            <Check className="w-3 h-3 text-emerald-600" />
                          ) : (
                            <Copy className="w-3 h-3 text-slate-400" />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
