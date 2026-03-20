import { useState } from 'react'
import { PageHeader, LoadingPage } from '../components/UI'
import api from '../api/axios'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell, Legend
} from 'recharts'
import { Zap, ChevronDown, ChevronUp, Play, TrendingDown, Clock } from 'lucide-react'

function ExplainPanel({ plan, label }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 text-xs font-mono text-muted hover:text-paper transition-colors"
      >
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        {label} EXPLAIN plan
      </button>
      {open && (
        <pre className="mt-2 p-3 bg-white/[0.03] border border-white/[0.06] rounded-lg text-[10px] font-mono text-muted overflow-x-auto leading-relaxed">
          {plan?.join('\n') || 'No plan available'}
        </pre>
      )}
    </div>
  )
}

function QueryResultCard({ result, index }) {
  const improved = result.improvement > 0
  const pct = Math.abs(result.speedup_pct)

  return (
    <div className="card p-5 animate-fade-up" style={{ animationDelay: `${index * 80}ms` }}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="font-display font-semibold text-paper text-sm">{result.query}</p>
          <p className="font-mono text-[10px] text-muted mt-0.5">Query {index + 1}</p>
        </div>
        {improved ? (
          <div className="flex items-center gap-1.5 bg-accent/10 border border-accent/20 rounded-full px-3 py-1">
            <TrendingDown size={11} className="text-accent" />
            <span className="font-mono text-xs text-accent">{pct}% faster</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 bg-white/5 border border-white/10 rounded-full px-3 py-1">
            <span className="font-mono text-xs text-muted">No change</span>
          </div>
        )}
      </div>

      {/* Before/after bars */}
      <div className="space-y-2.5 mb-4">
        <div>
          <div className="flex justify-between text-[10px] font-mono text-muted mb-1">
            <span>WITHOUT indexes</span>
            <span className="text-signal">{result.before_ms} ms</span>
          </div>
          <div className="h-2 bg-white/5 rounded-full overflow-hidden">
            <div
              className="h-full bg-signal/60 rounded-full"
              style={{ width: `${Math.min((result.before_ms / Math.max(result.before_ms, result.after_ms)) * 100, 100)}%` }}
            />
          </div>
        </div>
        <div>
          <div className="flex justify-between text-[10px] font-mono text-muted mb-1">
            <span>WITH indexes</span>
            <span className="text-accent">{result.after_ms} ms</span>
          </div>
          <div className="h-2 bg-white/5 rounded-full overflow-hidden">
            <div
              className="h-full bg-accent/70 rounded-full"
              style={{ width: `${Math.min((result.after_ms / Math.max(result.before_ms, result.after_ms)) * 100, 100)}%` }}
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 pt-3 border-t border-white/[0.06]">
        <div className="text-center">
          <p className="text-[10px] font-mono text-muted mb-0.5">Before</p>
          <p className="font-display font-bold text-sm text-signal">{result.before_ms}ms</p>
        </div>
        <div className="text-center">
          <p className="text-[10px] font-mono text-muted mb-0.5">After</p>
          <p className="font-display font-bold text-sm text-accent">{result.after_ms}ms</p>
        </div>
        <div className="text-center">
          <p className="text-[10px] font-mono text-muted mb-0.5">Saved</p>
          <p className={`font-display font-bold text-sm ${improved ? 'text-accent' : 'text-muted'}`}>
            {result.improvement > 0 ? `${result.improvement}ms` : '—'}
          </p>
        </div>
      </div>

      <ExplainPanel plan={result.explain_before} label="Before" />
      <ExplainPanel plan={result.explain_after}  label="After" />
    </div>
  )
}

export default function Benchmark() {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const runBenchmark = async () => {
    setLoading(true); setError(''); setData(null)
    try {
      const { data: res } = await api.get('/api/benchmark')
      setData(res.comparison)
    } catch(e) {
      setError(e.response?.data?.error || 'Benchmark failed')
    } finally {
      setLoading(false)
    }
  }

  const chartData = data?.map(r => ({
    name: r.query.split(' ').slice(0,3).join(' '),
    before: r.before_ms,
    after:  r.after_ms,
  }))

  const totalSaved = data?.reduce((s, r) => s + Math.max(r.improvement, 0), 0).toFixed(4)
  const avgSpeedup = data
    ? (data.reduce((s,r) => s + r.speedup_pct, 0) / data.length).toFixed(1)
    : null

  return (
    <div>
      <PageHeader
        title="SQL Index Benchmark"
        subtitle="Measures query performance before and after applying indexes with EXPLAIN ANALYZE"
        action={
          <button className="btn-primary" onClick={runBenchmark} disabled={loading}>
            <Play size={15} />
            {loading ? 'Running…' : 'Run Benchmark'}
          </button>
        }
      />

      {/* Info card */}
      <div className="card p-5 mb-6 border-frost/10">
        <p className="font-display font-semibold text-paper text-sm mb-3">How it works</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs text-muted font-body">
          <div className="flex gap-3">
            <span className="font-display font-bold text-frost text-lg leading-none">1</span>
            <p>Drops all indexes on relevant tables to simulate a cold, unoptimised database</p>
          </div>
          <div className="flex gap-3">
            <span className="font-display font-bold text-frost text-lg leading-none">2</span>
            <p>Runs 5 production queries used by the API and records execution time via <code className="font-mono bg-white/5 px-1 rounded">EXPLAIN ANALYZE</code></p>
          </div>
          <div className="flex gap-3">
            <span className="font-display font-bold text-frost text-lg leading-none">3</span>
            <p>Applies all 20 indexes, re-runs the same queries, and compares the results</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="border border-signal/25 bg-signal/5 rounded-lg px-4 py-3 text-signal text-sm font-mono mb-6">
          {error}
        </div>
      )}

      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="w-12 h-12 rounded-full border-2 border-accent/30 border-t-accent animate-spin" />
          <p className="font-mono text-sm text-muted">Running EXPLAIN ANALYZE on 5 queries…</p>
        </div>
      )}

      {data && !loading && (
        <>
          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-4 mb-7 animate-fade-up">
            <div className="stat-card">
              <div className="flex items-center justify-between">
                <p className="text-xs font-mono text-muted uppercase tracking-wider">Queries Tested</p>
                <Zap size={15} className="text-accent" />
              </div>
              <p className="font-display font-bold text-3xl text-accent">{data.length}</p>
            </div>
            <div className="stat-card">
              <div className="flex items-center justify-between">
                <p className="text-xs font-mono text-muted uppercase tracking-wider">Total Time Saved</p>
                <Clock size={15} className="text-frost" />
              </div>
              <p className="font-display font-bold text-3xl text-frost">{totalSaved}ms</p>
            </div>
            <div className="stat-card">
              <div className="flex items-center justify-between">
                <p className="text-xs font-mono text-muted uppercase tracking-wider">Avg Speedup</p>
                <TrendingDown size={15} className="text-accent" />
              </div>
              <p className="font-display font-bold text-3xl text-accent">{avgSpeedup}%</p>
            </div>
          </div>

          {/* Bar chart comparison */}
          <div className="card p-6 mb-7 animate-fade-up">
            <p className="font-display font-semibold text-paper mb-5">Execution Time Comparison (ms)</p>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={chartData} barGap={4} barSize={20}>
                <XAxis
                  dataKey="name"
                  tick={{ fill: '#6B6B7B', fontSize: 9, fontFamily: 'JetBrains Mono' }}
                  axisLine={false} tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#6B6B7B', fontSize: 10 }}
                  axisLine={false} tickLine={false}
                  unit="ms"
                />
                <Tooltip
                  contentStyle={{ background: '#1C1C27', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, fontFamily: 'JetBrains Mono', fontSize: 11 }}
                  labelStyle={{ color: '#F2F0EB' }}
                  cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                  formatter={(v, name) => [`${v}ms`, name === 'before' ? 'Without Index' : 'With Index']}
                />
                <Legend
                  formatter={v => <span className="font-mono text-xs text-muted">{v === 'before' ? 'Without Index' : 'With Index'}</span>}
                />
                <Bar dataKey="before" fill="#FF4D6D" opacity={0.7} radius={[4,4,0,0]} />
                <Bar dataKey="after"  fill="#C8F135" opacity={0.8} radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Per-query cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {data.map((r, i) => <QueryResultCard key={i} result={r} index={i} />)}
          </div>

          {/* Indexes applied card */}
          <div className="card p-5 mt-6 animate-fade-up">
            <p className="font-display font-semibold text-paper mb-3 text-sm">Indexes Applied</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
              {[
                'idx_uploadsession_status','idx_uploadsession_deviceid',
                'idx_filemetadata_sessionid','idx_onetimetoken_tokenvalue',
                'idx_onetimetoken_status','idx_ratelimitlog_deviceid',
                'idx_ratelimitlog_eventtype','idx_integrity_verified',
                'idx_audittrail_sessionid','idx_errorlog_sessionid',
              ].map(idx => (
                <div key={idx} className="flex items-center gap-2 text-xs font-mono">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent flex-shrink-0" />
                  <span className="text-muted">{idx}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {!data && !loading && !error && (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div className="w-16 h-16 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center">
            <Zap size={28} className="text-accent" />
          </div>
          <p className="font-display font-semibold text-paper">Ready to benchmark</p>
          <p className="text-muted text-sm text-center max-w-xs">
            Click "Run Benchmark" to measure query performance before and after SQL indexing.
          </p>
        </div>
      )}
    </div>
  )
}
