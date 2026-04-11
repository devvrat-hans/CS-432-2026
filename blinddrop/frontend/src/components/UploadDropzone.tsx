"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, FileIcon, X } from "lucide-react";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface UploadDropzoneProps {
  /** Called when a file is selected or dropped. */
  onFileSelect: (file: File) => void;
  /** Currently selected file (controlled). */
  file: File | null;
  /** Clear the current selection. */
  onClear: () => void;
  /** Upload progress (0–100). Null when not uploading. */
  progress: number | null;
  /** Whether uploading is in progress. */
  uploading: boolean;
  /** Max file size in bytes (for display only). */
  maxSizeMB?: number;
}

export default function UploadDropzone({
  onFileSelect,
  file,
  onClear,
  progress,
  uploading,
  maxSizeMB = 100,
}: UploadDropzoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const dropped = e.dataTransfer.files[0];
      if (dropped) onFileSelect(dropped);
    },
    [onFileSelect]
  );

  const onChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) onFileSelect(selected);
    },
    [onFileSelect]
  );

  const handleClick = () => {
    if (!uploading) fileInputRef.current?.click();
  };

  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={handleClick}
      className={`
        relative border-2 border-dashed transition-colors
        flex flex-col items-center justify-center py-16 px-8 space-y-4
        ${uploading ? "cursor-default" : "cursor-pointer"}
        ${
          dragOver
            ? "border-neutral-900 bg-neutral-100"
            : file
            ? "border-neutral-900 bg-white"
            : "border-neutral-400 hover:border-neutral-900 bg-white"
        }
      `}
    >
      <input
        ref={fileInputRef}
        type="file"
        onChange={onChange}
        className="hidden"
      />

      {file ? (
        <>
          <FileIcon size={32} className="text-neutral-900" />
          <p className="text-sm font-bold uppercase tracking-widest text-neutral-900 truncate max-w-full">
            {file.name}
          </p>
          <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
            {formatSize(file.size)}
          </p>

          {/* Clear button */}
          {!uploading && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onClear();
              }}
              className="absolute top-3 right-3 p-1 border border-neutral-900 hover:bg-neutral-100 transition-colors"
              aria-label="Clear selection"
            >
              <X size={14} className="text-neutral-900" />
            </button>
          )}
        </>
      ) : (
        <>
          <Upload size={32} className="text-neutral-500" />
          <p className="text-sm font-bold uppercase tracking-widest text-neutral-500">
            DRAG & DROP A FILE HERE
          </p>
          <p className="text-xs text-neutral-400">
            or click to browse — max {maxSizeMB} MB
          </p>
        </>
      )}

      {/* Progress bar */}
      {uploading && progress !== null && (
        <div className="w-full mt-4 space-y-2">
          <div className="w-full h-2 bg-neutral-200 border border-neutral-900">
            <div
              className="h-full bg-neutral-900 transition-all duration-200"
              style={{ width: `${Math.min(progress, 100)}%` }}
            />
          </div>
          <p className="text-xs font-bold uppercase tracking-widest text-neutral-500 text-center">
            {progress < 100 ? `${Math.round(progress)}%` : "PROCESSING..."}
          </p>
        </div>
      )}
    </div>
  );
}
