"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { Database, Users, Activity, ShieldAlert, Zap, Server, Lock, ArrowRight, Table, BarChart3, DatabaseZap, Clock } from 'lucide-react';
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

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8080/api';

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

        setStats({
          databaseCount: Number(summaryData.database_count || 0),
          tableCount: Number(summaryData.table_count || 0),
          memberCount: Number(summaryData.member_count || 0),
          auditCount: Number(summaryData.audit_count || 0),
          queryLatencyMs,
        });
        setLogs(recentLogs);
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

        {/* Main Interactive Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          {/* Main Activity Area (Expanded) */}
          <div className="lg:col-span-3 border border-neutral-900 flex flex-col h-full lg:sticky lg:top-8 bg-white">
            <div className="p-6 md:p-8 flex-1 flex flex-col">
              <div className="flex items-center justify-between mb-8 pb-4 border-b border-neutral-200">
                <h3 className="text-xl font-bold uppercase tracking-wide flex items-center gap-2">
                  <Activity size={22} className="text-neutral-900" />
                  LIVE ACTIVITY
                </h3>
                <span className="flex h-2 w-2 relative">
                  {loading ? (
                    '...'
                  ) : (
                    <>
                      <span className="animate-ping absolute inline-flex h-full w-full bg-neutral-900 opacity-75"></span>
                      <span className="relative inline-flex h-2 w-2 bg-neutral-900"></span>
                    </>
                  )}
                </span>
              </div>
              
              <div className="flex-1 space-y-6 flex flex-col justify-start">
                {activityRows.length === 0 && !loading && (
                  <div className="flex flex-col items-center justify-center py-10 text-center space-y-3">
                    <div className="p-4 bg-neutral-100 border border-neutral-900">
                      <Clock size={24} className="text-neutral-900" />
                    </div>
                    <p className="text-sm font-bold uppercase tracking-widest text-neutral-500">
                      SYSTEM IDLE
                    </p>
                  </div>
                )}
                {loading && activityRows.length === 0 && (
                  <div className="space-y-4 animate-pulse">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="flex gap-4 items-start">
                        <div className="w-2.5 h-2.5 bg-neutral-200 mt-1.5 flex-shrink-0"></div>
                        <div className="space-y-2 flex-1">
                          <div className="h-4 bg-neutral-200 w-3/4"></div>
                          <div className="h-3 bg-neutral-100 w-1/2"></div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {activityRows.map((row, i) => (
                  <div key={row.id} className="relative flex gap-5 group">
                    <div className="flex flex-col items-center">
                      <div className="w-3 h-3 bg-white border border-neutral-900 group-hover:bg-neutral-900 transition-all z-10 relative mt-1"></div>
                      {i !== activityRows.length - 1 && (
                        <div className="w-[1px] h-full bg-neutral-300 absolute top-4 left-[0.3rem]"></div>
                      )}
                    </div>
                    <div className="pb-6 w-full">
                      <p className="text-sm font-bold text-neutral-900 uppercase tracking-widest">{row.title}</p>
                      <div className="flex items-center justify-between mt-1">
                        <p className="text-sm text-neutral-500 font-medium uppercase">{row.subtitle}</p>
                        <p className="text-xs text-neutral-400 font-bold uppercase tracking-wider">{row.time}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="mt-4 pt-6 border-t border-neutral-900">
                <Link href="/admin/audit-logs" className="flex items-center justify-between w-full text-sm font-bold uppercase tracking-widest text-neutral-900 hover:bg-neutral-100 p-3 border border-neutral-900 transition-colors">
                  FULL SYSTEM LOGS 
                  <ArrowRight size={16} />
                </Link>
              </div>
            </div>
          </div>
        </div>

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
