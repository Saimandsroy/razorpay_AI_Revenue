const phases = [
  "Detect failed payments", "Diagnose the root cause", "Score recovery likelihood",
  "Recommend an action", "Enforce policy", "Track outcomes",
];

export default function DashboardPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">Razorpay · Test Mode</p>
      <h1 className="mt-3 text-4xl font-bold">AI Revenue Recovery</h1>
      <p className="mt-4 max-w-2xl text-slate-300">The dashboard foundation is ready. Phase 2 will connect live test-mode payment failures and begin the recovery workflow.</p>
      <section className="mt-10 grid gap-4 sm:grid-cols-3">
        {[["Revenue at risk", "—"], ["Recovered", "—"], ["Active cases", "0"]].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-700 bg-slate-900 p-5"><p className="text-sm text-slate-400">{label}</p><p className="mt-2 text-3xl font-semibold">{value}</p></div>
        ))}
      </section>
      <section className="mt-8 rounded-xl border border-slate-700 bg-slate-900 p-6">
        <h2 className="text-lg font-semibold">Recovery pipeline</h2>
        <ol className="mt-4 grid gap-3 sm:grid-cols-2">{phases.map((phase, index) => <li key={phase} className="rounded-lg bg-slate-800 p-3 text-slate-200"><span className="mr-3 text-cyan-300">{index + 1}</span>{phase}</li>)}</ol>
      </section>
    </main>
  );
}
