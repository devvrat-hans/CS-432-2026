"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import { Download, ShieldCheck, AlertTriangle, Loader2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface FileStatus {
  valid: boolean;
  file_name?: string;
  file_size?: number;
  expires_at?: string;
  reason?: string;
}

export default function DirectDownloadPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = use(params);
  const upperCode = code.toUpperCase();

  const [checking, setChecking] = useState(true);
  const [status, setStatus] = useState<FileStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloaded, setDownloaded] = useState(false);

  // Auto-check status on page load.
  useEffect(() => {
    let cancelled = false;

    async function checkStatus() {
      setChecking(true);
      setError(null);
      setStatus(null);

      try {
        const res = await fetch(`${API_BASE}/api/public/status/${upperCode}`);
        if (cancelled) return;

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          setError(data.error || "Could not check the code.");
          return;
        }

        const data: FileStatus = await res.json();
        if (!data.valid) {
          setError(data.reason || "This code is invalid or has expired.");
        } else {
          setStatus(data);
        }
      } catch {
        if (!cancelled) {
          setError("Network error. Could not reach the server.");
        }
      } finally {
        if (!cancelled) setChecking(false);
      }
    }

    checkStatus();
    return () => {
      cancelled = true;
    };
  }, [upperCode]);

  const handleDownload = () => {
    const link = document.createElement("a");
    link.href = `${API_BASE}/api/public/download/${upperCode}`;
    link.setAttribute("download", "");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setDownloaded(true);
  };

  // ────────── POST-DOWNLOAD ──────────
  if (downloaded) {
    return (
      <div className="flex-1 flex items-center justify-center bg-white min-h-[calc(100vh-3.5rem)] p-8">
        <div className="max-w-md w-full space-y-10 text-center">
          <div className="flex justify-center">
            <div className="p-4 border border-neutral-900 bg-neutral-100">
              <ShieldCheck size={32} className="text-neutral-900" />
            </div>
          </div>
          <div className="space-y-4">
            <h2 className="text-3xl font-extrabold tracking-tighter text-neutral-900 uppercase">
              DOWNLOAD STARTED
            </h2>
            <p className="text-sm font-bold uppercase tracking-widest text-neutral-500 leading-relaxed">
              File securely deleted from our servers.
            </p>
          </div>
          <Link
            href="/download"
            className="inline-block border border-neutral-900 px-6 py-3 text-sm font-bold uppercase tracking-widest hover:bg-neutral-100 transition-colors"
          >
            ENTER ANOTHER CODE
          </Link>
        </div>
      </div>
    );
  }

  // ────────── LOADING ──────────
  if (checking) {
    return (
      <div className="flex-1 flex items-center justify-center bg-white min-h-[calc(100vh-3.5rem)] p-8">
        <div className="max-w-md w-full space-y-8 text-center">
          <Loader2 size={32} className="text-neutral-900 animate-spin mx-auto" />
          <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
            CHECKING CODE {upperCode}...
          </p>
        </div>
      </div>
    );
  }

  // ────────── ERROR ──────────
  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center bg-white min-h-[calc(100vh-3.5rem)] p-8">
        <div className="max-w-md w-full space-y-10 text-center">
          <div className="flex justify-center">
            <div className="p-4 border border-neutral-900 bg-neutral-100">
              <AlertTriangle size={32} className="text-neutral-900" />
            </div>
          </div>
          <div className="space-y-4">
            <h2 className="text-3xl font-extrabold tracking-tighter text-neutral-900 uppercase">
              INVALID CODE
            </h2>
            <p className="text-sm font-bold uppercase tracking-widest text-neutral-500">
              {error}
            </p>
          </div>
          <Link
            href="/download"
            className="inline-block border border-neutral-900 px-6 py-3 text-sm font-bold uppercase tracking-widest hover:bg-neutral-100 transition-colors"
          >
            TRY ANOTHER CODE
          </Link>
        </div>
      </div>
    );
  }

  // ────────── READY TO DOWNLOAD ──────────
  return (
    <div className="flex-1 flex items-center justify-center bg-white min-h-[calc(100vh-3.5rem)] p-8">
      <div className="max-w-md w-full space-y-10">
        <div className="text-center space-y-4">
          <span className="inline-block bg-neutral-900 text-white text-xs font-bold tracking-widest uppercase px-4 py-1">
            BLIND DROP
          </span>
          <h1 className="text-4xl font-extrabold tracking-tighter text-neutral-900 uppercase">
            FILE READY
          </h1>
          <p className="text-lg font-extrabold tracking-[0.3em] text-neutral-900 font-mono">
            {upperCode}
          </p>
        </div>

        {status && (
          <div className="space-y-6">
            <div className="border border-neutral-900 bg-white divide-y divide-neutral-200">
              <div className="flex justify-between px-5 py-3">
                <span className="text-xs font-bold uppercase tracking-widest text-neutral-500">
                  FILE
                </span>
                <span className="text-xs font-bold uppercase tracking-widest text-neutral-900 truncate max-w-[240px]">
                  {status.file_name}
                </span>
              </div>
              <div className="flex justify-between px-5 py-3">
                <span className="text-xs font-bold uppercase tracking-widest text-neutral-500">
                  SIZE
                </span>
                <span className="text-xs font-bold uppercase tracking-widest text-neutral-900">
                  {formatSize(status.file_size || 0)}
                </span>
              </div>
            </div>

            <button
              onClick={handleDownload}
              className="w-full py-4 text-sm font-bold uppercase tracking-widest bg-neutral-900 text-white border border-neutral-900 hover:bg-neutral-800 transition-colors inline-flex items-center justify-center gap-3"
            >
              <Download size={18} />
              DOWNLOAD
            </button>

            <p className="text-xs font-bold uppercase tracking-widest text-neutral-500 text-center leading-relaxed">
              This code works once. The file is deleted after download.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
