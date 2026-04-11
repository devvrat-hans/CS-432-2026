"use client";

import { useState } from "react";
import { Download, Search, ShieldCheck, AlertTriangle } from "lucide-react";

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

export default function DownloadPage() {
  const [code, setCode] = useState("");
  const [checking, setChecking] = useState(false);
  const [status, setStatus] = useState<FileStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloaded, setDownloaded] = useState(false);

  const handleCheck = async () => {
    const trimmed = code.trim().toUpperCase();
    if (!trimmed) return;
    setChecking(true);
    setError(null);
    setStatus(null);
    setDownloaded(false);

    try {
      const res = await fetch(`${API_BASE}/api/public/status/${trimmed}`);
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
      setError("Network error. Could not reach the server.");
    } finally {
      setChecking(false);
    }
  };

  const handleDownload = () => {
    const trimmed = code.trim().toUpperCase();
    // Trigger download via browser navigation.
    const link = document.createElement("a");
    link.href = `${API_BASE}/api/public/download/${trimmed}`;
    link.setAttribute("download", "");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setDownloaded(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleCheck();
  };

  // ────────── POST-DOWNLOAD VIEW ──────────
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

          <button
            onClick={() => {
              setCode("");
              setStatus(null);
              setError(null);
              setDownloaded(false);
            }}
            className="border border-neutral-900 px-6 py-3 text-sm font-bold uppercase tracking-widest hover:bg-neutral-100 transition-colors"
          >
            ENTER ANOTHER CODE
          </button>
        </div>
      </div>
    );
  }

  // ────────── MAIN VIEW ──────────
  return (
    <div className="flex-1 flex items-center justify-center bg-white min-h-[calc(100vh-3.5rem)] p-8">
      <div className="max-w-lg w-full space-y-10">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-5xl font-extrabold tracking-tighter text-neutral-900 uppercase">
            RECEIVE A FILE
          </h1>
          <p className="text-sm text-neutral-500 font-medium">
            Enter the 6-character download code to retrieve your file.
          </p>
        </div>

        {/* Code input */}
        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
            DOWNLOAD CODE
          </p>
          <div className="flex border border-neutral-900">
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase().slice(0, 6))}
              onKeyDown={handleKeyDown}
              maxLength={6}
              placeholder="ABC123"
              className="flex-1 px-5 py-4 text-2xl font-extrabold tracking-[0.3em] text-neutral-900 font-mono text-center bg-white outline-none placeholder:text-neutral-300 uppercase"
            />
            <button
              onClick={handleCheck}
              disabled={code.trim().length === 0 || checking}
              className={`
                px-6 border-l border-neutral-900 transition-colors
                ${
                  code.trim().length === 0 || checking
                    ? "bg-neutral-200 text-neutral-500 cursor-not-allowed"
                    : "bg-neutral-900 text-white hover:bg-neutral-800"
                }
              `}
            >
              {checking ? (
                <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" />
              ) : (
                <Search size={20} />
              )}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="border border-neutral-900 bg-white px-5 py-4 flex items-start gap-3">
            <AlertTriangle size={18} className="text-neutral-900 mt-0.5 flex-shrink-0" />
            <p className="text-xs font-bold uppercase tracking-widest text-neutral-900">
              {error}
            </p>
          </div>
        )}

        {/* File info + download button */}
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
          </div>
        )}
      </div>
    </div>
  );
}
