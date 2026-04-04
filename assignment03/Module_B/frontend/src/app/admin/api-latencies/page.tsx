'use client';

import { useCallback, useEffect, useState } from 'react';

type ApiLatencyRow = {
  method: string;
  api: string;
  avg_ms: number;
  total_seconds: number;
  iterations: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? (typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8080/api`
  : 'http://127.0.0.1:8080/api');

export default function ApiLatenciesPage() {
  const [token, setToken] = useState('');
  const [rows, setRows] = useState<ApiLatencyRow[]>([]);
  const [iterations, setIterations] = useState(150);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const savedToken = window.localStorage.getItem('blinddrop_token') || '';
    setToken(savedToken);
  }, []);

  const loadLatencies = useCallback(async (activeToken: string, activeIterations: number) => {
    if (!activeToken) {
      setError('Login required to view API latency telemetry');
      setRows([]);
      return;
    }

    setLoading(true);
    setError('');
    const res = await fetch(`${API_BASE}/indexing/api-latency?iterations=${activeIterations}`, {
      headers: {
        Authorization: `Bearer ${activeToken}`
      }
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(data.error || 'Failed to fetch API latencies');
      setRows([]);
      setLoading(false);
      return;
    }

    const parsedRows = Array.isArray(data.results)
      ? data.results.map((row: any) => ({
          method: String(row.method || 'GET').toUpperCase(),
          api: String(row.api || ''),
          avg_ms: Number(row.avg_ms || 0),
          total_seconds: Number(row.total_seconds || 0),
          iterations: Number(row.iterations || activeIterations),
        }))
      : [];

    setRows(parsedRows);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadLatencies(token, iterations).catch(() => {
      setError('Unable to load API latency telemetry');
      setLoading(false);
    });
  }, [token, iterations, loadLatencies]);

  const getRows = rows.filter((row) => row.method === 'GET');
  const postRows = rows.filter((row) => row.method === 'POST');

  return (
    <div className="flex-1 overflow-y-auto p-8 lg:p-16 bg-white min-h-full">
      <div className="max-w-6xl mx-auto space-y-16">
        <div className="space-y-4">
          <div className="inline-flex px-3 py-1 bg-neutral-900 text-white text-xs font-bold tracking-widest uppercase mb-4">
            Indexing Telemetry
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tighter text-neutral-900 uppercase">
            API LATENCIES
          </h1>
          <p className="text-xl text-neutral-500 max-w-3xl leading-relaxed mt-2 font-medium">
            Live benchmark timings for key Module B APIs measured against local SQLite query paths.
          </p>
        </div>

        {error && (
          <div className="border border-neutral-900 bg-neutral-100 p-4 text-sm font-bold uppercase tracking-widest text-neutral-900">
            {error}
          </div>
        )}

        <div className="border border-neutral-900 flex flex-col bg-white">
          <div className="p-6 md:p-8 border-b border-neutral-900 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <h2 className="text-xl font-bold uppercase tracking-wide text-neutral-900">GET API LATENCIES</h2>
            <div className="flex items-center gap-3">
              <label className="text-xs font-bold uppercase tracking-widest text-neutral-500">Iterations</label>
              <input
                type="number"
                min={10}
                max={5000}
                value={iterations}
                onChange={(e) => setIterations(Number(e.target.value || 150))}
                className="px-3 py-2 bg-neutral-100 border border-neutral-900 focus:outline-none focus:bg-white text-neutral-900 font-bold w-28 text-center"
              />
              <button
                onClick={() => loadLatencies(token, iterations)}
                className="px-5 py-2 bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-bold uppercase tracking-widest transition-colors"
              >
                Refresh
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm font-medium text-left">
              <thead className="bg-neutral-100 border-b border-neutral-900 uppercase tracking-wider text-neutral-900 text-xs font-bold">
                <tr>
                  <th className="px-6 py-4">API</th>
                  <th className="px-6 py-4">AVG (ms)</th>
                  <th className="px-6 py-4">TOTAL (s)</th>
                  <th className="px-6 py-4">ITERATIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200">
                {getRows.map((row) => (
                  <tr key={row.api} className="hover:bg-neutral-50 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs text-neutral-900">{row.api}</td>
                    <td className="px-6 py-4 font-bold text-neutral-900">{row.avg_ms.toFixed(6)}</td>
                    <td className="px-6 py-4 text-neutral-600">{row.total_seconds.toFixed(6)}</td>
                    <td className="px-6 py-4 text-neutral-600">{row.iterations}</td>
                  </tr>
                ))}
                {!loading && getRows.length === 0 && (
                  <tr>
                    <td className="px-6 py-6 text-neutral-500 uppercase text-xs tracking-widest" colSpan={4}>
                      No GET latency data available.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="border border-neutral-900 flex flex-col bg-white">
          <div className="p-6 md:p-8 border-b border-neutral-900">
            <h2 className="text-xl font-bold uppercase tracking-wide text-neutral-900">POST API LATENCIES</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm font-medium text-left">
              <thead className="bg-neutral-100 border-b border-neutral-900 uppercase tracking-wider text-neutral-900 text-xs font-bold">
                <tr>
                  <th className="px-6 py-4">API</th>
                  <th className="px-6 py-4">AVG (ms)</th>
                  <th className="px-6 py-4">TOTAL (s)</th>
                  <th className="px-6 py-4">ITERATIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200">
                {postRows.map((row) => (
                  <tr key={row.api} className="hover:bg-neutral-50 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs text-neutral-900">{row.api}</td>
                    <td className="px-6 py-4 font-bold text-neutral-900">{row.avg_ms.toFixed(6)}</td>
                    <td className="px-6 py-4 text-neutral-600">{row.total_seconds.toFixed(6)}</td>
                    <td className="px-6 py-4 text-neutral-600">{row.iterations}</td>
                  </tr>
                ))}
                {!loading && postRows.length === 0 && (
                  <tr>
                    <td className="px-6 py-6 text-neutral-500 uppercase text-xs tracking-widest" colSpan={4}>
                      No POST latency data available.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
