"use client";

import { useState, useEffect } from "react";
import { Copy, Check } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import UploadDropzone from "@/components/UploadDropzone";

const EXPIRY_OPTIONS = [
  { label: "15 MIN", value: 15 },
  { label: "30 MIN", value: 30 },
  { label: "1 HOUR", value: 60 },
  { label: "24 HOURS", value: 1440 },
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface UploadResult {
  download_code: string;
  expires_at: string;
  file_name: string;
  file_size: number;
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [expiryMinutes, setExpiryMinutes] = useState(30);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [copied, setCopied] = useState(false);
  const [countdown, setCountdown] = useState("");

  // -- Countdown timer --
  useEffect(() => {
    if (!result) return;
    const expiresAt = new Date(result.expires_at).getTime();

    const tick = () => {
      const remaining = expiresAt - Date.now();
      if (remaining <= 0) {
        setCountdown("EXPIRED");
        return;
      }
      const h = Math.floor(remaining / 3600000);
      const m = Math.floor((remaining % 3600000) / 60000);
      const s = Math.floor((remaining % 60000) / 1000);
      setCountdown(
        h > 0 ? `${h}h ${m}m ${s}s` : m > 0 ? `${m}m ${s}s` : `${s}s`
      );
    };

    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [result]);

  // -- Upload with XHR for progress tracking --
  const handleUpload = () => {
    if (!file) return;
    setUploading(true);
    setUploadProgress(0);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("expires_in_minutes", String(expiryMinutes));

    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        setUploadProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      setUploading(false);
      setUploadProgress(null);

      if (xhr.status === 413) {
        setError("File exceeds the 100 MB size limit.");
        return;
      }
      if (xhr.status === 429) {
        setError("Upload rate limit exceeded. Please try again later.");
        return;
      }

      let data: UploadResult;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        setError("Upload failed. Invalid server response.");
        return;
      }

      if (xhr.status !== 201) {
        setError((data as unknown as { error?: string }).error || "Upload failed.");
        return;
      }

      setResult(data);
    });

    xhr.addEventListener("error", () => {
      setUploading(false);
      setUploadProgress(null);
      setError("Network error. Could not reach the server.");
    });

    xhr.addEventListener("abort", () => {
      setUploading(false);
      setUploadProgress(null);
    });

    xhr.open("POST", `${API_BASE}/api/public/upload`);
    xhr.send(formData);
  };

  // -- Copy code --
  const copyCode = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(result.download_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ────────── SUCCESS VIEW ──────────
  if (result) {
    return (
      <div className="flex-1 flex items-center justify-center bg-white min-h-[calc(100vh-3.5rem)] p-8">
        <div className="max-w-md w-full space-y-10 text-center">
          <span className="inline-block bg-neutral-900 text-white text-xs font-bold tracking-widest uppercase px-4 py-1">
            UPLOAD COMPLETE
          </span>

          <div className="space-y-4">
            <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
              YOUR DOWNLOAD CODE
            </p>
            <p className="text-7xl font-extrabold tracking-[0.3em] text-neutral-900 font-mono">
              {result.download_code}
            </p>
            <button
              onClick={copyCode}
              className="inline-flex items-center gap-2 border border-neutral-900 px-5 py-2 text-sm font-bold uppercase tracking-widest hover:bg-neutral-100 transition-colors"
            >
              {copied ? (
                <>
                  <Check size={14} /> COPIED
                </>
              ) : (
                <>
                  <Copy size={14} /> COPY CODE
                </>
              )}
            </button>
          </div>

          <div className="border border-neutral-900 bg-white divide-y divide-neutral-200">
            <div className="flex justify-between px-5 py-3">
              <span className="text-xs font-bold uppercase tracking-widest text-neutral-500">
                FILE
              </span>
              <span className="text-xs font-bold uppercase tracking-widest text-neutral-900 truncate max-w-[200px]">
                {result.file_name}
              </span>
            </div>
            <div className="flex justify-between px-5 py-3">
              <span className="text-xs font-bold uppercase tracking-widest text-neutral-500">
                SIZE
              </span>
              <span className="text-xs font-bold uppercase tracking-widest text-neutral-900">
                {formatSize(result.file_size)}
              </span>
            </div>
            <div className="flex justify-between px-5 py-3">
              <span className="text-xs font-bold uppercase tracking-widest text-neutral-500">
                EXPIRES IN
              </span>
              <span className="text-xs font-bold uppercase tracking-widest text-neutral-900">
                {countdown}
              </span>
            </div>
          </div>

          <div className="flex flex-col items-center space-y-3">
            <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
              OR SCAN TO DOWNLOAD
            </p>
            <div className="border border-neutral-900 p-4 bg-white">
              <QRCodeSVG
                value={`${window.location.origin}/download/${result.download_code}`}
                size={160}
                level="M"
                bgColor="#ffffff"
                fgColor="#171717"
              />
            </div>
          </div>

          <p className="text-xs font-bold uppercase tracking-widest text-neutral-500 leading-relaxed">
            This code works once. The file is deleted after download.
          </p>

          <button
            onClick={() => {
              setResult(null);
              setFile(null);
              setCopied(false);
            }}
            className="border border-neutral-900 px-6 py-3 text-sm font-bold uppercase tracking-widest hover:bg-neutral-100 transition-colors"
          >
            UPLOAD ANOTHER FILE
          </button>
        </div>
      </div>
    );
  }

  // ────────── UPLOAD FORM VIEW ──────────
  return (
    <div className="flex-1 flex items-center justify-center bg-white min-h-[calc(100vh-3.5rem)] p-8">
      <div className="max-w-lg w-full space-y-10">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-5xl font-extrabold tracking-tighter text-neutral-900 uppercase">
            SEND A FILE
          </h1>
          <p className="text-sm text-neutral-500 font-medium">
            No login. No trace. Auto-deleted after download.
          </p>
        </div>

        {/* Drop zone */}
        <UploadDropzone
          file={file}
          onFileSelect={(f) => { setFile(f); setError(null); }}
          onClear={() => setFile(null)}
          progress={uploadProgress}
          uploading={uploading}
        />

        {/* Expiry selector */}
        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
            AUTO-DELETE AFTER
          </p>
          <div className="grid grid-cols-4 border border-neutral-900">
            {EXPIRY_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setExpiryMinutes(opt.value)}
                className={`
                  py-3 text-xs font-bold uppercase tracking-widest transition-colors border-r last:border-r-0 border-neutral-900
                  ${
                    expiryMinutes === opt.value
                      ? "bg-neutral-900 text-white"
                      : "bg-white text-neutral-900 hover:bg-neutral-100"
                  }
                `}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="border border-neutral-900 bg-white px-5 py-3">
            <p className="text-xs font-bold uppercase tracking-widest text-neutral-900">
              {error}
            </p>
          </div>
        )}

        {/* Upload button */}
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className={`
            w-full py-4 text-sm font-bold uppercase tracking-widest transition-colors border border-neutral-900
            ${
              !file || uploading
                ? "bg-neutral-200 text-neutral-500 cursor-not-allowed"
                : "bg-neutral-900 text-white hover:bg-neutral-800"
            }
          `}
        >
          {uploading ? (
            <span className="inline-flex items-center gap-3">
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              {uploadProgress !== null && uploadProgress < 100
                ? `UPLOADING ${uploadProgress}%`
                : "PROCESSING..."}
            </span>
          ) : (
            "UPLOAD"
          )}
        </button>
      </div>
    </div>
  );
}
