'use client';
import React, { useState, useEffect, use } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8080/api';

export default function TableDetailsPage({
  params
}: {
  params: Promise<{ dbName: string; tableName: string }>;
}) {
  const { dbName, tableName } = use(params);
  
  const [records, setRecords] = useState<any[]>([]);
  const [newRecordJson, setNewRecordJson] = useState('{\n  "id": "1",\n  "name": "example",\n  "value": "data"\n}');
  const [error, setError] = useState('');
  const [token, setToken] = useState('');

  useEffect(() => {
    const savedToken = window.localStorage.getItem('blinddrop_token') || '';
    setToken(savedToken);
  }, []);

  const fetchRecords = React.useCallback(async () => {
    try {
      const localToken = window.localStorage.getItem('blinddrop_token') || '';
      const res = await fetch(`${API_BASE}/databases/${dbName}/tables/${tableName}/records`, {
        headers: localToken ? { Authorization: `Bearer ${localToken}` } : undefined
      });
      if (res.ok) {
        const data = await res.json();
        setRecords(data.records || []);
      }
    } catch (err) {
      console.error(err);
    }
  }, [dbName, tableName]);

  useEffect(() => {
    if (dbName && tableName) {
      fetchRecords();
    }
  }, [dbName, tableName, fetchRecords]);

  const handleCreateRecord = async () => {
    if (!token) return;
    try {
      const parsed = JSON.parse(newRecordJson);
      const res = await fetch(`${API_BASE}/databases/${dbName}/tables/${tableName}/records`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(parsed)
      });
      if (res.ok) {
        setError('');
        fetchRecords();
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.error || 'Could not create record');
      }
    } catch (err: any) {
      setError('Invalid JSON or connection failed: ' + err.message);
    }
  };

  const handleDeleteRecord = async (record: any) => {
    if (!token) return;
    try {
      // Find the ID. It might be 'id', 'memberID', etc.
      // We will try extracting the first key's value to delete
      const keys = Object.keys(record.data);
      if (keys.length === 0) return;
      const recordId = record.data[keys[0]]; // assuming first key is search key

      const res = await fetch(`${API_BASE}/databases/${dbName}/tables/${tableName}/records/${recordId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      if (res.ok) {
        fetchRecords();
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.error || 'Could not delete record');
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 lg:p-16 bg-white min-h-full">
      <div className="max-w-6xl mx-auto space-y-16">
        
        {/* Header */}
        <div className="space-y-4">
          <div className="flex items-center gap-4 text-sm font-bold uppercase tracking-widest text-neutral-500 mb-4">
            <Link href="/admin/databases" className="hover:text-black transition-colors">REGISTRY</Link>
            <span>/</span>
            <Link href={`/admin/databases/${dbName}`} className="hover:text-black transition-colors">{dbName}</Link>
            <span>/</span>
            <span className="text-black">{tableName}</span>
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tighter text-neutral-900 uppercase">
            {tableName}
          </h1>
          <p className="text-xl text-neutral-500 max-w-2xl leading-relaxed mt-2 font-medium">
            Manage records directly in the data structure.
          </p>
        </div>

        {error && (
          <div className="border border-neutral-900 bg-neutral-100 p-4 text-sm font-bold uppercase tracking-widest text-neutral-900">
            {error}
          </div>
        )}

        <div className="border border-neutral-900 p-8 space-y-6 bg-white">
          <h2 className="text-xl font-bold uppercase tracking-wide text-neutral-900">NEW RECORD (JSON)</h2>
          <div className="flex flex-col md:flex-row gap-4">
            <textarea
              rows={4}
              value={newRecordJson}
              onChange={(e) => setNewRecordJson(e.target.value)}
              className="flex-1 px-4 py-3 bg-neutral-100 border border-neutral-900 focus:outline-none focus:bg-white text-neutral-900 font-mono text-sm"
            />
            <button
              onClick={handleCreateRecord}
              className="px-8 py-3 bg-neutral-900 hover:bg-neutral-800 text-white font-bold uppercase tracking-widest transition-colors whitespace-nowrap h-fit"
            >
              INSERT
            </button>
          </div>
        </div>

        <div className="border border-neutral-900 flex flex-col bg-white">
          <div className="p-6 md:p-8 flex items-center justify-between border-b border-neutral-900 gap-4">
            <h2 className="text-xl font-bold uppercase tracking-wide text-neutral-900">RECORDS</h2>
            <span className="text-sm font-bold tracking-widest uppercase text-neutral-500 border border-neutral-200 px-3 py-1">
              TOTAL: {records.length}
            </span>
          </div>

          {records.length === 0 ? (
            <div className="p-8 text-center text-sm font-bold tracking-widest uppercase text-neutral-500">
              No records found.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm font-medium text-left">
                <thead className="bg-neutral-100 border-b border-neutral-900 uppercase tracking-wider text-neutral-900 text-xs font-bold">
                  <tr>
                    <th className="px-6 py-4">DATA (JSON)</th>
                    <th className="px-6 py-4 w-32">ACTIONS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200">
                  {records.map((r, i) => (
                    <tr key={i} className="hover:bg-neutral-50 transition-colors">
                      <td className="px-6 py-4">
                        <pre className="text-xs text-neutral-600">
                          {JSON.stringify(r.data, null, 2)}
                        </pre>
                      </td>
                      <td className="px-6 py-4">
                        <button
                          onClick={() => handleDeleteRecord(r)}
                          className="px-3 py-1 border border-red-200 text-red-600 hover:bg-red-50 transition-colors text-xs font-bold tracking-widest uppercase"
                        >
                          DELETE
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Tree Visualization */}
        <div className="border border-neutral-900 p-8 bg-white flex flex-col items-center">
             <h2 className="text-xl font-bold uppercase tracking-wide text-neutral-900 mb-6 self-start">B+ TREE VISUALIZATION</h2>
             {/* eslint-disable-next-line @next/next/no-img-element */}
             <img 
               src={`${API_BASE}/databases/${dbName}/tables/${tableName}/visualize`} 
               alt="B+ Tree Visualization" 
               className="max-w-full"
             />
        </div>

      </div>
    </div>
  );
}