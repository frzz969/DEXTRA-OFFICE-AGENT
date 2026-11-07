'use client';

import {
  Package,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function InventoryProcurement() {
  const { inventory, purchaseOrders, handleApprove, setCurrentView, runWorkBuddyPrompt } =
    useDextra();

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-600 mb-1">
            <Package className="w-4 h-4" />
            <span>Supply Chain & Warehouse Logistics</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-slate-900 tracking-tight">
            Inventory & Autonomous Procurement
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Real-time component telemetry, safety stock monitoring, and human-governed purchase
            order preparation.
          </p>
        </div>

        <button
          onClick={() =>
            runWorkBuddyPrompt(
              'Audit warehouse component inventory, evaluate reorder thresholds, and prepare a procurement purchase order for low-stock edge nodes.'
            )
          }
          className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs transition-colors self-start md:self-auto"
        >
          <Sparkles className="w-4 h-4" />
          <span>Run Inventory Agent Optimization</span>
        </button>
      </div>

      {/* Critical Stock Alert Banner (Journey 4 Core Anchor) */}
      <div className="p-4 lg:p-5 rounded-xl border border-rose-300 bg-rose-50/70 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-rose-100 flex items-center justify-center shrink-0">
            <AlertTriangle className="w-5 h-5 text-rose-700" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-rose-900">
                Supply Chain Alert: Critical Warehouse Stock Deficit
              </h3>
              <span className="text-[10px] bg-rose-200 text-rose-900 px-1.5 py-0.5 rounded font-mono">
                SKU: EDG-GW-V3
              </span>
            </div>
            <p className="text-xs text-rose-900 mt-1 leading-relaxed">
              <strong>Enterprise Edge Gateway V3</strong> is currently at <strong>14 units</strong>{' '}
              (Minimum safety baseline: 50). Depletion velocity indicates risk of stockout within 5
              business days. Inventory Agent has staged Purchase Requisition{' '}
              <strong>PO-2026-8822 ($14,200.00)</strong> awaiting human sign-off in the Approval
              Center.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => handleApprove('APR-1049')}
            className="px-3.5 py-1.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg shadow-xs transition-colors"
          >
            Authorize Reorder ($14,200)
          </button>
          <button
            onClick={() => setCurrentView('approvals')}
            className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-rose-200 rounded-lg hover:bg-slate-50 transition-colors"
          >
            View Governance Ticket
          </button>
        </div>
      </div>

      {/* Warehouse Inventory Catalog Table */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Enterprise Component Stock & Telemetry
            </h3>
            <p className="text-xs text-slate-500">
              Automated sensor updates from Warehouse Alpha & Beta.
            </p>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {inventory.length} Catalog Items Tracked
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase text-[10px] tracking-wider">
                <th className="py-3 px-4">SKU / Item Name</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4 text-right">In Stock</th>
                <th className="py-3 px-4 text-right">Min Threshold</th>
                <th className="py-3 px-4 text-right">Unit Cost</th>
                <th className="py-3 px-4">Supplier</th>
                <th className="py-3 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {inventory.map((item) => {
                const isCritical = item.status === 'critical';
                const isLow = item.status === 'low_stock';
                const isReordered = item.status === 'reordered';

                return (
                  <tr key={item.sku} className="hover:bg-slate-50/60">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-900">{item.name}</div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        {item.sku} · {item.location}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-medium text-slate-600">{item.category}</td>

                    <td className="py-3.5 px-4 text-right font-mono font-bold tabular-nums">
                      <span
                        className={
                          isCritical
                            ? 'text-rose-600 font-extrabold text-sm'
                            : isLow
                            ? 'text-amber-600 font-bold'
                            : 'text-slate-900'
                        }
                      >
                        {item.stockLevel}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-right font-mono text-slate-500 tabular-nums">
                      {item.minThreshold}
                    </td>

                    <td className="py-3.5 px-4 text-right font-mono text-slate-700 tabular-nums">
                      ${item.unitCost.toFixed(2)}
                    </td>

                    <td className="py-3.5 px-4 text-slate-700">{item.supplier}</td>

                    <td className="py-3.5 px-4 text-right">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono ${
                          isCritical
                            ? 'bg-rose-100 text-rose-800'
                            : isLow
                            ? 'bg-amber-100 text-amber-800'
                            : isReordered
                            ? 'bg-indigo-100 text-indigo-800'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {item.status.replace('_', ' ')}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Purchase Orders Staged by Inventory Agent */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Procurement Purchase Orders (POs)
            </h3>
            <p className="text-xs text-slate-500">
              Autonomous preparation by Inventory Agent with human sign-off gating.
            </p>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {purchaseOrders.length} Recorded
          </span>
        </div>

        <div className="space-y-3">
          {purchaseOrders.map((po) => (
            <div
              key={po.id}
              className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-900 font-mono">{po.poNumber}</span>
                  <span className="text-slate-400">·</span>
                  <span className="text-slate-700 font-medium">{po.supplier}</span>
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.2 rounded uppercase ${
                      po.status === 'approved'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {po.status}
                  </span>
                </div>
                <div className="text-slate-600 mt-1">
                  Items: {po.items.map((i) => `${i.qty}x ${i.name}`).join(', ')} · Staged by{' '}
                  {po.generatedBy} on {po.date}
                </div>
              </div>

              <div className="flex items-center gap-4">
                <span className="text-sm font-bold font-mono text-slate-900 tabular-nums">
                  ${po.totalAmount.toLocaleString()}.00
                </span>
                <span className="text-xs text-emerald-700 font-medium flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Authorized</span>
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
