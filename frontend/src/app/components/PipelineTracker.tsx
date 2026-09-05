"use client";

import type { ReactNode } from "react";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";

// The canonical pipeline stages in order
export const PIPELINE_STAGES = [
  { key: "DETECTED", label: "Detected" },
  { key: "DIAGNOSED", label: "Diagnosed" },
  { key: "SCORED", label: "Scored" },
  { key: "DECISION_MADE", label: "Decided" },
  { key: "POLICY_GATE", label: "Policy Gate" },
  { key: "ACTION_EXECUTED", label: "Action Sent" },
  { key: "LINK_CLICKED", label: "Customer Response", altKeys: ["PLAN_VIEWED", "PLAN_ACCEPTED"] },
  { key: "PAYMENT_CAPTURED", label: "Captured" },
  { key: "REVENUE_RECOVERED", label: "Recovered" },
] as const;

type StageStatus = "done" | "active" | "blocked" | "pending";

interface PipelineStageProps {
  label: string;
  status: StageStatus;
  isLast: boolean;
}

function PipelineStage({ label, status, isLast }: PipelineStageProps) {
  const iconMap: Record<StageStatus, ReactNode> = {
    done: <CheckCircle2 size={16} className="text-accent-green" />,
    active: <Loader2 size={16} className="text-accent-blue animate-spin" />,
    blocked: <Circle size={16} className="text-accent-red fill-accent-red/20" />,
    pending: <Circle size={16} className="text-tertiary" />,
  };
  const labelColor: Record<StageStatus, string> = {
    done: "text-accent-green",
    active: "text-accent-blue",
    blocked: "text-accent-red",
    pending: "text-tertiary",
  };
  const connectorColor: Record<StageStatus, string> = {
    done: "bg-accent-green/30",
    active: "bg-accent-blue/30",
    blocked: "bg-accent-red/20",
    pending: "bg-border",
  };

  return (
    <div className="flex items-center">
      <div className="flex flex-col items-center gap-1.5">
        <div className="flex items-center justify-center w-7 h-7">
          {iconMap[status]}
        </div>
        <span className={`text-[9px] font-mono uppercase tracking-widest text-center w-16 leading-tight ${labelColor[status]}`}>
          {label}
        </span>
      </div>
      {!isLast && (
        <div className={`h-px w-8 sm:w-12 shrink-0 mx-1 mt-[-14px] ${connectorColor[status]}`} />
      )}
    </div>
  );
}

interface PipelineTrackerProps {
  /** Set of event_type strings that have been recorded for this case */
  observedEvents: Set<string>;
  /** Whether the action was policy-blocked */
  policyBlocked?: boolean;
}

export function PipelineTracker({ observedEvents, policyBlocked = false }: PipelineTrackerProps) {
  // Determine which stages are reached
  const reachedStages = new Set<string>();
  for (const s of PIPELINE_STAGES) {
    if (observedEvents.has(s.key)) {
      reachedStages.add(s.key);
    }
    // Check alternate keys
    if ("altKeys" in s && s.altKeys) {
      for (const alt of s.altKeys) {
        if (observedEvents.has(alt)) {
          reachedStages.add(s.key);
        }
      }
    }
  }

  // Determine the last reached index so we can mark "active" on the next
  let lastDoneIndex = -1;
  PIPELINE_STAGES.forEach((stage, idx) => {
    if (reachedStages.has(stage.key)) lastDoneIndex = idx;
  });

  return (
    <div className="flex flex-wrap gap-y-4 items-center py-2 overflow-x-auto">
      {PIPELINE_STAGES.map((stage, idx) => {
        let status: StageStatus = "pending";
        if (reachedStages.has(stage.key)) {
          status = "done";
        } else if (idx === lastDoneIndex + 1) {
          // The next expected stage
          if (policyBlocked && stage.key === "ACTION_EXECUTED") {
            status = "blocked";
          } else {
            status = "active";
          }
        }
        return (
          <PipelineStage
            key={stage.key}
            label={stage.label}
            status={status}
            isLast={idx === PIPELINE_STAGES.length - 1}
          />
        );
      })}
    </div>
  );
}
