'use client';

import { useCallback, useEffect, useState } from 'react';

type AuditLog = {
  id: number;
  action: string;
  target: string;
  status: string;
  details: string | null;
  created_at: string;
  actor_username: string | null;
  actor_role: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? (typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8080/api`
  : 'http://127.0.0.1:8080/api');

export default function AuditLogsPage() {
  const [token, setToken] = useState('');
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [limit, setLimit] = useState(100);
  const [error, setError] = useState('');

  useEffect(() => {
    const savedToken = window.localStorage.getItem('blinddrop_token') || '';
    setToken(savedToken);
  }, []);

  const fetchLogs = useCallback(async (activeToken: string) => {
    if (!activeToken) {
      setError('Login from Members page first to access audit logs');
      setLogs([]);
      return;
    }

    setError('');
    const res = await fetch(`${API_BASE}/audit-logs?limit=${limit}`, {
      headers: {
        Authorization: `Bearer ${activeToken}`
      }
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(data.error || 'Could not fetch audit logs');
      setLogs([]);
      return;
    }
    setLogs(data.logs || []);
  }, [limit]);

  useEffect(() => {
    fetchLogs(token).catch(() => setError('Failed to load logs'));
  }, [token, fetchLogs]);

  return (
    <div className="flex-1 overflow-y-auto p-8 lg:p-16 bg-white min-h-full">
      <div className="max-w-6xl mx-auto space-y-16">
        
        {/* Header Block */}
        <div className="space-y-4">
          <div className="inline-flex px-3 py-1 bg-neutral-900 text-white text-xs font-bold tracking-widest uppercase mb-4">
            Audit Telemetry
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tighter text-neutral-900 uppercase">
            SYSTEM LOGS
          </h1>
          <p className="text-xl text-neutral-500 max-w-2xl leading-relaxed mt-2 font-medium">
            Safely audit transfer patterns to ensure no traces remain on public computers without logging private information.
          </p>
        </div>

        {error && (
          <div className="border border-neutral-900 bg-neutral-100 p-4 text-sm font-bold uppercase tracking-widest text-neutral-900">
            {error}
          </div>
        )}

        <div className="border border-neutral-900 flex flex-col bg-white">
          <div className="p-6 md:p-8 flex flex-col md:flex-row items-start md:items-center justify-between border-b border-neutral-900 gap-4">
            <h2 className="text-xl font-bold uppercase tracking-wide text-neutral-900">EVENT STREAM</h2>
            <div className="flex items-center gap-4">
              <div className="flex items-center">
                <span className="text-xs font-bold tracking-widest text-neutral-500 uppercase mr-3">LIMIT</span>
                <input
                  type="number"
                  min={1}
                  max={500}
                  value={limit}
                  onChange={(e) => setLimit(Number(e.target.value || 100))}
                  className="px-3 py-2 bg-neutral-100 border border-neutral-900 focus:outline-none focus:bg-white text-neutral-900 font-bold w-24 text-center"
                />
              </div>
              <button
                onClick={() => fetchLogs(token)}
                className="px-6 py-2 bg-neutral-900 hover:bg-neutral-800 text-white font-bold uppercase tracking-widest transition-colors text-sm"
              >
                REFRESH
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm font-medium text-left">
              <thead className="bg-neutral-100 border-b border-neutral-900 uppercase tracking-wider text-neutral-900 text-xs font-bold">
                <tr>
                  <th className="px-6 py-4">ID</th>
                  <th className="px-6 py-4">TIME</th>
                  <th className="px-6 py-4">ACTOR</th>
                  <th className="px-6 py-4">ROLE</th>
                  <th className="px-6 py-4">ACTION</th>
                  <th className="px-6 py-4">TARGET</th>
                  <th className="px-6 py-4">STATUS</th>
                  <th className="px-6 py-4">DETAILS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-neutral-50 transition-colors align-top">
                    <td className="px-6 py-4 font-bold text-neutral-900">{log.id}</td>
                    <td className="px-6 py-4 text-neutral-600 font-medium whitespace-nowrap text-xs uppercase tracking-wider">{new Date(log.created_at).toLocaleString()}</td>
                    <td className="px-6 py-4 text-neutral-900 font-bold uppercase tracking-widest">{log.actor_username || 'SYSTEM'}</td>
                    <td className="px-6 py-4 uppercase text-xs font-bold tracking-widest">{log.actor_role || '-'}</td>
                    <td className="px-6 py-4 text-neutral-900 font-bold tracking-widest uppercase">{log.action}</td>
                    <td className="px-6 py-4 text-neutral-600 font-mono text-xs">{log.target}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`px-2 py-1 text-[10px] font-bold tracking-widest uppercase border ${
                          log.status === 'success'
                            ? 'bg-neutral-900 text-white border-neutral-900'
                            : log.status === 'denied'
                              ? 'bg-neutral-200 text-neutral-900 border-neutral-900'
                              : 'bg-white text-neutral-900 border-neutral-900'
                        }`}
                      >
                        {log.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 max-w-sm break-words text-neutral-500 font-mono text-xs">{log.details || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}