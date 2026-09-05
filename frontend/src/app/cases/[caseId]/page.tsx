"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ChevronLeft, AlertCircle, ShieldCheck, ShieldX, Zap, CheckCircle2, FlaskConical } from "lucide-react";
import { fetchCaseAudit, fetchCaseJourney } from "../../../lib/api";
import type { AuditEvent, CustomerJourney } from "../../../types/api";
import { AuditTimeline } from "../../components/AuditTimeline";
import { PipelineTracker } from "../../components/PipelineTracker";
import { Card, StatusBadge, formatTime, labelize, money } from "../../components/ui";

const statusStyles: Record<string, string> = {
  completed: "border-accent-green/30 bg-accent-green/10 text-accent-green",
  failed: "border-accent-red/30 bg-accent-red/10 text-accent-red",
  clicked: "border-accent-amber/30 bg-accent-amber/10 text-accent-amber",
  accepted: "border-accent-amber/30 bg-accent-amber/10 text-accent-amber",
  sent: "border-accent-blue/30 bg-accent-blue/10 text-accent-blue",
  delivered: "border-accent-blue/30 bg-accent-blue/10 text-accent-blue",
  proposed: "border-border bg-background text-secondary",
  stopped: "border-accent-red/30 bg-accent-red/10 text-accent-red",
  cancelled: "border-accent-red/30 bg-accent-red/10 text-accent-red",
};

function Field({ label, value, mono = false }: { label: string; value: string | React.ReactNode; mono?: boolean }) {
  return (
    <div>
      <dt className="text-[10px] font-mono uppercase tracking-widest text-tertiary mb-1">{label}</dt>
      <dd className={`text-sm font-medium text-primary ${mono ? "font-mono" : ""}`}>{value}</dd>
    </div>
  );
}

export default function CaseDetailPage({ params }: { params: { caseId: string } }) {
  const [journey, setJourney] = useState<CustomerJourney | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [journeyData, auditData] = await Promise.all([
        fetchCaseJourney(params.caseId),
        fetchCaseAudit(params.caseId),
      ]);
      setJourney(journeyData);
      setAudit(auditData);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load case details.");
    } finally { setLoading(false); }
  }, [params.caseId]);

  useEffect(() => { void load(); }, [load]);

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
        <div className="flex items-center gap-2 mb-8">
          <div className="h-4 w-24 animate-pulse rounded bg-border" />
        </div>
        <div className="h-28 animate-pulse rounded bg-surface border border-border mb-6" />
        <div className="grid gap-6 xl:grid-cols-2">
          <div className="space-y-6">
            {[...Array(3)].map((_, i) => <div key={i} className="h-40 animate-pulse rounded bg-surface border border-border" />)}
          </div>
          <div className="h-full animate-pulse rounded bg-surface border border-border" />
        </div>
      </main>
    );
  }

  if (error || !journey) {
    return (
      <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
        <Card className="p-6 border-accent-red/30">
          <div className="flex items-center gap-3 mb-3">
            <AlertCircle size={18} className="text-accent-red" />
            <h1 className="font-semibold text-primary">Case Not Found</h1>
          </div>
          <p className="text-sm text-secondary">{error ?? "The case could not be found."}</p>
          <Link href="/dashboard" className="mt-4 inline-flex items-center gap-1 text-sm text-accent-blue hover:text-primary transition">
            <ChevronLeft size={14} /> Back to Dashboard
          </Link>
        </Card>
      </main>
    );
  }

  const c = journey.case;
  const scorePercent = c.recovery_score != null ? `${(c.recovery_score * 100).toFixed(0)}%` : "—";
  const statusVariant = c.status === "allowed" || c.status === "success" ? "success" : c.status === "stopped" || c.status === "failed" ? "danger" : "default";
  const outcomeVariant = c.outcome_status === "success" ? "success" : c.outcome_status === "failed" ? "danger" : "default";

  // Build observed events set from timeline for pipeline tracker
  const observedEvents = new Set(journey.timeline.map(e => e.event_type));

  // Check if it's a simulated/test batch (audit events with source=simulation)
  const isSimulation = audit.some(e => (e.data as any)?.source === "simulation");

  return (
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
      {/* Breadcrumb */}
      <Link href="/dashboard" className="inline-flex items-center gap-1 text-xs text-secondary hover:text-primary transition mb-6">
        <ChevronLeft size={14} /> Command Center
      </Link>

      {/* Header */}
      <header className="mb-6 border-b border-border pb-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="text-[10px] font-mono uppercase tracking-widest text-tertiary">Customer Recovery Journey</div>
              {isSimulation && (
                <span className="inline-flex items-center gap-1 rounded-sm border border-accent-amber/30 bg-accent-amber/10 px-2 py-0.5 text-[9px] font-mono uppercase tracking-wider text-accent-amber">
                  <FlaskConical size={10} /> Simulation
                </span>
              )}
            </div>
            <h1 className="text-2xl font-semibold text-primary">{c.customer_name ?? "Unknown Customer"}</h1>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2">
              <code className="text-xs font-mono text-tertiary">{c.payment_id}</code>
              <span className="text-tertiary">·</span>
              <code className="text-xs font-mono text-tertiary">{c.id}</code>
            </div>
          </div>
          <div className="flex gap-2">
            <StatusBadge value={c.status} variant={statusVariant} />
            <StatusBadge value={c.outcome_status} variant={outcomeVariant} />
          </div>
        </div>

        {/* Pipeline Tracker — the hero element */}
        <div className="mt-6 p-4 bg-background border border-border rounded-sm">
          <div className="text-[9px] font-mono uppercase tracking-widest text-tertiary mb-3">Recovery Pipeline Progress</div>
          <PipelineTracker
            observedEvents={observedEvents}
            policyBlocked={c.policy_allowed === false}
          />
          {c.policy_allowed === false && (
            <div className="mt-3 flex items-center gap-2 text-xs text-accent-amber">
              <ShieldX size={13} />
              Policy gate prevented automated action — requires human review.
            </div>
          )}
        </div>
      </header>

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        {/* Left Column */}
        <div className="space-y-5">

          {/* Revenue Summary */}
          <div className="grid grid-cols-2 gap-4">
            <div className="border border-border bg-surface p-4 rounded-sm">
              <p className="text-[9px] font-mono uppercase tracking-widest text-tertiary mb-1">Revenue at Risk</p>
              <p className="text-2xl font-semibold text-primary">{money(journey.revenue.at_risk_paise)}</p>
            </div>
            <div className={`border p-4 rounded-sm ${journey.revenue.recovered_paise > 0 ? "border-accent-green/30 bg-accent-green/5" : "border-border bg-surface"}`}>
              <p className="text-[9px] font-mono uppercase tracking-widest text-tertiary mb-1">Revenue Recovered</p>
              <p className={`text-2xl font-semibold ${journey.revenue.recovered_paise > 0 ? "text-accent-green" : "text-secondary"}`}>
                {money(journey.revenue.recovered_paise)}
              </p>
              {isSimulation && journey.revenue.recovered_paise > 0 && (
                <p className="text-[9px] font-mono text-accent-amber mt-1">TEST MODE — not production revenue</p>
              )}
            </div>
          </div>

          {/* Case Information */}
          <Card>
            <h2 className="text-[10px] font-mono uppercase tracking-widest text-tertiary mb-4">Payment Context</h2>
            <dl className="grid gap-4 sm:grid-cols-2">
              <Field label="Payment ID" value={c.payment_id} mono />
              <Field label="Customer" value={c.customer_name ?? "—"} />
              <Field label="Amount" value={money(c.amount_paise)} />
              <Field label="Customer ID" value={c.customer_id ?? "—"} mono />
            </dl>
          </Card>

          {/* AI Intelligence */}
          <Card>
            <h2 className="text-[10px] font-mono uppercase tracking-widest text-tertiary mb-4">AI Intelligence Output</h2>
            <dl className="grid gap-4 sm:grid-cols-2">
              <Field label="Root Cause Diagnosis" value={<StatusBadge value={c.diagnosis} variant="warning" />} />
              <Field label="Recovery Probability" value={scorePercent} />
              <Field label="Recommended Action" value={c.recommended_action ? labelize(c.recommended_action) : "—"} />
              <Field label="Outcome Status" value={labelize(c.outcome_status)} />
            </dl>
          </Card>

          {/* Policy Decision */}
          <Card>
            <h2 className="text-[10px] font-mono uppercase tracking-widest text-tertiary mb-4">Policy Guardrail Decision</h2>
            <div className={`flex items-start gap-3 mb-4 p-3 rounded-sm border ${c.policy_allowed ? "border-accent-green/30 bg-accent-green/5" : "border-accent-red/30 bg-accent-red/5"}`}>
              {c.policy_allowed ? (
                <ShieldCheck size={18} className="text-accent-green shrink-0 mt-0.5" />
              ) : (
                <ShieldX size={18} className="text-accent-red shrink-0 mt-0.5" />
              )}
              <div>
                <p className="text-sm font-semibold text-primary">{c.policy_allowed ? "Policy Approved" : "Policy Blocked"}</p>
                <p className="text-xs text-secondary mt-0.5">{c.policy_reason ?? "—"}</p>
              </div>
            </div>
          </Card>

          {/* Recovery Actions */}
          <Card noPadding className="overflow-hidden">
            <div className="border-b border-border px-6 py-4 flex items-center justify-between">
              <div>
                <h2 className="text-[10px] font-mono uppercase tracking-widest text-tertiary">Recovery Actions</h2>
                <p className="text-xs text-tertiary mt-0.5">{journey.actions.length} action{journey.actions.length !== 1 ? "s" : ""} executed</p>
              </div>
              {journey.actions.length > 0 && (
                <div className="text-xs font-mono text-tertiary">
                  {journey.actions.filter(a => a.status === "completed").length}/{journey.actions.length} completed
                </div>
              )}
            </div>
            {journey.actions.length > 0 ? (
              <div className="divide-y divide-border">
                {journey.actions.map((action) => (
                  <div key={action.id} className="p-6">
                    <div className="flex items-start justify-between gap-4 mb-4">
                      <div className="flex items-center gap-3">
                        <Zap size={16} className="text-accent-blue shrink-0" />
                        <div>
                          <p className="text-sm font-semibold text-primary">{labelize(action.action_type)}</p>
                          <p className="text-[11px] text-tertiary font-mono mt-0.5">via {labelize(action.channel)} · {action.id.split("-")[0]}</p>
                        </div>
                      </div>
                      <span className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider ${statusStyles[action.status] ?? statusStyles.proposed}`}>
                        {action.status}
                      </span>
                    </div>
                    <dl className="grid grid-cols-2 gap-3 text-xs mb-3">
                      <Field label="Recipient" value={action.recipient ?? "—"} />
                      <Field label="Provider Ref" value={action.provider_reference ?? "—"} mono />
                      <Field label="Sent" value={formatTime(action.sent_at)} />
                      <Field label="Response" value={action.clicked_at ? formatTime(action.clicked_at) : action.responded_at ? formatTime(action.responded_at) : "—"} />
                    </dl>
                    {action.action_url && (
                      <a href={action.action_url} target="_blank" rel="noopener noreferrer" className="text-xs text-accent-blue hover:text-primary break-all transition">
                        {action.action_url}
                      </a>
                    )}
                    {action.revenue_recovered_paise > 0 && (
                      <div className="mt-3 flex items-center gap-2 text-sm font-semibold text-accent-green">
                        <CheckCircle2 size={14} />
                        Revenue recovered: {money(action.revenue_recovered_paise)}
                        {isSimulation && <span className="text-[10px] font-mono text-accent-amber font-normal">(simulation)</span>}
                      </div>
                    )}
                    {action.failure_reason && (
                      <p className="mt-2 text-xs text-accent-red">Failure: {action.failure_reason}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="px-6 py-8 text-sm text-tertiary">No recovery actions were executed for this case.</p>
            )}
          </Card>
        </div>

        {/* Right Column: Timeline + Audit */}
        <div className="space-y-5">
          {/* Journey Timeline */}
          <Card>
            <h2 className="text-[10px] font-mono uppercase tracking-widest text-tertiary mb-1">Event Timeline</h2>
            <p className="text-xs text-tertiary mb-5">Chronological pipeline events for this case.</p>
            {journey.timeline.length > 0 ? (
              <ol className="space-y-0">
                {journey.timeline.map((event, index) => {
                  const isTerminal = event.event_type === "REVENUE_RECOVERED" || event.event_type === "PAYMENT_CAPTURED";
                  const isError = event.event_type === "ACTION_STOPPED";
                  return (
                    <li className="relative flex gap-4 pb-5 last:pb-0" key={`${event.event_type}-${index}`}>
                      {index < journey.timeline.length - 1 && (
                        <span className="absolute left-3.5 top-7 h-[calc(100%-1.5rem)] border-l border-border" />
                      )}
                      <div className={`relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-sm border text-[10px] ${
                        isTerminal ? "border-accent-green/40 bg-accent-green/10 text-accent-green" :
                        isError ? "border-accent-red/40 bg-accent-red/10 text-accent-red" :
                        "border-accent-blue/30 bg-accent-blue/5 text-accent-blue"
                      }`}>
                        {index + 1}
                      </div>
                      <div className="min-w-0 flex-1 border border-border bg-background rounded-sm p-3">
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <p className={`text-[10px] font-semibold font-mono uppercase tracking-widest ${
                            isTerminal ? "text-accent-green" : isError ? "text-accent-red" : "text-primary"
                          }`}>{event.event_type}</p>
                          <time className="text-[9px] font-mono text-tertiary shrink-0">{formatTime(event.timestamp)}</time>
                        </div>
                        <p className="text-[11px] text-secondary leading-relaxed">{event.message}</p>
                      </div>
                    </li>
                  );
                })}
              </ol>
            ) : (
              <p className="text-xs text-tertiary font-mono">NO TIMELINE EVENTS</p>
            )}
          </Card>

          {/* Audit Trail */}
          <AuditTimeline events={audit} />
        </div>
      </div>
    </main>
  );
}
