import type { AuditEvent } from "../../types/api";
import { Card, formatTime, labelize } from "./ui";

const icons: Record<string, string> = { DETECTED: "◎", DIAGNOSED: "⌕", SCORED: "◈", CLAUDE_REASONING_RECEIVED: "✦", POLICY_GATE: "⊞", ACTION_EXECUTED: "✓", ACTION_STOPPED: "⊘", OUTCOME_TRACKED: "●" };

export function AuditTimeline({ events }: { events: AuditEvent[] }) {
  const chronological = [...events].sort((a, b) => (a.timestamp ?? "").localeCompare(b.timestamp ?? ""));
  return <Card className="p-6"><h2 className="text-lg font-semibold">Audit trail</h2><p className="mt-1 text-sm text-slate-400">Chronological evidence from the recovery pipeline.</p>{chronological.length ? <ol className="mt-6 space-y-0">{chronological.map((event, index) => <li className="relative flex gap-4 pb-6 last:pb-0" key={`${event.event_type}-${event.timestamp}-${index}`}><div className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-cyan-400/30 bg-cyan-400/10 text-sm text-cyan-300">{icons[event.event_type] ?? "•"}</div>{index < chronological.length - 1 && <span className="absolute left-4 top-8 h-[calc(100%-1.25rem)] border-l border-slate-700" />}<div className="min-w-0 flex-1 rounded-xl border border-slate-800 bg-slate-950/40 p-4"><div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between"><p className="font-semibold text-slate-100">{labelize(event.event_type)}</p><time className="text-xs text-slate-400">{formatTime(event.timestamp)}</time></div><pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words text-xs leading-5 text-slate-300">{JSON.stringify(event.data, null, 2)}</pre></div></li>)}</ol> : <p className="mt-6 text-sm text-slate-400">No audit events are available for this case.</p>}</Card>;
}
