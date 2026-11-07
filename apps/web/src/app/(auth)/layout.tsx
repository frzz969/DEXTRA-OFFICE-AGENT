export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen bg-[#F8FAFC] flex flex-col items-center justify-center px-4 py-12 overflow-hidden">
      {/* Subtle indigo atmosphere */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute -top-48 left-1/2 -translate-x-1/2 h-[520px] w-[520px] rounded-full bg-indigo-500/10 blur-3xl" />
        <div className="absolute -bottom-24 -right-16 h-80 w-80 rounded-full bg-indigo-400/10 blur-3xl" />
        <div
          className="absolute inset-0 opacity-40"
          style={{
            backgroundImage: 'radial-gradient(#c7d2fe 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />
      </div>

      <div className="relative w-full max-w-md">
        {/* Brand mark */}
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center text-sm font-extrabold tracking-tight shadow-lg shadow-indigo-600/25">
            DX
          </div>
          <span className="text-lg font-extrabold tracking-[0.22em] text-slate-900">DEXTRA</span>
        </div>

        {children}

        <p className="mt-8 text-center text-[11px] leading-relaxed text-slate-400">
          Governed enterprise AI workforce. Autonomous execution, human accountability.
        </p>
      </div>
    </div>
  );
}
