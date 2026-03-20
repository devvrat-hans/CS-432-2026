import { useEffect, useState } from 'react'
import { PageHeader, LoadingPage, EmptyState } from '../components/UI'
import api from '../api/axios'
import {
  Upload, Key, Download, Trash2, RefreshCw,
  Shield, AlertOctagon, FileCheck, Clock
} from 'lucide-react'

const ACTION_ICONS = {
  FILE_UPLOADED:        { icon: Upload,       color: 'text-accent',  bg: 'bg-accent/10' },
  TOKEN_GENERATED:      { icon: Key,          color: 'text-frost',   bg: 'bg-frost/10' },
  FILE_DOWNLOADED:      { icon: Download,     color: 'text-frost',   bg: 'bg-frost/10' },
  TOKEN_USED:           { icon: Key,          color: 'text-frost',   bg: 'bg-frost/10' },
  FILE_DELETED:         { icon: Trash2,       color: 'text-signal',  bg: 'bg-signal/10' },
  FILE_AUTO_DELETED:    { icon: Trash2,       color: 'text-signal',  bg: 'bg-signal/10' },
  SESSION_EXPIRED:      { icon: Clock,        color: 'text-muted',   bg: 'bg-white/5' },
  INTEGRITY_CHECK_FAIL: { icon: Shield,       color: 'text-signal',  bg: 'bg-signal/10' },
  RATE_LIMIT_TRIGGERED: { icon: AlertOctagon, color: 'text-signal',  bg: 'bg-signal/10' },
}

export default function AuditTrail() {
  const [rows,      setRows]      = useState([])
  const [loading,   setLoading]   = useState(true)
  const [sessionID, setSessionID] = useState('')
  const [actions,   setActions]   = useState({})

  const load = (sid = '') => {
    setLoading(true)
    const url = sid ? `/api/audittrail?sessionID=${sid}` : '/api/audittrail'
    api.get(url).then(r => {
      setRows(r.data)
      const freq = {}
      r.data.forEach(x => { freq[x.action] = (freq[x.action]||0)+1 })
      setActions(freq)
    }).finally(() => setLoading(false))
  }

  useEffect(() => load(), [])

  const handleFilter = e => {
    e.preventDefault()
    load(sessionID)
  }

  return (
    <div>
      <PageHeader title="Audit Trail" subtitle="Full lifecycle log of every session action" />

      {/* Session filter */}
      <form onSubmit={handleFilter} className="flex gap-3 mb-6">
        <input className="input max-w-xs" placeholder="Filter by Session ID…"
          value={sessionID} onChange={e => setSessionID(e.target.value)} />
        <button type="submit" className="btn-primary text-sm">Filter</button>
        {sessionID && (
          <button type="button" className="btn-ghost text-sm"
            onClick={() => { setSessionID(''); load('') }}>
            <RefreshCw size={13} /> Clear
          </button>
        )}
      </form>

      {/* Action frequency pills */}
      {!loading && Object.keys(actions).length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          {Object.entries(actions).sort((a,b) => b[1]-a[1]).map(([action, count]) => {
            const cfg = ACTION_ICONS[action] || { color: 'text-muted', bg: 'bg-white/5' }
            return (
              <span key={action} className={`inline-flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded-full border border-white/10 ${cfg.bg} ${cfg.color}`}>
                {action} <span className="opacity-60">×{count}</span>
              </span>
            )
          })}
        </div>
      )}

      {loading ? <LoadingPage /> : rows.length === 0 ? <EmptyState message="No audit records found" /> : (
        <div className="relative animate-fade-up">
          {/* Timeline line */}
          <div className="absolute left-5 top-0 bottom-0 w-px bg-white/[0.06]" />
          <div className="space-y-1">
            {rows.map((r, i) => {
              const cfg = ACTION_ICONS[r.action] || { icon: FileCheck, color: 'text-muted', bg: 'bg-white/5' }
              const Icon = cfg.icon
              return (
                <div key={r.auditid} className="flex items-start gap-4 pl-12 relative py-2 hover:bg-white/[0.02] rounded-xl transition-colors">
                  {/* Dot */}
                  <div className={`absolute left-2.5 top-3 w-5 h-5 rounded-full border border-white/10 flex items-center justify-center ${cfg.bg}`}>
                    <Icon size={10} className={cfg.color} />
                  </div>
                  <div className="flex-1 flex items-center justify-between gap-4">
                    <div>
                      <span className={`font-mono text-xs font-medium ${cfg.color}`}>{r.action}</span>
                      <span className="font-mono text-xs text-muted ml-3">Session #{r.sessionid}</span>
                    </div>
                    <span className="font-mono text-xs text-muted/60 flex-shrink-0">
                      {r.timestamp?.slice(0,19)}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
