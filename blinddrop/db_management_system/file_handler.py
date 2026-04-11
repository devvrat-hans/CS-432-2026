"""Utility module for temporary file storage in the Blind Drop system.

Handles saving uploaded files to disk, computing checksums, and cleaning
up files after download or expiry.
"""

import hashlib
import os
import uuid
from pathlib import Path

FILE_STORAGE_DIR = Path(__file__).resolve().parent / "uploads"

# Ensure the uploads directory exists at import time.
FILE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Maximum allowed upload size in bytes (100 MB).
MAX_FILE_SIZE = 100 * 1024 * 1024


def compute_checksum(file_path):
    """Return the SHA-256 hex digest of the file at *file_path*."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def save_uploaded_file(file_obj):
    """Save a Werkzeug ``FileStorage`` object to the uploads directory.

    Parameters
    ----------
    file_obj : werkzeug.datastructures.FileStorage
        The uploaded file from ``request.files``.

    Returns
    -------
    tuple[str, str, int, str]
        ``(storage_path, checksum, file_size, mime_type)`` where
        *storage_path* is the absolute path on disk.
    """
    original_name = file_obj.filename or "untitled"
    ext = Path(original_name).suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest = FILE_STORAGE_DIR / unique_name

    file_obj.save(str(dest))

    file_size = dest.stat().st_size
    checksum = compute_checksum(str(dest))
    mime_type = file_obj.content_type or "application/octet-stream"

    return str(dest), checksum, file_size, mime_type


def delete_file(storage_path):
    """Remove a file from disk safely.

    If the file does not exist, this is a no-op (idempotent).

    Parameters
    ----------
    storage_path : str
        Absolute path to the file to delete.

    Returns
    -------
    bool
        ``True`` if the file was deleted, ``False`` if it didn't exist.
    """
    try:
        os.remove(storage_path)
        return True
    except FileNotFoundError:
        return False
