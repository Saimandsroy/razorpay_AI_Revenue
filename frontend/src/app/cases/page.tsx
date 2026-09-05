"use client";

import { useCallback, useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { RefreshCw, Search, Filter, ArrowRight, FlaskConical } from "lucide-react";
import { fetchBatchCases, fetchLiveSession } from "../../lib/api";
import type { CaseListItem } from "../../types/api";
import { Card, Skeleton, StatusBadge, labelize, money } from "../components/ui";

const DIAGNOSIS_COLORS: Record<string, string> = {
  card_expired: "border-accent-amber/30 bg-accent-amber/10 text-accent-amber",
  insufficient_funds: "border-accent-red/30 bg-accent-red/10 text-accent-red",
  mandate_rejected: "border-accent-blue/30 bg-accent-blue/10 text-accent-blue",
  authentication_failed: "border-accent-red/30 bg-accent-red/10 text-accent-red",
  unknown_failure: "border-border bg-background text-tertiary",
};

function CasesContent() {
  const searchParams = useSearchParams();
  const urlBatchId = searchParams.get("batchId");

  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [diagnosisFilter, setDiagnosisFilter] = useState("");
  const [batchId, setBatchId] = useState<string | null>(urlBatchId);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      let resolvedBatchId = urlBatchId;
      if (!resolvedBatchId) {
        const session = await fetchLiveSession();
        resolvedBatchId = session.batch_id;
      }
      setBatchId(resolvedBatchId);
      const data = await fetchBatchCases(resolvedBatchId);
      setCases(data);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load cases.");
    } finally { setLoading(false); }
  }, [urlBatchId]);

  useEffect(() => { void load(); }, [load]);

  const diagnoses = Array.from(new Set(cases.map(c => c.diagnosis))).filter(Boolean);

  const filtered = cases.filter(c => {
    const matchesSearch = !search ||
      (c.customer?.toLowerCase().includes(search.toLowerCase())) ||
      c.case_id.includes(search) ||
      c.diagnosis.includes(search);
    const matchesDiagnosis = !diagnosisFilter || c.diagnosis === diagnosisFilter;
    return matchesSearch && matchesDiagnosis;
  });

  const totalRisk = filtered.reduce((s, c) => s + c.amount_paise, 0);
  const totalRecovered = filtered.reduce((s, c) => s + c.recovered_amount_paise, 0);

  return (
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
      <header className="mb-8 flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-tertiary mb-1">Recovery</div>
          <h1 className="text-2xl font-semibold text-primary">Recovery Cases</h1>
          <p className="text-xs text-secondary mt-1">AI-processed payment failure events and their recovery state.</p>
          {batchId && (
            <p className="text-[10px] font-mono text-tertiary mt-2">
              Batch: <span className="text-secondary">{batchId.split("-")[0]}</span>
            </p>
          )}
        </div>
        <button onClick={() => void load()} className="flex items-center gap-2 rounded-sm border border-border bg-background px-4 py-2 text-xs font-semibold text-secondary hover:text-primary transition">
          <RefreshCw size={13} /> Refresh
        </button>
      </header>

      {/* Aggregate strip */}
      {!loading && cases.length > 0 && (
        <div className="mb-5 grid grid-cols-3 gap-4 sm:grid-cols-5">
          {[
            { label: "Cases", value: filtered.length.toString() },
            { label: "Allowed", value: filtered.filter(c => c.status === "allowed" || c.status === "success").length.toString(), color: "text-accent-green" },
            { label: "Stopped", value: filtered.filter(c => c.status === "stopped").length.toString(), color: "text-accent-red" },
            { label: "Revenue at Risk", value: money(totalRisk) },
            { label: "Recovered", value: money(totalRecovered), color: totalRecovered > 0 ? "text-accent-green" : "text-secondary" },
          ].map(({ label, value, color }) => (
            <div key={label} className="border border-border bg-surface rounded-sm p-4">
              <p className="text-[9px] font-mono uppercase tracking-widest text-tertiary">{label}</p>
              <p className={`text-xl font-semibold mt-1 ${color ?? "text-primary"}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-tertiary" />
          <input
            type="text"
            placeholder="Search by customer, ID, or diagnosis…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-sm border border-border bg-surface pl-9 pr-4 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent-blue"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter size={13} className="text-tertiary shrink-0" />
          <select
            value={diagnosisFilter}
            onChange={(e) => setDiagnosisFilter(e.target.value)}
            className="rounded-sm border border-border bg-surface px-3 py-2 text-xs text-primary focus:outline-none focus:ring-1 focus:ring-accent-blue"
          >
            <option value="">All Diagnoses</option>
            {diagnoses.map(d => (
              <option key={d} value={d}>{labelize(d)}</option>
            ))}
          </select>
        </div>
      </div>

      <Card noPadding className="overflow-hidden">
        {error && (
          <div className="border-b border-accent-red/30 bg-accent-red/5 px-6 py-3 text-sm text-accent-red">{error}</div>
        )}
        <div className="overflow-x-auto">
          <table className="min-w-[1100px] w-full text-left text-sm">
            <thead className="bg-background text-[9px] uppercase tracking-widest text-secondary border-b border-border">
              <tr>
                <th className="px-5 py-4 font-semibold">Customer</th>
                <th className="px-5 py-4 font-semibold">Amount</th>
                <th className="px-5 py-4 font-semibold">Root Cause</th>
                <th className="px-5 py-4 font-semibold">Intervention</th>
                <th className="px-5 py-4 font-semibold">Policy</th>
                <th className="px-5 py-4 font-semibold text-right">Recovered</th>
                <th className="px-5 py-4 font-semibold"></th>
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-border/50">
                  <td colSpan={7} className="px-5 py-5">
                    <Skeleton className="h-4 w-full" />
                  </td>
                </tr>
              )) : filtered.map((item) => {
                const policyVariant = item.status === "allowed" || item.status === "success" ? "success"
                  : item.status === "stopped" || item.status === "failed" ? "danger" : "warning";
                const isRecovered = item.recovered_amount_paise > 0;
                return (
                  <tr key={item.case_id} className="border-b border-border/50 transition hover:bg-surfaceHover">
                    <td className="px-5 py-4">
                      <div className="font-medium text-primary">{item.customer ?? "Unknown Customer"}</div>
                      <div className="text-[10px] font-mono text-tertiary mt-0.5">{item.case_id.split("-")[0]}</div>
                    </td>
                    <td className="px-5 py-4 font-mono text-[12px] text-secondary">{money(item.amount_paise)}</td>
                    <td className="px-5 py-4">
                      <span className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[9px] font-mono uppercase tracking-wider ${DIAGNOSIS_COLORS[item.diagnosis] ?? "border-border text-tertiary"}`}>
                        {labelize(item.diagnosis)}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-accent-blue font-medium text-xs">
                      {item.action ? labelize(item.action) : "—"}
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge
                        value={item.status === "allowed" ? "Approved" : item.status}
                        variant={policyVariant}
                      />
                    </td>
                    <td className="px-5 py-4 text-right">
                      {isRecovered ? (
                        <span className="font-semibold text-accent-green">{money(item.recovered_amount_paise)}</span>
                      ) : (
                        <span className="text-tertiary font-mono text-[11px]">—</span>
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <Link
                        href={`/cases/${item.case_id}`}
                        className="inline-flex items-center gap-1.5 text-tertiary hover:text-accent-blue transition text-xs"
                        title="View Recovery Journey"
                      >
                        <ArrowRight size={14} />
                      </Link>
                    </td>
                  </tr>
                );
              })}
              {!loading && !filtered.length && (
                <tr>
                  <td colSpan={7} className="px-5 py-16 text-center text-secondary text-sm">
                    No recovery cases found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </main>
  );
}

export default function CasesPage() {
  return (
    <Suspense fallback={<div className="p-8 text-secondary">Loading Recovery Cases...</div>}>
      <CasesContent />
    </Suspense>
  );
}
