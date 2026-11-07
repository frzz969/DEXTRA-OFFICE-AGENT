'use client';

import { useState } from 'react';
import { Settings, Shield, Building, CheckCircle2, Save } from 'lucide-react';

type GovernanceMode = 'strict' | 'standard' | 'relaxed';

export function SettingsView() {
  const [orgName, setOrgName] = useState('Apex Industrial Global Inc.');
  const [governanceMode, setGovernanceMode] = useState<GovernanceMode>('strict');
  const [maxSpendLimit, setMaxSpendLimit] = useState(5000);
  const [dualSignOff, setDualSignOff] = useState(true);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-600 mb-1">
            <Settings className="w-4 h-4" />
            <span>Platform Governance & System Config</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-slate-900 tracking-tight">
            Platform Settings
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Configure organization profiles, autonomous AI spend thresholds, and security sign-off
            policies.
          </p>
        </div>

        {savedSuccess && (
          <span className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg animate-fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Settings Saved</span>
          </span>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Organization Information */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Building className="w-4 h-4 text-indigo-600" />
            <h3 className="text-sm font-bold text-slate-900">Organization Profile</h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Enterprise Name
              </label>
              <input
                type="text"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                className="w-full text-xs px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 outline-none focus:border-indigo-600"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Platform Tenant ID
              </label>
              <input
                type="text"
                value="TENANT-APEX-GLOBAL-PROD"
                readOnly
                className="w-full text-xs px-3.5 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-500 font-mono outline-none"
              />
            </div>
          </div>
        </div>

        {/* AI Autonomous Governance Limits */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Shield className="w-4 h-4 text-indigo-600" />
            <h3 className="text-sm font-bold text-slate-900">AI Governance & Gating Thresholds</h3>
          </div>

          <div className="space-y-4 text-xs">
            <div>
              <label className="font-semibold text-slate-700 block mb-1">
                Enforcement Rigor Mode
              </label>
              <div className="grid grid-cols-3 gap-3">
                {[
                  {
                    id: 'strict',
                    label: 'Strict (Zero-Bypass)',
                    desc: 'All operations >$0 or touching HR require operator approval',
                  },
                  {
                    id: 'standard',
                    label: 'Standard (Threshold)',
                    desc: 'Routine low-risk operations auto-execute up to limit',
                  },
                  {
                    id: 'relaxed',
                    label: 'Supervised Sandbox',
                    desc: 'Pre-production test sandbox mode',
                  },
                ].map((mode) => (
                  <button
                    key={mode.id}
                    type="button"
                    onClick={() => setGovernanceMode(mode.id as GovernanceMode)}
                    className={`p-3 text-left rounded-lg border transition-all ${
                      governanceMode === mode.id
                        ? 'border-indigo-600 bg-indigo-50/50 shadow-2xs'
                        : 'border-slate-200 bg-white hover:bg-slate-50'
                    }`}
                  >
                    <div className="font-bold text-slate-900">{mode.label}</div>
                    <div className="text-[11px] text-slate-500 mt-1 leading-snug">{mode.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Single-Action Spend Gating Ceiling (USD)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2 text-slate-400 font-mono">$</span>
                  <input
                    type="number"
                    value={maxSpendLimit}
                    onChange={(e) => setMaxSpendLimit(Number(e.target.value))}
                    className="w-full text-xs pl-7 pr-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 outline-none focus:border-indigo-600 font-mono"
                  />
                </div>
                <span className="text-[10px] text-slate-400 mt-1 block">
                  Any PO or expenditure above this requires human approval.
                </span>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Payroll Dual Executive Sign-Off
                </label>
                <button
                  type="button"
                  onClick={() => setDualSignOff(!dualSignOff)}
                  className={`w-full text-left px-3.5 py-2 rounded-lg border font-semibold flex items-center justify-between ${
                    dualSignOff
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                      : 'bg-slate-100 border-slate-200 text-slate-600'
                  }`}
                >
                  <span>{dualSignOff ? 'Enabled (Mandatory)' : 'Disabled'}</span>
                  <span className="text-[10px] font-mono">POL-02</span>
                </button>
                <span className="text-[10px] text-slate-400 mt-1 block">
                  Requires two executive operators for payroll disbursement.
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Save Bar */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="submit"
            className="flex items-center gap-2 px-5 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs transition-colors"
          >
            <Save className="w-4 h-4" />
            <span>Save Governance Configuration</span>
          </button>
        </div>
      </form>
    </div>
  );
}
