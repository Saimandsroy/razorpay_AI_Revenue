"use client";
export default function ReviewPage() {
  return (
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
      <div className="mb-8 border-b border-border pb-6">
        <div className="text-[10px] font-mono uppercase tracking-widest text-tertiary mb-1">Recovery</div>
        <h1 className="text-2xl font-semibold text-primary">Human Review Queue</h1>
        <p className="text-xs text-secondary mt-1">Cases flagged for manual intervention by the policy engine.</p>
      </div>
      <div className="border border-border bg-surface rounded-sm p-12 text-center">
        <p className="text-secondary text-sm">Human Review queue will surface cases where the AI confidence is low or policy blocks are triggered. Connect to backend endpoint when available.</p>
      </div>
    </main>
  );
}
