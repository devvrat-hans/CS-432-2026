"use client";

import React, { useEffect, useState } from "react";
import { HardDrive, Layers, ArrowRight, RefreshCw, CheckCircle2, XCircle } from "lucide-react";
import Link from "next/link";

/* ─── API types ─── */
type PerTableCount = {
  total: number;
  per_shard: Record<string, number>;
};

type ShardingInfo = {
  num_shards: number;
  shard_key: string;
  partitioning_strategy: string;
  sharded_tables: string[];
  unsharded_tables: string[];
  per_table_counts: Record<string, PerTableCount>;
};

type VerifyCheck = {
  table: string;
  check: string;
  status: "pass" | "fail";
  original?: number;
  shard_total?: number;
  per_shard?: Record<string, number>;
  message?: string;
};

type VerifyResult = {
  all_pass: boolean;
  checks: VerifyCheck[];
};

/* ─── helpers ─── */
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ??
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8080/api`
    : "http://127.0.0.1:8080/api");

function getCookieToken() {
  if (typeof document === "undefined") return "";
  const match = document.cookie.split("; ").find((r) => r.startsWith("blinddrop_token="));
  return match ? match.split("=")[1] : "";
}

function authHeaders(): Record<string, string> {
  const token = (typeof window !== "undefined" && window.localStorage.getItem("blinddrop_token")) || getCookieToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/* ─── page ─── */
export default function ShardingPage() {
  const [info, setInfo] = useState<ShardingInfo | null>(null);
  const [verify, setVerify] = useState<VerifyResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState("");

  const loadInfo = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/sharding/info`, { headers: authHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setInfo(await res.json());
    } catch {
      setError("Failed to load sharding info from backend.");
    } finally {
      setLoading(false);
    }
  };

  const runVerify = async () => {
    setVerifying(true);
    try {
      const res = await fetch(`${API_BASE}/sharding/verify`, { headers: authHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setVerify(await res.json());
    } catch {
      setError("Verification request failed.");
    } finally {
      setVerifying(false);
    }
  };

  useEffect(() => {
    loadInfo();
  }, []);

  /* ─── distribution bar ─── */
  const DistributionBar = ({ perShard, total }: { perShard: Record<string, number>; total: number }) => {
    const shardColors = ["bg-neutral-900", "bg-neutral-600", "bg-neutral-400"];
    return (
      <div className="flex w-full h-6 border border-neutral-900 overflow-hidden">
        {Object.entries(perShard).map(([id, count], idx) => {
          const pct = total > 0 ? (count / total) * 100 : 0;
          return (
            <div
              key={id}
              className={`${shardColors[idx % shardColors.length]} relative group`}
              style={{ width: `${Math.max(pct, 1)}%` }}
              title={`Shard ${id}: ${count} (${pct.toFixed(1)}%)`}
            >
              <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white opacity-0 group-hover:opacity-100 transition-opacity">
                {count}
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 lg:p-16 bg-white min-h-full">
      <div className="max-w-6xl mx-auto space-y-16">
        {/* Header */}
        <div className="space-y-4">
          <div className="inline-flex px-3 py-1 bg-neutral-900 text-white text-xs font-bold tracking-widest uppercase mb-4">
            Infrastructure
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tighter text-neutral-900 uppercase">
            SHARD TOPOLOGY
          </h1>
          <p className="text-xl text-neutral-500 max-w-2xl leading-relaxed mt-2 font-medium">
            Hash-based horizontal partitioning across SQLite shard databases. Monitor distribution, verify integrity, and inspect per-table record placement.
          </p>
        </div>

        {error && (
          <div className="border border-neutral-900 bg-neutral-100 p-4 text-sm font-bold uppercase tracking-widest flex items-center gap-3">
            <XCircle size={20} className="text-neutral-900" />
            {error}
          </div>
        )}

        {loading && (
          <div className="text-sm font-bold uppercase tracking-widest text-neutral-500 animate-pulse">
            Loading shard topology...
          </div>
        )}

        {info && (
          <>
            {/* Shard Config Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-0 border-t border-l border-neutral-900">
              <ConfigCard title="TOTAL SHARDS" value={String(info.num_shards)} icon={<HardDrive size={22} className="text-neutral-900" />} />
              <ConfigCard title="SHARD KEY" value={info.shard_key} icon={<Layers size={22} className="text-neutral-900" />} />
              <ConfigCard title="SHARDED TABLES" value={String(info.sharded_tables.length)} icon={<Layers size={22} className="text-neutral-900" />} />
              <ConfigCard title="UNSHARDED TABLES" value={String(info.unsharded_tables.length)} icon={<HardDrive size={22} className="text-neutral-900" />} />
            </div>
            <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
              Strategy: {info.partitioning_strategy}
            </p>

            {/* Per-table distribution */}
            <div className="border border-neutral-900 bg-white">
              <div className="p-6 md:p-8 border-b border-neutral-900 flex items-center justify-between">
                <h3 className="text-xl font-bold uppercase tracking-wide text-neutral-900">
                  PER-TABLE DISTRIBUTION
                </h3>
                <button
                  onClick={loadInfo}
                  className="p-2 border border-neutral-900 hover:bg-neutral-100 transition-colors"
                  title="Refresh"
                >
                  <RefreshCw size={16} />
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm font-medium text-left">
                  <thead className="bg-neutral-100 border-b border-neutral-900 uppercase tracking-wider text-neutral-900 text-xs font-bold">
                    <tr>
                      <th className="px-6 py-4">TABLE</th>
                      <th className="px-6 py-4">TOTAL</th>
                      {Array.from({ length: info.num_shards }).map((_, i) => (
                        <th key={i} className="px-6 py-4">SHARD {i}</th>
                      ))}
                      <th className="px-6 py-4 w-64">DISTRIBUTION</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-200">
                    {info.sharded_tables.map((table) => {
                      const tc = info.per_table_counts[table] || { total: 0, per_shard: {} };
                      return (
                        <tr key={table} className="hover:bg-neutral-50 transition-colors">
                          <td className="px-6 py-4 font-bold text-neutral-900 uppercase tracking-widest text-xs">{table}</td>
                          <td className="px-6 py-4 font-bold text-neutral-900">{tc.total}</td>
                          {Array.from({ length: info.num_shards }).map((_, i) => (
                            <td key={i} className="px-6 py-4 text-neutral-700">{tc.per_shard[String(i)] ?? 0}</td>
                          ))}
                          <td className="px-6 py-4">
                            <DistributionBar perShard={tc.per_shard} total={tc.total} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Shard Legend */}
            <div className="flex gap-6 items-center">
              {Array.from({ length: info.num_shards }).map((_, i) => {
                const colors = ["bg-neutral-900", "bg-neutral-600", "bg-neutral-400"];
                return (
                  <div key={i} className="flex items-center gap-2">
                    <div className={`w-4 h-4 ${colors[i % colors.length]}`} />
                    <span className="text-xs font-bold uppercase tracking-widest text-neutral-600">Shard {i}</span>
                  </div>
                );
              })}
            </div>

            {/* Unsharded Tables List */}
            <div className="border border-neutral-900 bg-white">
              <div className="p-6 md:p-8 border-b border-neutral-900">
                <h3 className="text-xl font-bold uppercase tracking-wide text-neutral-900">
                  UNSHARDED TABLES
                </h3>
              </div>
              <div className="p-6 md:p-8 flex flex-wrap gap-3">
                {info.unsharded_tables.map((t) => (
                  <span key={t} className="px-4 py-2 border border-neutral-900 text-xs font-bold uppercase tracking-widest text-neutral-900">
                    {t}
                  </span>
                ))}
              </div>
            </div>

            {/* Verification Section */}
            <div className="border border-neutral-900 bg-white">
              <div className="p-6 md:p-8 border-b border-neutral-900 flex items-center justify-between">
                <h3 className="text-xl font-bold uppercase tracking-wide text-neutral-900">
                  INTEGRITY VERIFICATION
                </h3>
                <button
                  onClick={runVerify}
                  disabled={verifying}
                  className="inline-flex items-center gap-2 px-4 py-2 border border-neutral-900 hover:bg-neutral-100 text-sm font-bold uppercase tracking-widest transition-colors disabled:opacity-50"
                >
                  {verifying ? "RUNNING..." : "RUN CHECKS"}
                  <ArrowRight size={14} />
                </button>
              </div>
              {verify && (
                <div className="p-6 md:p-8 space-y-4">
                  <div className={`inline-flex px-3 py-1 text-xs font-bold tracking-widest uppercase ${verify.all_pass ? "bg-neutral-900 text-white" : "bg-red-600 text-white"}`}>
                    {verify.all_pass ? "ALL CHECKS PASSED" : "SOME CHECKS FAILED"}
                  </div>
                  <div className="overflow-x-auto border border-neutral-900">
                    <table className="w-full text-sm font-medium text-left">
                      <thead className="bg-neutral-100 border-b border-neutral-900 uppercase tracking-wider text-neutral-900 text-xs font-bold">
                        <tr>
                          <th className="px-6 py-4">TABLE</th>
                          <th className="px-6 py-4">CHECK</th>
                          <th className="px-6 py-4">STATUS</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-neutral-200">
                        {verify.checks.map((c, i) => (
                          <tr key={i} className="hover:bg-neutral-50 transition-colors">
                            <td className="px-6 py-4 font-bold text-neutral-900 uppercase tracking-widest text-xs">{c.table}</td>
                            <td className="px-6 py-4 text-neutral-700 uppercase text-xs tracking-wider">{c.check}</td>
                            <td className="px-6 py-4">
                              {c.status === "pass" ? (
                                <CheckCircle2 size={18} className="text-neutral-900" />
                              ) : (
                                <XCircle size={18} className="text-red-600" />
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              {!verify && !verifying && (
                <div className="p-6 md:p-8 text-xs font-bold uppercase tracking-widest text-neutral-500">
                  Click &ldquo;Run Checks&rdquo; to verify shard integrity — record counts, duplicate detection, and hash consistency.
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/* ─── stat card ─── */
function ConfigCard({ title, value, icon }: { title: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="bg-white p-6 border-r border-b border-neutral-900 flex flex-col justify-between hover:bg-neutral-50 transition-colors">
      <div className="flex items-start justify-between relative z-10 mb-4">
        <div className="p-3 border border-neutral-900 bg-neutral-100">{icon}</div>
      </div>
      <div className="mt-4 relative z-10">
        <div className="text-4xl font-extrabold text-neutral-900 tracking-tighter uppercase">{value}</div>
        <div className="text-sm font-bold tracking-widest text-neutral-500 mt-2 uppercase">{title}</div>
      </div>
    </div>
  );
}
