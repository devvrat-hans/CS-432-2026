'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

type Member = {
  id: number;
  username: string;
  role: 'admin' | 'user';
  full_name: string;
  email: string;
  member_group: string;
  created_at: string;
};

type SessionMember = {
  id: number;
  username: string;
  role: 'admin' | 'user';
  full_name: string;
  email: string;
  member_group: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? (typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8080/api`
  : 'http://127.0.0.1:8080/api');

export default function MembersPage() {
  const [token, setToken] = useState('');
  const [me, setMe] = useState<SessionMember | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [newMember, setNewMember] = useState({
    username: '',
    password: '',
    full_name: '',
    email: '',
    role: 'user',
    member_group: 'general'
  });

  useEffect(() => {
    const savedToken = window.localStorage.getItem('blinddrop_token') || '';
    if (savedToken) {
      setToken(savedToken);
    }
  }, []);

  const authHeaders = useMemo(
    () => ({
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    }),
    [token]
  );

  const clearNotices = useCallback(() => {
    setError('');
    setSuccess('');
  }, []);

  const loadMeAndMembers = useCallback(async (activeToken: string) => {
    clearNotices();
    const meRes = await fetch(`${API_BASE}/auth/me`, {
      headers: {
        Authorization: `Bearer ${activeToken}`
      }
    });

    if (!meRes.ok) {
      const meData = await meRes.json().catch(() => ({}));
      setError(meData.error || 'Session validation failed');
      return;
    }

    const meData = await meRes.json();
    setMe(meData.member || null);

    const membersRes = await fetch(`${API_BASE}/members/portfolio`, {
      headers: {
        Authorization: `Bearer ${activeToken}`
      }
    });
    const membersData = await membersRes.json().catch(() => ({}));
    if (!membersRes.ok) {
      setError(membersData.error || 'Could not fetch member portfolio');
      return;
    }
    setMembers(membersData.portfolio || []);
  }, [clearNotices]);

  useEffect(() => {
    if (!token) {
      setMe(null);
      setMembers([]);
      return;
    }
    loadMeAndMembers(token).catch(() => setError('Failed to fetch member data'));
  }, [token, loadMeAndMembers]);

  const handleCreateMember = async () => {
    clearNotices();
    const res = await fetch(`${API_BASE}/members`, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify(newMember)
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(data.error || 'Member creation failed');
      return;
    }

    setSuccess('Member created');
    setNewMember({
      username: '',
      password: '',
      full_name: '',
      email: '',
      role: 'user',
      member_group: 'general'
    });
    await loadMeAndMembers(token);
  };

  const handleDeleteMember = async (id: number) => {
    clearNotices();
    const res = await fetch(`${API_BASE}/members/${id}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(data.error || 'Delete failed');
      return;
    }
    setSuccess('Member deleted');
    await loadMeAndMembers(token);
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 lg:p-16 bg-white min-h-full">
      <div className="max-w-6xl mx-auto space-y-16">
        
        {/* Header Block */}
        <div className="space-y-4">
          <div className="inline-flex px-3 py-1 bg-neutral-900 text-white text-xs font-bold tracking-widest uppercase mb-4">
            Security Module
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tighter text-neutral-900 uppercase">
            MEMBER PORTFOLIO
          </h1>
          <p className="text-xl text-neutral-500 max-w-2xl leading-relaxed mt-2 font-medium">
            Govern temporary transfer access and maintain strict privacy policies for public stations.
            {me && ` Authenticated as ${me.username.toUpperCase()} [${me.role.toUpperCase()}]`}
          </p>
        </div>

        {error && (
          <div className="border border-neutral-900 bg-neutral-100 p-4 text-sm font-bold uppercase tracking-widest text-neutral-900">
            {error}
          </div>
        )}
        {success && (
          <div className="border border-neutral-900 bg-neutral-900 text-white p-4 text-sm font-bold uppercase tracking-widest">
            {success}
          </div>
        )}

        {me?.role === 'admin' && (
          <div className="border border-neutral-900 p-8 space-y-6 bg-white">
            <h2 className="text-xl font-bold uppercase tracking-widest text-neutral-900 border-b border-neutral-200 pb-4">Initialize Member</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <input
                className="px-4 py-3 bg-neutral-100 border border-neutral-900 focus:outline-none focus:bg-white text-neutral-900 font-medium placeholder:uppercase placeholder:text-sm placeholder:tracking-widest"
                placeholder="USERNAME"
                value={newMember.username}
                onChange={(e) => setNewMember((prev) => ({ ...prev, username: e.target.value }))}
              />
              <input
                className="px-4 py-3 bg-neutral-100 border border-neutral-900 focus:outline-none focus:bg-white text-neutral-900 font-medium placeholder:uppercase placeholder:text-sm placeholder:tracking-widest"
                placeholder="PASSWORD"
                type="password"
                value={newMember.password}
                onChange={(e) => setNewMember((prev) => ({ ...prev, password: e.target.value }))}
              />
              <input
                className="px-4 py-3 bg-neutral-100 border border-neutral-900 focus:outline-none focus:bg-white text-neutral-900 font-medium placeholder:uppercase placeholder:text-sm placeholder:tracking-widest"
                placeholder="FULL NAME"
                value={newMember.full_name}
                onChange={(e) => setNewMember((prev) => ({ ...prev, full_name: e.target.value }))}
              />
              <input
                className="px-4 py-3 bg-neutral-100 border border-neutral-900 focus:outline-none focus:bg-white text-neutral-900 font-medium placeholder:uppercase placeholder:text-sm placeholder:tracking-widest"
                placeholder="EMAIL"
                value={newMember.email}
                onChange={(e) => setNewMember((prev) => ({ ...prev, email: e.target.value }))}
              />
              <input
                className="px-4 py-3 bg-neutral-100 border border-neutral-900 focus:outline-none focus:bg-white text-neutral-900 font-medium placeholder:uppercase placeholder:text-sm placeholder:tracking-widest"
                placeholder="GROUP"
                value={newMember.member_group}
                onChange={(e) => setNewMember((prev) => ({ ...prev, member_group: e.target.value }))}
              />
              <div className="relative border border-neutral-900 bg-neutral-100 focus-within:bg-white text-neutral-900 font-medium uppercase text-sm tracking-widest">
                <select
                  className="w-full px-4 py-3 bg-transparent focus:outline-none appearance-none cursor-pointer relative z-10"
                  value={newMember.role}
                  onChange={(e) => setNewMember((prev) => ({ ...prev, role: e.target.value as 'user' | 'admin' }))}
                >
                  <option value="user">USER</option>
                  <option value="admin">ADMIN</option>
                </select>
                <div className="absolute top-0 right-0 bottom-0 flex items-center px-4 border-l border-neutral-900 bg-neutral-200 z-0 pointer-events-none">
                  <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/></svg>
                </div>
              </div>
            </div>
            <button onClick={handleCreateMember} className="px-8 py-3 bg-neutral-900 hover:bg-neutral-800 text-white font-bold uppercase tracking-widest transition-colors w-full md:w-auto">
              DEPLOY MEMBER
            </button>
          </div>
        )}

        <div className="border border-neutral-900 bg-white flex flex-col">
          <div className="p-6 md:p-8 flex items-center justify-between border-b border-neutral-900">
            <h2 className="text-xl font-bold uppercase tracking-wide text-neutral-900">VISIBLE PROFILES</h2>
            <span className="text-sm font-bold tracking-widest uppercase text-neutral-500">COUNT: {members.length}</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm font-medium text-left">
              <thead className="bg-neutral-100 border-b border-neutral-900 uppercase tracking-wider text-neutral-900 text-xs font-bold">
                <tr>
                  <th className="px-6 py-4">ID</th>
                  <th className="px-6 py-4">NAME</th>
                  <th className="px-6 py-4">USERNAME</th>
                  <th className="px-6 py-4">ROLE</th>
                  <th className="px-6 py-4">EMAIL</th>
                  <th className="px-6 py-4">GROUP</th>
                  <th className="px-6 py-4">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200">
                {members.map((member) => (
                  <tr key={member.id} className="hover:bg-neutral-50 transition-colors">
                    <td className="px-6 py-4 font-bold text-neutral-900">{member.id}</td>
                    <td className="px-6 py-4 text-neutral-600">{member.full_name}</td>
                    <td className="px-6 py-4 text-neutral-600">{member.username}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-[10px] font-bold tracking-widest uppercase border ${member.role === 'admin' ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-900 bg-white text-neutral-900'}`}>
                        {member.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-neutral-600">{member.email}</td>
                    <td className="px-6 py-4 text-neutral-600 uppercase text-xs">{member.member_group || '-'}</td>
                    <td className="px-6 py-4">
                      {me?.role === 'admin' && me.id !== member.id ? (
                        <button
                          onClick={() => handleDeleteMember(member.id)}
                          className="px-3 py-1.5 border border-neutral-900 hover:bg-neutral-900 hover:text-white transition-colors text-xs font-bold tracking-widest uppercase"
                        >
                          DELETE
                        </button>
                      ) : (
                        <span className="text-neutral-400 font-bold uppercase text-xs tracking-widest">LOCKED</span>
                      )}
                    </td>
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