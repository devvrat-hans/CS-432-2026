'use client';
import React, { useState, useEffect, use } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? (typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8080/api`
  : 'http://127.0.0.1:8080/api');

export default function DatabaseTablesPage({ params }: { params: Promise<{ dbName: string }> }) {
  const { dbName } = use(params);
  const [tables, setTables] = useState<string[]>([]);
  const [newTableName, setNewTableName] = useState('');
  const [error, setError] = useState('');
  const [token, setToken] = useState('');

  useEffect(() => {
    const savedToken = window.localStorage.getItem('blinddrop_token') || '';
    setToken(savedToken);
  }, []);

  const fetchTables = React.useCallback(async () => {
    try {
      const localToken = window.localStorage.getItem('blinddrop_token') || '';
      const res = await fetch(`${API_BASE}/databases/${dbName}/tables`, {
        headers: localToken ? { Authorization: `Bearer ${localToken}` } : undefined
      });
      if (res.ok) {
        const data = await res.json();
        setTables(data.tables || []);
      }
    } catch (err) {
      console.error(err);
    }
  }, [dbName]);

  useEffect(() => {
    if (dbName) {
      fetchTables();
    }
  }, [dbName, fetchTables]);

  const handleCreateTable = async () => {
    if (!newTableName.trim() || !token) return;
    try {
      const res = await fetch(`${API_BASE}/databases/${dbName}/tables`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ name: newTableName.trim(), schema: ['id', 'name', 'value'] })
      });
      if (res.ok) {
        setNewTableName('');
        setError('');
        fetchTables();
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.error || 'Could not create table');
      }
    } catch (err) {
      setError('Could not connect to backend');
    }
  };

  const handleDeleteTable = async (t: string) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/databases/${dbName}/tables/${t}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      if (res.ok) {
        fetchTables();
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.error || 'Could not delete table');
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 lg:p-16 bg-white min-h-full">
      <div className="max-w-6xl mx-auto space-y-16">
        {/* Header Block */}
        <div className="space-y-4">
          <div className="flex items-center gap-4 text-sm font-bold uppercase tracking-widest text-neutral-500 mb-4">
            <Link href="/admin/databases" className="hover:text-black transition-colors">REGISTRY</Link>
            <span>/</span>
            <span className="text-black">{dbName}</span>
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tighter text-neutral-900 uppercase">
            {dbName} WORKSPACE
          </h1>
          <p className="text-xl text-neutral-500 max-w-2xl leading-relaxed mt-2 font-medium">
            Manage data structures within the selected infrastructure.
          </p>
        </div>

        {error && (
          <div className="border border-neutral-900 bg-neutral-100 p-4 text-sm font-bold uppercase tracking-widest text-neutral-900">
            {error}
          </div>
        )}

        {/* Create Table Area */}
        <div className="border border-neutral-900 p-8 space-y-6 bg-white">
          <h2 className="text-xl font-bold uppercase tracking-wide text-neutral-900">NEW TABLE</h2>
          <div className="flex flex-col md:flex-row gap-4">
            <input
              type="text"
              placeholder="TABLE_NAME"
              value={newTableName}
              onChange={(e) => setNewTableName(e.target.value)}
              className="flex-1 px-4 py-3 bg-neutral-100 border border-neutral-900 focus:outline-none focus:bg-white text-neutral-900 font-bold uppercase tracking-widest placeholder:text-neutral-400"
            />
            <button
              onClick={handleCreateTable}
              className="px-8 py-3 bg-neutral-900 hover:bg-neutral-800 text-white font-bold uppercase tracking-widest transition-colors whitespace-nowrap"
            >
              INITIALIZE TABLE
            </button>
          </div>
        </div>

        {/* Tables */}
        <div className="border border-neutral-900 flex flex-col bg-white overflow-hidden">
          <div className="p-6 md:p-8 flex items-center justify-between border-b border-neutral-900 gap-4">
            <h2 className="text-xl font-bold uppercase tracking-wide text-neutral-900">TABLE REGISTRY</h2>
            <span className="text-sm font-bold tracking-widest uppercase text-neutral-500 border border-neutral-200 px-3 py-1">
              TOTAL: {tables.length}
            </span>
          </div>

          {tables.length === 0 ? (
            <div className="p-8 text-center text-sm font-bold tracking-widest uppercase text-neutral-500">
              No tables instantiated.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 -mr-px -mb-px">
              {tables.map((t, idx) => (
                <div key={`${t}-${idx}`} className="bg-white p-6 md:p-8 flex flex-col justify-between group hover:bg-neutral-50 transition-colors border-r border-b border-neutral-900">
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <h3 className="text-xl font-bold text-neutral-900 uppercase tracking-wide truncate">
                        {t}
                      </h3>
                    </div>
                  </div>
                  <div className="mt-8 flex gap-3">
                    <Link
                      href={`/admin/databases/${dbName}/${t}`}
                      className="flex-1 text-center px-4 py-2 border border-neutral-900 text-neutral-900 hover:bg-neutral-900 hover:text-white transition-colors text-xs font-bold tracking-widest uppercase"
                    >
                      EXPLORE
                    </Link>
                    <button
                      onClick={() => handleDeleteTable(t)}
                      className="px-4 py-2 border border-red-200 text-red-600 hover:bg-red-50 transition-colors text-xs font-bold tracking-widest uppercase"
                    >
                      DELETE
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}