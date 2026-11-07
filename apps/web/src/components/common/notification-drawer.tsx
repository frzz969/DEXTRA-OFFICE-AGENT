'use client';

import { Bell, Bot, CheckCircle2, ExternalLink, ShieldAlert, X } from 'lucide-react';
import { useDextra } from '@/providers/dextra-provider';

export function NotificationDrawer() {
  const {
    isNotificationOpen,
    setIsNotificationOpen,
    notifications,
    markAllNotificationsRead,
    setCurrentView,
  } = useDextra();

  if (!isNotificationOpen) return null;

  return (
    <div
      className="fixed inset-0 z-40 flex justify-end bg-slate-900/20 backdrop-blur-2xs"
      onClick={() => setIsNotificationOpen(false)}
    >
      <div
        className="flex h-full w-full max-w-sm flex-col border-l border-slate-200 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 p-4">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-slate-700" />
            <h3 className="text-sm font-semibold text-slate-900">Notifications</h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={markAllNotificationsRead}
              className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
            >
              Mark all read
            </button>
            <button
              onClick={() => setIsNotificationOpen(false)}
              className="rounded-md p-1 text-slate-400 hover:text-slate-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 space-y-2 overflow-y-auto p-3">
          {notifications.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No new notifications.
            </div>
          ) : (
            notifications.map((item) => (
              <div
                key={item.id}
                className={`rounded-lg border p-3 text-xs transition-colors ${
                  !item.isRead
                    ? 'border-slate-200 bg-slate-50 text-slate-900'
                    : 'border-slate-100 bg-white text-slate-600'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-1.5 font-semibold text-slate-900">
                    {item.type === 'approval' && (
                      <ShieldAlert className="h-3.5 w-3.5 shrink-0 text-amber-600" />
                    )}
                    {item.type === 'agent' && (
                      <Bot className="h-3.5 w-3.5 shrink-0 text-indigo-600" />
                    )}
                    {item.type === 'system' && (
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-600" />
                    )}
                    {item.type === 'alert' && (
                      <ShieldAlert className="h-3.5 w-3.5 shrink-0 text-rose-600" />
                    )}
                    <span>{item.title}</span>
                  </div>
                  <span className="shrink-0 text-[10px] text-slate-400">{item.timestamp}</span>
                </div>
                <p className="mt-1 text-[11px] leading-relaxed text-slate-600">{item.message}</p>
                {item.linkView && (
                  <button
                    onClick={() => {
                      setCurrentView(item.linkView!);
                      setIsNotificationOpen(false);
                    }}
                    className="mt-2 inline-flex items-center gap-1 text-[11px] font-medium text-indigo-600 hover:text-indigo-700"
                  >
                    <span>View in {item.linkView}</span>
                    <ExternalLink className="h-3 w-3" />
                  </button>
                )}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 p-3 text-[11px] text-slate-500">
          <span>Enterprise Real-time Stream</span>
          <span className="font-medium text-emerald-600">Synced</span>
        </div>
      </div>
    </div>
  );
}
