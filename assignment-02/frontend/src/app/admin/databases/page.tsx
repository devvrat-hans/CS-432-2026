'use client';
import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Database, Plus, Search, Server } from 'lucide-react';

type CatalogItem = {
  name: string;
  table_count: number;
  tables: string[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8080/api';

export default function DatabasesPage() {
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [newDbName, setNewDbName] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [token, setToken] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const savedToken = window.localStorage.getItem('blinddrop_token') || '';
    setToken(savedToken);
  }, []);

  const fetchDbs = async () => {
    try {
      const localToken = window.localStorage.getItem('blinddrop_token') || '';
      const res = await fetch(`${API_BASE}/databases/catalog`, {
        headers: localToken ? { Authorization: `Bearer ${localToken}` } : undefined
      });
      if (res.ok) {
        const data = await res.json();
        setCatalog(data.catalog || []);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchDbs();
  }, []);

  const handleCreate = async () => {
    if (!newDbName.trim()) return;
    if (!token) {
      setError('Login first to create a database.');
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/databases`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ name: newDbName.trim() })
      });
      if (res.ok) {
        setNewDbName('');
        setError('');
        fetchDbs();
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.error || 'Could not create database');
      }
    } catch (err) {
      console.error(err);
      setError('Could not connect to backend');
    }
  };

  const filteredDbs = catalog.filter((item) =>
    item.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex-1 overflow-y-auto p-8 lg:p-16 bg-white min-h-full">
      <div className="max-w-6xl mx-auto space-y-16">
        {/* Header Block */}
        <div className="space-y-4">
          <div className="inline-flex px-3 py-1 bg-neutral-900 text-white text-xs font-bold tracking-widest uppercase mb-4">
            System Workspace
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tighter text-neutral-900 uppercase">
            DATABASE REGISTRY
          </h1>
          <p className="text-xl text-neutral-500 max-w-2xl leading-relaxed mt-2 font-medium">
            Manage secure, temporary file transfer records and clear traces automatically.
          </p>
        </div>

        {/* Create Database Area */}
        <div className="border border-neutral-900 p-8 space-y-6 bg-white">
          <label className="text-sm font-bold uppercase tracking-widest text-neutral-900 block">Deploy New Infrastructure</label>
          <div className="flex flex-col md:flex-row gap-4 items-end">
            <div className="flex-1 w-full relative">
              <input 
                type="text" 
                value={newDbName}
                onChange={(e) => setNewDbName(e.target.value)}
                placeholder="DATABASE IDENTIFIER (E.G. USERS_DB)"
                className="w-full px-4 py-3 bg-neutral-100 border border-neutral-900 focus:outline-none focus:bg-white transition-all text-neutral-900 font-medium placeholder:uppercase placeholder:text-sm placeholder:tracking-widest"
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              />
            </div>
            <button 
              onClick={handleCreate}
              className="w-full md:w-auto px-8 py-3 bg-neutral-900 hover:bg-neutral-800 text-white font-bold uppercase tracking-widest transition-colors flex items-center justify-center gap-2"
            >
              <Plus size={20} />
              Deploy
            </button>
          </div>
          {error && (
            <div className="p-4 bg-neutral-100 border border-neutral-900 text-neutral-900 text-sm font-bold uppercase tracking-widest mt-4">
              {error}
            </div>
          )}
        </div>

        {/* Search and Table List */}
        <div className="space-y-6">
          <div className="flex items-center gap-3 px-4 py-3 bg-white border border-neutral-900 w-full md:w-1/2">
            <Search size={18} className="text-neutral-900" />
            <input 
              type="text" 
              placeholder="SEARCH REGISTRY..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1 bg-transparent focus:outline-none text-neutral-900 placeholder:text-neutral-500 font-medium tracking-wide uppercase text-sm"
            />
          </div>

          {filteredDbs.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-0 border-t border-l border-neutral-900">
              {filteredDbs.map((item) => (
                <Link key={item.name} href={`/admin/databases/${item.name}`} className="group block bg-white p-6 border-r border-b border-neutral-900 hover:bg-neutral-900 hover:text-white transition-colors relative">
                  <div className="flex items-start gap-4">
                    <div className="p-3 bg-neutral-100 border border-neutral-900 text-neutral-900 group-hover:bg-white group-hover:text-black transition-colors">
                      <Database size={24} />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold tracking-tight uppercase">{item.name}</h3>
                      <p className="text-sm font-medium tracking-widest mt-1 text-neutral-500 group-hover:text-neutral-400 uppercase">Tables: {item.table_count}</p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-16 bg-neutral-100 border border-neutral-900">
              <Database className="mx-auto text-neutral-900 mb-4" size={48} />
              <h3 className="text-xl font-bold uppercase tracking-widest text-neutral-900">No Infrastructure Found</h3>
              <p className="text-neutral-500 mt-2 font-medium">Deploy a new database above to get started.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
