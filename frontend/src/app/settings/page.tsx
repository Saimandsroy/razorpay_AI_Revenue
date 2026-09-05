"use client";
export default function SettingsPage() {
  return (
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
      <div className="mb-8 border-b border-border pb-6">
        <div className="text-[10px] font-mono uppercase tracking-widest text-tertiary mb-1">System</div>
        <h1 className="text-2xl font-semibold text-primary">Settings</h1>
        <p className="text-xs text-secondary mt-1">Application configuration and environment settings.</p>
      </div>
      <div className="border border-border bg-surface rounded-sm p-12 text-center">
        <p className="text-secondary text-sm">Settings will be added as the product evolves. Environment is currently configured via backend <code className="font-mono text-xs">.env</code>.</p>
      </div>
    </main>
  );
}
