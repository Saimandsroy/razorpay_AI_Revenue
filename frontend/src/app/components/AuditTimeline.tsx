import type { AuditEvent } from "../../types/api";
import { Card, formatTime } from "./ui";

const EVENT_ICONS: Record<string, string> = {
  DETECTED: "◎",
  DIAGNOSED: "⌕",
  CONTEXT_FETCHED: "◈",
  SYNTHETIC_DEMO_CONTEXT: "⚑",
  SCORED: "◈",
  GEMINI_REASONING_RECEIVED: "✦",
  POLICY_GATE: "⊞",
  ACTION_EXECUTED: "✓",
  ACTION_STOPPED: "⊘",
  OUTCOME_TRACKED: "●",
  RISK_ASSESSED: "△",
  DECISION_MADE: "▷",
};

const EVENT_COLORS: Record<string, string> = {
  DETECTED: "text-accent-blue border-accent-blue/30 bg-accent-blue/10",
  DIAGNOSED: "text-accent-amber border-accent-amber/30 bg-accent-amber/10",
  CONTEXT_FETCHED: "text-secondary border-border bg-surface",
  SYNTHETIC_DEMO_CONTEXT: "text-accent-amber border-accent-amber/30 bg-accent-amber/10",
  GEMINI_REASONING_RECEIVED: "text-accent-blue border-accent-blue/30 bg-accent-blue/10",
  POLICY_GATE: "text-accent-amber border-accent-amber/30 bg-accent-amber/10",
  ACTION_EXECUTED: "text-accent-green border-accent-green/30 bg-accent-green/10",
  ACTION_STOPPED: "text-accent-red border-accent-red/30 bg-accent-red/10",
  OUTCOME_TRACKED: "text-accent-green border-accent-green/30 bg-accent-green/10",
};

export function AuditTimeline({ events }: { events: AuditEvent[] }) {
  const chronological = [...events].sort((a, b) => (a.timestamp ?? "").localeCompare(b.timestamp ?? ""));

  return (
    <Card className="h-full">
      <h2 className="text-xs font-semibold uppercase tracking-widest text-primary mb-1">Audit Trail</h2>
      <p className="text-xs text-tertiary mb-6">Chronological evidence from the recovery pipeline.</p>

      {chronological.length ? (
        <ol className="space-y-0">
          {chronological.map((event, index) => {
            const colorClass = EVENT_COLORS[event.event_type] ?? "text-secondary border-border bg-surface";
            return (
              <li className="relative flex gap-4 pb-5 last:pb-0" key={`${event.event_type}-${event.timestamp}-${index}`}>
                {/* Line */}
                {index < chronological.length - 1 && (
                  <span className="absolute left-4 top-8 h-[calc(100%-1.5rem)] border-l border-border" />
                )}
                {/* Icon */}
                <div className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-sm border text-xs ${colorClass}`}>
                  {EVENT_ICONS[event.event_type] ?? "•"}
                </div>
                {/* Content */}
                <div className="min-w-0 flex-1 border border-border bg-background rounded-sm p-4">
                  <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between mb-2">
                    <p className="text-xs font-semibold font-mono uppercase tracking-widest text-primary">
                      {event.event_type}
                    </p>
                    <time className="text-[10px] font-mono text-tertiary">{formatTime(event.timestamp)}</time>
                  </div>
                  <pre className="overflow-x-auto whitespace-pre-wrap break-words text-[11px] leading-5 text-secondary font-mono">
                    {JSON.stringify(event.data, null, 2)}
                  </pre>
                </div>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="text-sm text-tertiary font-mono">NO AUDIT EVENTS AVAILABLE</p>
      )}
    </Card>
  );
}
