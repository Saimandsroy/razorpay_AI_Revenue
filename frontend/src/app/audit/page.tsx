"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { RefreshCw, Activity } from "lucide-react";
import { fetchGlobalAudit } from "../../lib/api";
import type { GlobalAuditEvent } from "../../types/api";
import { Skeleton, formatTime } from "../components/ui";

const EVENT_COLORS: Record<string, { icon: string; dot: string; label: string }> = {
  DETECTED:                 { icon: "◎", dot: "bg-accent-blue",  label: "text-accent-blue" },
  DIAGNOSED:                { icon: "⌕", dot: "bg-accent-amber", label: "text-accent-amber" },
  CONTEXT_FETCHED:          { icon: "◈", dot: "bg-secondary",    label: "text-secondary" },
  SYNTHETIC_DEMO_CONTEXT:   { icon: "⚑", dot: "bg-accent-amber", label: "text-accent-amber" },
  SCORED:                   { icon: "◈", dot: "bg-secondary",    label: "text-secondary" },
  RISK_ASSESSED:            { icon: "△", dot: "bg-accent-amber", label: "text-accent-amber" },
  DECISION_MADE:            { icon: "▷", dot: "bg-accent-blue",  label: "text-accent-blue" },
  GEMINI_REASONING_RECEIVED:{ icon: "✦", dot: "bg-accent-blue",  label: "text-accent-blue" },
  POLICY_GATE:              { icon: "⊞", dot: "bg-accent-amber", label: "text-accent-amber" },
  ACTION_EXECUTED:          { icon: "✓", dot: "bg-accent-green", label: "text-accent-green" },
  ACTION_STOPPED:           { icon: "⊘", dot: "bg-accent-red",   label: "text-accent-red" },
  OUTCOME_TRACKED:          { icon: "●", dot: "bg-accent-green", label: "text-accent-green" },
};

const ALL_EVENT_TYPES = Object.keys(EVENT_COLORS);

function EventRow({ event }: { event: GlobalAuditEvent }) {
  const style = EVENT_COLORS[event.event_type];
  const dot = style?.dot ?? "bg-tertiary";
  const label = style?.label ?? "text-secondary";
  const icon = style?.icon ?? "·";

  return (
    <div className="flex items-start gap-4 border-b border-border/50 px-6 py-4 hover:bg-surfaceHover transition group">
      {/* Status dot */}
      <div className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center">
        <div className={`h-2 w-2 rounded-full ${dot}`} />
      </div>

      {/* Timestamp */}
      <div className="w-36 shrink-0">
        <time className="text-[10px] font-mono text-tertiary">{formatTime(event.timestamp)}</time>
      </div>

      {/* Event type */}
      <div className="w-60 shrink-0">
        <span className={`font-mono text-[11px] uppercase tracking-widest ${label}`}>
          {icon} {event.event_type}
        </span>
      </div>

      {/* Case context */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Link
            href={`/cases/${event.case_id}`}
            className="font-medium text-primary text-sm hover:text-accent-blue transition"
          >
            {event.customer ?? "Unknown customer"}
          </Link>
          <span className="text-tertiary text-xs">·</span>
          <code className="text-[10px] font-mono text-tertiary">{event.payment_id}</code>
          <span className="text-tertiary text-xs">·</span>
          <code className="text-[10px] font-mono text-tertiary">{event.case_id.split("-")[0]}</code>
        </div>
        {/* Inline data preview */}
        <p className="mt-0.5 text-[11px] font-mono text-tertiary line-clamp-1">
          {JSON.stringify(event.data)}
        </p>
      </div>
    </div>
  );
}

export default function AuditPage() {
  const [events, setEvents] = useState<GlobalAuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [eventTypeFilter, setEventTypeFilter] = useState<string>("");
  const [limit, setLimit] = useState(100);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await fetchGlobalAudit(limit, eventTypeFilter || undefined);
      setEvents(data);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load audit events.");
    } finally { setLoading(false); }
  }, [limit, eventTypeFilter]);

  useEffect(() => { void load(); }, [load]);

  // Live polling
  useEffect(() => {
    const interval = window.setInterval(() => { void load(); }, 10_000);
    return () => window.clearInterval(interval);
  }, [load]);

  return (
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
      <header className="mb-8 flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-tertiary mb-1">System</div>
          <h1 className="text-2xl font-semibold text-primary">Audit Logs</h1>
          <p className="text-xs text-secondary mt-1">
            Live event stream from the recovery pipeline. Polling every 10 seconds.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-accent-green animate-pulse" />
            <span className="text-[10px] font-mono text-tertiary">LIVE</span>
          </div>
          <button
            onClick={() => void load()}
            className="flex items-center gap-2 rounded-sm border border-border bg-background px-4 py-2 text-xs font-semibold text-secondary hover:text-primary transition"
          >
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </header>

      {/* Controls */}
      <div className="mb-4 flex flex-wrap gap-3 items-center justify-between">
        {/* Event type filter pills */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setEventTypeFilter("")}
            className={`rounded-sm border px-3 py-1 text-[10px] font-mono uppercase tracking-widest transition ${
              !eventTypeFilter ? "border-accent-blue bg-accent-blue/10 text-accent-blue" : "border-border text-tertiary hover:text-secondary"
            }`}
          >
            All
          </button>
          {ALL_EVENT_TYPES.map(t => (
            <button
              key={t}
              onClick={() => setEventTypeFilter(eventTypeFilter === t ? "" : t)}
              className={`rounded-sm border px-3 py-1 text-[10px] font-mono uppercase tracking-widest transition ${
                eventTypeFilter === t ? "border-accent-blue bg-accent-blue/10 text-accent-blue" : "border-border text-tertiary hover:text-secondary"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Limit control */}
        <div className="flex items-center gap-2">
          <label className="text-[10px] font-mono uppercase tracking-widest text-tertiary">Show</label>
          {[50, 100, 200].map(n => (
            <button
              key={n}
              onClick={() => setLimit(n)}
              className={`rounded-sm border px-2 py-1 text-[10px] font-mono transition ${
                limit === n ? "border-accent-blue text-accent-blue" : "border-border text-tertiary hover:text-secondary"
              }`}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      {/* Count */}
      {!loading && (
        <div className="mb-2 text-[10px] font-mono text-tertiary px-1">
          {events.length} event{events.length !== 1 ? "s" : ""} {eventTypeFilter ? `· ${eventTypeFilter}` : ""}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-4 border border-accent-red/30 bg-accent-red/5 rounded-sm px-6 py-3 text-sm text-accent-red">
          {error}
        </div>
      )}

      {/* Stream */}
      <div className="border border-border bg-surface rounded-sm overflow-hidden">
        {/* Table header */}
        <div className="flex items-center gap-4 border-b border-border bg-background px-6 py-3">
          <div className="w-6 shrink-0" />
          <div className="w-36 shrink-0">
            <span className="text-[10px] font-mono uppercase tracking-widest text-tertiary">Timestamp</span>
          </div>
          <div className="w-60 shrink-0">
            <span className="text-[10px] font-mono uppercase tracking-widest text-tertiary">Event</span>
          </div>
          <div className="flex-1">
            <span className="text-[10px] font-mono uppercase tracking-widest text-tertiary">Context</span>
          </div>
        </div>

        {loading ? (
          Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 border-b border-border/50 px-6 py-4">
              <Skeleton className="h-3 w-3 rounded-full shrink-0" />
              <Skeleton className="h-3 w-36 shrink-0" />
              <Skeleton className="h-3 w-48" />
              <Skeleton className="h-3 flex-1" />
            </div>
          ))
        ) : events.length > 0 ? (
          events.map(event => <EventRow key={event.id} event={event} />)
        ) : (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <Activity size={32} className="text-border" />
            <p className="text-sm text-tertiary">No audit events yet. Start a batch or process a payment to see the pipeline in action.</p>
          </div>
        )}
      </div>
    </main>
  );
}
