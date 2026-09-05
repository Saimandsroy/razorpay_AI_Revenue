"use client";
export default function StatusPage() {
  return (
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
      <div className="mb-8 border-b border-border pb-6">
        <div className="text-[10px] font-mono uppercase tracking-widest text-tertiary mb-1">System</div>
        <h1 className="text-2xl font-semibold text-primary">System Status</h1>
        <p className="text-xs text-secondary mt-1">Backend health and pipeline configuration.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: "Backend API", status: "Operational", href: "http://localhost:8000/health" },
          { label: "Razorpay Test Mode", status: "Connected", href: null },
          { label: "Recovery Pipeline", status: "Active", href: null },
        ].map(({ label, status }) => (
          <div key={label} className="border border-border bg-surface rounded-sm p-6">
            <div className="flex items-center gap-2 mb-2">
              <div className="h-2 w-2 rounded-full bg-accent-green"></div>
              <span className="text-[10px] font-mono uppercase tracking-widest text-tertiary">{status}</span>
            </div>
            <p className="text-sm font-semibold text-primary">{label}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
