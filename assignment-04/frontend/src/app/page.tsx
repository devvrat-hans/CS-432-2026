import Link from "next/link";
import { Upload, Download } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-[calc(100vh-3.5rem)]">
      {/* Hero section */}
      <div className="flex flex-col items-center justify-center py-16 px-8 bg-white border-b border-neutral-900">
        <div className="max-w-2xl text-center space-y-5">
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tighter text-neutral-900 uppercase">
            BLIND DROP
          </h1>
          <p className="text-sm md:text-base text-neutral-500 font-medium leading-relaxed max-w-md mx-auto">
            Privacy-focused file transfer. No login. No trace.
            Files are auto-deleted immediately after download.
          </p>
        </div>
      </div>

      {/* Action panels */}
      <div className="flex-1 flex flex-col md:flex-row">
        {/* ─── LEFT PANEL: SEND ─── */}
        <Link
          href="/upload"
          className="flex-1 flex flex-col items-center justify-center p-12 bg-white border-b md:border-b-0 md:border-r border-neutral-900 group hover:bg-neutral-50 transition-colors"
        >
          <div className="max-w-sm w-full space-y-8 text-center">
            <div className="flex justify-center">
              <div className="p-4 border border-neutral-900 bg-neutral-100 group-hover:bg-white transition-colors">
                <Upload size={32} className="text-neutral-900" />
              </div>
            </div>
            <div className="space-y-3">
              <h2 className="text-4xl md:text-5xl font-extrabold tracking-tighter text-neutral-900 uppercase">
                SEND A FILE
              </h2>
              <p className="text-sm text-neutral-500 font-medium leading-relaxed">
                Upload a file and receive a one-time download code.
                No account required.
              </p>
            </div>
            <span className="inline-block border border-neutral-900 px-6 py-3 text-sm font-bold uppercase tracking-widest group-hover:bg-neutral-900 group-hover:text-white transition-colors">
              UPLOAD
            </span>
          </div>
        </Link>

        {/* ─── RIGHT PANEL: RECEIVE ─── */}
        <Link
          href="/download"
          className="flex-1 flex flex-col items-center justify-center p-12 bg-neutral-900 group hover:bg-neutral-800 transition-colors"
        >
          <div className="max-w-sm w-full space-y-8 text-center">
            <div className="flex justify-center">
              <div className="p-4 border border-white bg-neutral-800 group-hover:bg-neutral-700 transition-colors">
                <Download size={32} className="text-white" />
              </div>
            </div>
            <div className="space-y-3">
              <h2 className="text-4xl md:text-5xl font-extrabold tracking-tighter text-white uppercase">
                RECEIVE A FILE
              </h2>
              <p className="text-sm text-neutral-400 font-medium leading-relaxed">
                Enter your 6-character code to download.
                The file is deleted immediately after.
              </p>
            </div>
            <span className="inline-block border border-white text-white px-6 py-3 text-sm font-bold uppercase tracking-widest group-hover:bg-white group-hover:text-neutral-900 transition-colors">
              DOWNLOAD
            </span>
          </div>
        </Link>
      </div>

      {/* ─── FOOTER STRIP ─── */}
      <div className="flex items-center justify-center px-6 py-3 bg-white border-t border-neutral-900">
        <div className="flex items-center gap-2">
          <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
            No login. No trace. Auto-deleted after download.
          </p>
        </div>
      </div>
    </div>
  );
}
