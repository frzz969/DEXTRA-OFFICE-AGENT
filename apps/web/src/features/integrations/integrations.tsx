'use client';

import {
  Puzzle,
  RotateCw,
  Database,
  Building2,
  Layers,
  MessageSquare,
} from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function Integrations() {
  const { integrations, syncIntegration } = useDextra();

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'ERP':
        return Layers;
      case 'HRIS':
        return Building2;
      case 'Database':
        return Database;
      case 'Communication':
        return MessageSquare;
      default:
        return Puzzle;
    }
  };

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-600 mb-1">
            <Puzzle className="w-4 h-4" />
            <span>Enterprise Connectors & API Gateways</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-slate-900 tracking-tight">
            System Integrations & Live Data Sync
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Real-time synchronizers linking DEXTRA multi-agent workers to ERP, HRIS, and operational
            datalakes.
          </p>
        </div>

        <button
          onClick={() => integrations.forEach((int) => syncIntegration(int.id))}
          className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs transition-colors self-start md:self-auto"
        >
          <RotateCw className="w-4 h-4" />
          <span>Sync All 5 Connectors</span>
        </button>
      </div>

      {/* Integration Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {integrations.map((service) => {
          const Icon = getCategoryIcon(service.category);
          const isSyncing = service.status === 'syncing';

          return (
            <div
              key={service.id}
              className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-5 flex flex-col justify-between hover:border-slate-300 transition-colors"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shrink-0">
                    <Icon className="w-5 h-5" />
                  </div>

                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase ${
                      isSyncing
                        ? 'bg-amber-100 text-amber-800'
                        : service.status === 'connected'
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : 'bg-rose-50 text-rose-700'
                    }`}
                  >
                    {isSyncing ? 'Syncing...' : service.status}
                  </span>
                </div>

                <div>
                  <span className="text-[10px] font-mono font-semibold text-slate-400 uppercase">
                    {service.category} Connector
                  </span>
                  <h3 className="text-sm font-bold text-slate-900 mt-0.5">{service.name}</h3>
                  <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                    {service.description}
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-100 grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-[10px] text-slate-400 block font-mono">Last Sync</span>
                    <span className="font-semibold text-slate-800">{service.lastSync}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block font-mono">
                      Records Tracked
                    </span>
                    <span className="font-semibold font-mono text-slate-800">
                      {service.recordsSynced.toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[11px] text-emerald-600 font-mono font-semibold">
                  {service.healthPercent}% Uptime
                </span>

                <button
                  onClick={() => syncIntegration(service.id)}
                  disabled={isSyncing}
                  className="px-2.5 py-1 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-md transition-colors flex items-center gap-1.5"
                >
                  <RotateCw className={`w-3 h-3 ${isSyncing ? 'animate-spin' : ''}`} />
                  <span>{isSyncing ? 'Syncing' : 'Sync Now'}</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
