import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Eye, EyeOff, ArrowRight, Lock } from 'lucide-react'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw,   setShowPw]   = useState(false)
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)
  const { login } = useAuth()
  const navigate  = useNavigate()

  const handleSubmit = async e => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left panel */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 bg-ghost border-r border-white/[0.06] p-12">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-accent flex items-center justify-center glow-accent">
            <span className="text-ink font-display font-black text-base">BD</span>
          </div>
          <span className="font-display font-bold text-paper text-lg">Blind Drop</span>
        </div>

        <div>
          <h2 className="font-display font-bold text-5xl text-paper leading-tight mb-6">
            Transfer files.<br />
            Leave <span className="text-gradient">no trace.</span>
          </h2>
          <p className="text-muted font-body text-base leading-relaxed max-w-sm">
            Privacy-focused file transfer for public computers. No login on the sender side, no credentials exposed — just a one-time token.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Sessions', val: '20' },
            { label: 'Files',    val: '25' },
            { label: 'Devices',  val: '12' },
          ].map(s => (
            <div key={s.label} className="border border-white/[0.07] rounded-xl p-4">
              <p className="font-display font-bold text-2xl text-accent">{s.val}</p>
              <p className="font-mono text-xs text-muted mt-0.5">{s.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <div className="inline-flex items-center gap-2 border border-accent/25 bg-accent/5 rounded-full px-3 py-1 mb-5">
              <Lock size={11} className="text-accent" />
              <span className="font-mono text-xs text-accent">Secure Portal</span>
            </div>
            <h1 className="font-display font-bold text-3xl text-paper mb-1.5">Welcome back</h1>
            <p className="text-muted text-sm">Sign in to access the Blind Drop admin panel.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-muted mb-1.5 uppercase tracking-wider">Username</label>
              <input
                className="input"
                placeholder="admin"
                value={username}
                onChange={e => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-muted mb-1.5 uppercase tracking-wider">Password</label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  className="input pr-10"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-paper transition-colors"
                  onClick={() => setShowPw(p => !p)}
                >
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="border border-signal/25 bg-signal/5 rounded-lg px-4 py-2.5 text-signal text-xs font-mono">
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full justify-center py-3 mt-2">
              {loading ? 'Signing in…' : <><span>Sign in</span><ArrowRight size={15} /></>}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-muted font-mono">
            Default: <span className="text-paper/60">admin</span> / <span className="text-paper/60">password123</span>
          </p>
        </div>
      </div>
    </div>
  )
}
