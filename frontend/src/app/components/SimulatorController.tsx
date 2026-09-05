"use client";

import { useState } from "react";
import { advanceSimulatorBatch, simulateCustomerResponses, simulateRecoveries } from "../../lib/api";
import { Play, ActivitySquare, CheckCircle } from "lucide-react";
import { Card } from "./ui";

interface SimulatorControllerProps {
  batchId: string;
  onUpdate: () => void;
  status: string;
}

export function SimulatorController({ batchId, onUpdate, status }: SimulatorControllerProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleStep = async (step: string, apiCall: () => Promise<any>) => {
    setLoading(step);
    setError(null);
    try {
      await apiCall();
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(null);
    }
  };

  return (
    <Card className="p-5 mb-6 border-accent-blue/30 bg-accent-blue/5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold tracking-wider text-accent-blue uppercase mb-1">
            TEST MODE: Simulator Controller
          </h2>
          <p className="text-xs text-secondary">
            Step through the AI recovery lifecycle for batch <span className="font-mono text-tertiary">{batchId.split("-")[0]}</span>
          </p>
          {error && <p className="text-xs text-accent-red mt-2">{error}</p>}
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => handleStep("advance", () => advanceSimulatorBatch(batchId))}
            disabled={loading !== null || status === "complete"}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-md bg-surface border border-border hover:border-accent-blue hover:text-accent-blue transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading === "advance" ? <span className="animate-spin text-tertiary">↻</span> : <Play size={14} />}
            1. Advance Cases
          </button>

          <button
            onClick={() => handleStep("responses", () => simulateCustomerResponses(batchId))}
            disabled={loading !== null || status === "complete"}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-md bg-surface border border-border hover:border-accent-amber hover:text-accent-amber transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading === "responses" ? <span className="animate-spin text-tertiary">↻</span> : <ActivitySquare size={14} />}
            2. Simulate Responses
          </button>

          <button
            onClick={() => handleStep("recoveries", () => simulateRecoveries(batchId))}
            disabled={loading !== null || status === "complete"}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-md bg-surface border border-border hover:border-accent-green hover:text-accent-green transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading === "recoveries" ? <span className="animate-spin text-tertiary">↻</span> : <CheckCircle size={14} />}
            3. Capture Revenue
          </button>
        </div>
      </div>
    </Card>
  );
}
