import { useEffect, useState } from 'react'
import { PageHeader, LoadingPage, EmptyState, RoleBadge, ConfirmModal, Modal } from '../components/UI'
import api from '../api/axios'
import { Plus, Trash2, ShieldCheck, ShieldOff, Users } from 'lucide-react'

export default function UsersPage() {
  const [users,    setUsers]    = useState([])
  const [groups,   setGroups]   = useState([])
  const [loading,  setLoading]  = useState(true)
  const [toDelete, setToDelete] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [changing, setChanging] = useState(null) // { uid, role }
  const [form,     setForm]     = useState({ username:'', password:'', role:'user', memberID:'' })
  const [saving,   setSaving]   = useState(false)
  const [err,      setErr]      = useState('')

  const load = () => {
    setLoading(true)
    Promise.all([api.get('/api/users'), api.get('/api/groups')])
      .then(([u, g]) => { setUsers(u.data); setGroups(g.data) })
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const handleCreate = async e => {
    e.preventDefault(); setErr(''); setSaving(true)
    try {
      await api.post('/api/users', { ...form, memberID: form.memberID ? +form.memberID : null })
      setShowForm(false); setForm({ username:'', password:'', role:'user', memberID:'' }); load()
    } catch(e) { setErr(e.response?.data?.error || 'Error') }
    finally { setSaving(false) }
  }

  const handleRoleToggle = async (uid, currentRole) => {
    const newRole = currentRole === 'admin' ? 'user' : 'admin'
    await api.put(`/api/users/${uid}/role`, { role: newRole })
    load()
  }

  return (
    <div>
      <PageHeader
        title="Users & RBAC"
        subtitle="Manage login accounts, roles, and group memberships"
        action={<button className="btn-primary" onClick={() => setShowForm(true)}><Plus size={15} /> Add User</button>}
      />

      {/* Groups summary */}
      {groups.length > 0 && (
        <div className="flex gap-3 mb-6">
          {groups.map(g => (
            <div key={g.groupid} className="card px-4 py-3 flex items-center gap-2.5">
              <Users size={14} className="text-frost" />
              <div>
                <p className="font-display font-medium text-paper text-xs">{g.groupname}</p>
                <p className="font-mono text-[10px] text-muted">Group #{g.groupid}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {loading ? <LoadingPage /> : users.length === 0 ? <EmptyState /> : (
        <div className="table-wrap animate-fade-up">
          <table className="data-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Linked Member</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.userid}>
                  <td>
                    <div className="flex items-center gap-2.5">
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-display font-bold ${
                        u.role === 'admin' ? 'bg-signal/15 text-signal' : 'bg-white/10 text-paper/60'
                      }`}>
                        {u.username?.[0]?.toUpperCase()}
                      </div>
                      <span className="font-mono text-xs">{u.username}</span>
                    </div>
                  </td>
                  <td className="text-sm">{u.name || <span className="text-muted">—</span>}</td>
                  <td><span className="font-mono text-xs text-muted">{u.email || '—'}</span></td>
                  <td><RoleBadge role={u.role} /></td>
                  <td>
                    {u.isactive
                      ? <span className="badge-active">ACTIVE</span>
                      : <span className="badge-expired">INACTIVE</span>
                    }
                  </td>
                  <td><span className="font-mono text-xs text-muted">{u.createdat?.slice(0,10)}</span></td>
                  <td>
                    <div className="flex items-center gap-2">
                      <button
                        title={`Switch to ${u.role === 'admin' ? 'user' : 'admin'}`}
                        onClick={() => handleRoleToggle(u.userid, u.role)}
                        className={`p-1.5 rounded-lg border transition-all hover:bg-white/5 ${
                          u.role === 'admin' ? 'border-signal/20 text-signal' : 'border-accent/20 text-accent'
                        }`}
                      >
                        {u.role === 'admin' ? <ShieldOff size={13} /> : <ShieldCheck size={13} />}
                      </button>
                      <button className="btn-danger py-1 px-2" onClick={() => setToDelete(u)}>
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* RBAC explanation card */}
      <div className="card p-5 mt-6 border-frost/10 animate-fade-up">
        <p className="font-display font-semibold text-paper mb-3 text-sm">Role Permissions</p>
        <div className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <p className="font-mono text-signal mb-2 flex items-center gap-1.5"><ShieldCheck size={12} /> Admin</p>
            <ul className="space-y-1 text-muted">
              {['Full CRUD on all tables','Manage users & roles','View audit trail & errors','Run performance benchmarks','Delete members / devices'].map(p => (
                <li key={p} className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-signal/60 flex-shrink-0" />{p}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="font-mono text-paper/60 mb-2 flex items-center gap-1.5"><ShieldOff size={12} /> Regular User</p>
            <ul className="space-y-1 text-muted">
              {['View own profile only','Read sessions, files, tokens','View downloads & integrity','Cannot delete/create records','No access to admin pages'].map(p => (
                <li key={p} className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-white/20 flex-shrink-0" />{p}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Create user modal */}
      <Modal open={showForm} onClose={() => setShowForm(false)} title="Create User Account">
        <form onSubmit={handleCreate} className="space-y-3">
          <div>
            <label className="block text-xs font-mono text-muted mb-1 uppercase tracking-wider">Username</label>
            <input className="input" value={form.username} onChange={e => setForm(p=>({...p,username:e.target.value}))} required />
          </div>
          <div>
            <label className="block text-xs font-mono text-muted mb-1 uppercase tracking-wider">Password</label>
            <input type="password" className="input" value={form.password} onChange={e => setForm(p=>({...p,password:e.target.value}))} required />
          </div>
          <div>
            <label className="block text-xs font-mono text-muted mb-1 uppercase tracking-wider">Role</label>
            <select className="input" value={form.role} onChange={e => setForm(p=>({...p,role:e.target.value}))}>
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-mono text-muted mb-1 uppercase tracking-wider">Linked Member ID (optional)</label>
            <input type="number" className="input" placeholder="Leave blank for standalone admin"
              value={form.memberID} onChange={e => setForm(p=>({...p,memberID:e.target.value}))} />
          </div>
          {err && <p className="text-signal text-xs font-mono">{err}</p>}
          <div className="flex gap-3 pt-2 justify-end">
            <button type="button" className="btn-ghost text-sm" onClick={() => setShowForm(false)}>Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary text-sm">{saving?'Creating…':'Create'}</button>
          </div>
        </form>
      </Modal>

      <ConfirmModal
        open={!!toDelete} onClose={() => setToDelete(null)}
        onConfirm={() => api.delete(`/api/users/${toDelete.userid}`).then(() => { setToDelete(null); load() })}
        message={`Delete user "${toDelete?.username}"? They will lose access immediately.`}
      />
    </div>
  )
}
