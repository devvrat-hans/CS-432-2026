"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { Database, Users, ShieldAlert, Zap, Server, Lock, ArrowRight, Table, BarChart3, Clock, HardDrive, Upload, Download, FileX, FileClock } from 'lucide-react';
import Link from 'next/link';

type AuditLog = {
  id: number;
  action: string;
  target: string;
  status: string;
  details: string | null;
  created_at: string;
  actor_username: string | null;
};

type DashboardStats = {
  databaseCount: number;
  tableCount: number;
  memberCount: number;
  auditCount: number;
  queryLatencyMs: number | null;
};

type ApiLatency = {
  api: string;
  avg_ms: number;
};

type ShardSummary = {
  num_shards: number;
  shard_key: string;
  partitioning_strategy: string;
  sharded_tables: string[];
  total_sharded_records: number;
};

type TransferStats = {
  uploads_today: number;
  downloads_today: number;
  active_files: number;
  expired_files: number;
  downloaded_files: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? (typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8080/api`
  : 'http://127.0.0.1:8080/api');

function getCookieToken() {
  if (typeof document === 'undefined') {
    return '';
  }
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith('blinddrop_token='));
  return match ? match.split('=')[1] : '';
}

export default function Home() {
  const [stats, setStats] = useState<DashboardStats>({
    databaseCount: 0,
    tableCount: 0,
    memberCount: 0,
    auditCount: 0,
    queryLatencyMs: null,
  });
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [apiLatencies, setApiLatencies] = useState<ApiLatency[]>([]);
  const [shardSummary, setShardSummary] = useState<ShardSummary | null>(null);
  const [transferStats, setTransferStats] = useState<TransferStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const activityRows = useMemo(
    () =>
      logs.map((log) => ({
        id: log.id,
        title: `${log.action} • ${log.target}`,
        subtitle: log.actor_username ? `by ${log.actor_username}` : 'by system',
        time: new Date(log.created_at).toLocaleString(),
      })),
    [logs]
  );

  useEffect(() => {
    const loadDashboard = async () => {
      setLoading(true);
      setError('');

      try {
        const localToken = window.localStorage.getItem('blinddrop_token') || '';
        const token = localToken || getCookieToken();
        const authHeaders = token ? { Authorization: `Bearer ${token}` } : undefined;

        const summaryRes = await fetch(`${API_BASE}/dashboard/summary`, { headers: authHeaders });
        const summaryData = await summaryRes.json().catch(() => ({}));

        let queryLatencyMs: number | null = null;
        if (authHeaders) {
          const benchmarkRes = await fetch(`${API_BASE}/indexing/benchmark?iterations=250`, {
            headers: authHeaders,
          });
          const benchmarkData = await benchmarkRes.json().catch(() => ({}));
          if (benchmarkRes.ok) {
            queryLatencyMs = Number(benchmarkData.avg_ms || 0);
          }
        }

        let recentLogs: AuditLog[] = [];
        if (authHeaders) {
          const logsRes = await fetch(`${API_BASE}/audit-logs?limit=4`, {
            headers: authHeaders,
          });
          const logsData = await logsRes.json().catch(() => ({}));
          if (logsRes.ok) {
            recentLogs = logsData.logs || [];
          }
        }

        let latencies: ApiLatency[] = [];
        if (authHeaders) {
          const latencyRes = await fetch(`${API_BASE}/indexing/api-latency?iterations=150`, {
            headers: authHeaders,
          });
          const latencyData = await latencyRes.json().catch(() => ({}));
          if (latencyRes.ok && Array.isArray(latencyData.results)) {
            latencies = latencyData.results.map((item: any) => ({
              api: String(item.api || ''),
              avg_ms: Number(item.avg_ms || 0),
            }));
          }
        }

        let shardInfo: ShardSummary | null = null;
        if (authHeaders) {
          const shardRes = await fetch(`${API_BASE}/sharding/info`, {
            headers: authHeaders,
          });
          const shardData = await shardRes.json().catch(() => ({}));
          if (shardRes.ok && shardData.num_shards) {
            let totalSharded = 0;
            if (shardData.per_table_counts) {
              for (const tc of Object.values(shardData.per_table_counts) as any[]) {
                totalSharded += Number(tc.total || 0);
              }
            }
            shardInfo = {
              num_shards: shardData.num_shards,
              shard_key: shardData.shard_key,
              partitioning_strategy: shardData.partitioning_strategy,
              sharded_tables: shardData.sharded_tables || [],
              total_sharded_records: totalSharded,
            };
          }
        }

        setStats({
          databaseCount: Number(summaryData.database_count || 0),
          tableCount: Number(summaryData.table_count || 0),
          memberCount: Number(summaryData.member_count || 0),
          auditCount: Number(summaryData.audit_count || 0),
          queryLatencyMs,
        });
        setLogs(recentLogs);
        setApiLatencies(latencies);
        setShardSummary(shardInfo);

        // Fetch transfer stats.
        let xferStats: TransferStats | null = null;
        if (authHeaders) {
          try {
            const xferRes = await fetch(`${API_BASE}/admin/transfer-stats`, {
              headers: authHeaders,
            });
            const xferData = await xferRes.json().catch(() => ({}));
            if (xferRes.ok) {
              xferStats = {
                uploads_today: Number(xferData.uploads_today || 0),
                downloads_today: Number(xferData.downloads_today || 0),
                active_files: Number(xferData.active_files || 0),
                expired_files: Number(xferData.expired_files || 0),
                downloaded_files: Number(xferData.downloaded_files || 0),
              };
            }
          } catch {
            // Transfer stats endpoint may not exist yet.
          }
        }
        setTransferStats(xferStats);
      } catch {
        setError('Could not fetch live dashboard data from backend');
      } finally {
        setLoading(false);
      }
    };

    loadDashboard();
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-8 lg:p-16 bg-white min-h-full">
      <div className="max-w-6xl mx-auto space-y-16">
        
        {/* Header Block */}
        <div className="space-y-4">
          <div className="inline-flex px-3 py-1 bg-neutral-900 text-white text-xs font-bold tracking-widest uppercase mb-4">
            Administrative Core
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tighter text-neutral-900 uppercase">
            SYSTEM DASHBOARD
          </h1>
          <p className="text-xl text-neutral-500 max-w-2xl leading-relaxed mt-2 font-medium">
            Manage safe file transfer policies, oversee members, and verify privacy-focused audit trails for temporary storage.
          </p>
        </div>

        {error && (
          <div className="border border-neutral-900 bg-neutral-100 p-4 text-sm font-bold uppercase tracking-widest flex items-center gap-3">
            <ShieldAlert size={20} className="text-neutral-900" />
            {error}
          </div>
        )}

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-0 border-t border-l border-neutral-900">
          <StatCard
            title="ACTIVE DATABASES"
            value={String(stats.databaseCount)}
            
            icon={<Server size={22} className="text-neutral-900" />}
          />
          <StatCard
            title="TOTAL TABLES"
            value={String(stats.tableCount)}
            
            icon={<Table size={22} className="text-neutral-900" />}
          />
          <StatCard
            title="SYSTEM MEMBERS"
            value={String(stats.memberCount)}
            
            icon={<Users size={22} className="text-neutral-900" />}
          />
          <StatCard
            title="QUERY LATENCY"
            value={
              stats.queryLatencyMs === null
                ? 'N/A'
                : `${stats.queryLatencyMs.toFixed(6)} ms`
            }

            icon={<BarChart3 size={22} className="text-neutral-900" />}
          />
        </div>

        <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
          Query Latency represents average SQL response time for members lookup by username (250 benchmark iterations).
        </p>

        {/* File Transfer Stats */}
        {transferStats && (
          <>
            <div className="space-y-4">
              <h2 className="text-xl font-bold uppercase tracking-wide text-neutral-900">FILE TRANSFERS</h2>
              <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
                Real-time upload &amp; download activity across all shards.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-0 border-t border-l border-neutral-900">
              <StatCard
                title="UPLOADS TODAY"
                value={String(transferStats.uploads_today)}
                icon={<Upload size={22} className="text-neutral-900" />}
              />
              <StatCard
                title="DOWNLOADS TODAY"
                value={String(transferStats.downloads_today)}
                icon={<Download size={22} className="text-neutral-900" />}
              />
              <StatCard
                title="ACTIVE FILES"
                value={String(transferStats.active_files)}
                icon={<FileClock size={22} className="text-neutral-900" />}
              />
              <StatCard
                title="EXPIRED FILES"
                value={String(transferStats.expired_files)}
                icon={<FileX size={22} className="text-neutral-900" />}
              />
            </div>
          </>
        )}

        {/* Main Interactive Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
          {/* Main Activity Area (Expanded) */}
          <div className="border border-neutral-900 bg-white">
            <div className="p-6 md:p-8 border-b border-neutral-900 flex items-center justify-between">
              <h3 className="text-xl font-bold uppercase tracking-wide text-neutral-900">LIVE ACTIVITY</h3>
              <span className="text-xs font-bold uppercase tracking-widest text-neutral-500">live feed</span>
            </div>
            <div className="p-6 md:p-8">
              <div className="flex-1 overflow-x-auto border border-neutral-900">
                <table className="w-full text-sm font-medium text-left">
                  <thead className="bg-neutral-100 border-b border-neutral-900 uppercase tracking-wider text-neutral-900 text-xs font-bold">
                    <tr>
                      <th className="px-6 py-4">ACTION</th>
                      <th className="px-6 py-4">ACTOR</th>
                      <th className="px-6 py-4">TIME</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-200">
                    {activityRows.map((row) => (
                      <tr key={row.id} className="hover:bg-neutral-50 transition-colors">
                        <td className="px-6 py-4 font-bold text-neutral-900 uppercase tracking-widest text-xs">{row.title}</td>
                        <td className="px-6 py-4 text-neutral-600 uppercase text-xs tracking-wider">{row.subtitle}</td>
                        <td className="px-6 py-4 text-neutral-500 text-xs tracking-wider">{row.time}</td>
                      </tr>
                    ))}
                    {loading && activityRows.length === 0 && (
                      <tr>
                        <td className="px-6 py-6 text-neutral-500 uppercase text-xs tracking-widest" colSpan={3}>
                          Loading activity...
                        </td>
                      </tr>
                    )}
                    {!loading && activityRows.length === 0 && (
                      <tr>
                        <td className="px-6 py-6 text-neutral-500 uppercase text-xs tracking-widest" colSpan={3}>
                          System idle
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="p-6 border-t border-neutral-900">
              <Link href="/admin/audit-logs" className="inline-flex items-center gap-2 px-4 py-2 border border-neutral-900 hover:bg-neutral-100 text-sm font-bold uppercase tracking-widest transition-colors">
                VIEW FULL LOGS
                <ArrowRight size={14} />
              </Link>
            </div>
          </div>

          <div className="border border-neutral-900 bg-white">
            <div className="p-6 md:p-8 border-b border-neutral-900 flex items-center justify-between">
              <h3 className="text-xl font-bold uppercase tracking-wide text-neutral-900">API LATENCY MATRIX</h3>
              <span className="text-xs font-bold uppercase tracking-widest text-neutral-500">live benchmark</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm font-medium text-left">
                <thead className="bg-neutral-100 border-b border-neutral-900 uppercase tracking-wider text-neutral-900 text-xs font-bold">
                  <tr>
                    <th className="px-6 py-4">API</th>
                    <th className="px-6 py-4">AVG LATENCY</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200">
                  {apiLatencies.slice(0, 5).map((row) => (
                    <tr key={row.api} className="hover:bg-neutral-50 transition-colors">
                      <td className="px-6 py-4 font-mono text-xs text-neutral-900">{row.api}</td>
                      <td className="px-6 py-4 font-bold text-neutral-900">{row.avg_ms.toFixed(6)} ms</td>
                    </tr>
                  ))}
                  {!loading && apiLatencies.length === 0 && (
                    <tr>
                      <td className="px-6 py-6 text-neutral-500 uppercase text-xs tracking-widest" colSpan={2}>
                        No latency data available
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="p-6 border-t border-neutral-900">
              <Link href="/admin/api-latencies" className="inline-flex items-center gap-2 px-4 py-2 border border-neutral-900 hover:bg-neutral-100 text-sm font-bold uppercase tracking-widest transition-colors">
                VIEW ALL API LATENCIES
                <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </div>

        {/* Shard Overview Panel */}
        {shardSummary && (
          <div className="border border-neutral-900 bg-white">
            <div className="p-6 md:p-8 border-b border-neutral-900 flex items-center justify-between">
              <h3 className="text-xl font-bold uppercase tracking-wide text-neutral-900">SHARD OVERVIEW</h3>
              <span className="text-xs font-bold uppercase tracking-widest text-neutral-500">infrastructure</span>
            </div>
            <div className="p-6 md:p-8">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
                <div>
                  <div className="text-3xl font-extrabold text-neutral-900 tracking-tighter">{shardSummary.num_shards}</div>
                  <div className="text-xs font-bold tracking-widest text-neutral-500 mt-1 uppercase">Shards</div>
                </div>
                <div>
                  <div className="text-3xl font-extrabold text-neutral-900 tracking-tighter">{shardSummary.sharded_tables.length}</div>
                  <div className="text-xs font-bold tracking-widest text-neutral-500 mt-1 uppercase">Sharded Tables</div>
                </div>
                <div>
                  <div className="text-3xl font-extrabold text-neutral-900 tracking-tighter">{shardSummary.total_sharded_records}</div>
                  <div className="text-xs font-bold tracking-widest text-neutral-500 mt-1 uppercase">Total Records</div>
                </div>
                <div>
                  <div className="text-xl font-extrabold text-neutral-900 tracking-tighter uppercase">{shardSummary.shard_key}</div>
                  <div className="text-xs font-bold tracking-widest text-neutral-500 mt-1 uppercase">Shard Key</div>
                </div>
              </div>
              <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
                {shardSummary.partitioning_strategy}
              </p>
            </div>
            <div className="p-6 border-t border-neutral-900">
              <Link href="/admin/sharding" className="inline-flex items-center gap-2 px-4 py-2 border border-neutral-900 hover:bg-neutral-100 text-sm font-bold uppercase tracking-widest transition-colors">
                VIEW SHARD TOPOLOGY
                <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

function StatCard({ title, value, icon }: { title: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="bg-white p-6 border-r border-b border-neutral-900 flex flex-col justify-between hover:bg-neutral-50 transition-colors">
      <div className="flex items-start justify-between relative z-10 mb-4">
        <div className="p-3 border border-neutral-900 bg-neutral-100">
          {icon}
        </div>
      </div>
      
      <div className="mt-4 relative z-10">
        <div className="text-4xl font-extrabold text-neutral-900 tracking-tighter uppercase">{value}</div>
        <div className="text-sm font-bold tracking-widest text-neutral-500 mt-2 uppercase">
          {title}
        </div>
        
      </div>
    </div>
  );
}
