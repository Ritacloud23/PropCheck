"""File storage abstraction.

* Public media (property photos, agent logos) -> `save_public()`. Local disk by default;
  Cloudinary when STORAGE_BACKEND=cloudinary.
* Private files (identity documents, authority letters, report evidence) -> `save_private()`.
  These ALWAYS stay in local private storage outside any public directory and are only
  served through short-lived HMAC-signed URLs (`signed_url()`), after an authorisation check.
"""

import hashlib
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from fastapi import UploadFile

from app.config import settings
from app.errors import BadRequest
from app.security import sign_file_key

IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
DOCUMENT_TYPES = {**IMAGE_TYPES, "application/pdf": ".pdf"}


def _sniff(data: bytes) -> str | None:
    """Detect file type from magic bytes. The client-supplied content type is never trusted."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    return None


@dataclass
class ValidatedFile:
    data: bytes
    content_type: str
    extension: str
    original_filename: str | None


async def read_validated(upload: UploadFile, *, kind: str) -> ValidatedFile:
    """kind = 'image' (5 MB, jpg/png/webp) or 'document' (10 MB, jpg/png/webp/pdf)."""
    allowed = IMAGE_TYPES if kind == "image" else DOCUMENT_TYPES
    limit = settings.max_image_bytes if kind == "image" else settings.max_document_bytes
    data = await upload.read(limit + 1)
    if len(data) == 0:
        raise BadRequest("The uploaded file is empty.")
    if len(data) > limit:
        raise BadRequest(f"File too large. Maximum size is {limit // (1024 * 1024)} MB.")
    detected = _sniff(data)
    if detected not in allowed:
        raise BadRequest("Unsupported file type. Allowed: " + ", ".join(sorted(set(allowed.values()))))
    return ValidatedFile(data, detected, allowed[detected], upload.filename)


def _root() -> Path:
    return Path(settings.storage_dir).resolve()


def public_dir() -> Path:
    p = _root() / "public"
    p.mkdir(parents=True, exist_ok=True)
    return p


def private_dir() -> Path:
    p = _root() / "private"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _new_key(prefix: str, ext: str) -> str:
    return f"{prefix}/{secrets.token_hex(16)}{ext}"


def _write(base: Path, key: str, data: bytes) -> None:
    path = (base / key).resolve()
    if base not in path.parents:
        raise BadRequest("Invalid storage path.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def save_public(f: ValidatedFile, prefix: str) -> str:
    """Returns a public URL."""
    if settings.storage_backend == "cloudinary" and settings.cloudinary_cloud_name:
        return _cloudinary_upload(f, prefix)
    key = _new_key(prefix, f.extension)
    _write(public_dir(), key, f.data)
    return f"{settings.api_public_url}/media/{key}"


def save_public_bytes(data: bytes, prefix: str, ext: str) -> str:
    """Used by the seed script for generated demo images."""
    key = _new_key(prefix, ext)
    _write(public_dir(), key, data)
    return f"{settings.api_public_url}/media/{key}"


def save_private(f: ValidatedFile, prefix: str) -> str:
    """Returns a private storage key (NOT a URL)."""
    key = _new_key(prefix, f.extension)
    _write(private_dir(), key, f.data)
    return key


def save_private_bytes(data: bytes, prefix: str, ext: str) -> str:
    key = _new_key(prefix, ext)
    _write(private_dir(), key, data)
    return key


def private_path(key: str) -> Path | None:
    base = private_dir()
    path = (base / key).resolve()
    if base not in path.parents or not path.is_file():
        return None
    return path


def signed_url(key: str | None) -> str | None:
    """Short-lived URL for an authorised viewer. Call only after an ownership/role check."""
    if not key:
        return None
    return f"/api/files/{sign_file_key(key)}"


def _cloudinary_upload(f: ValidatedFile, prefix: str) -> str:
    ts = str(int(time.time()))
    folder = f"propcheck/{prefix}"
    to_sign = f"folder={folder}&timestamp={ts}{settings.cloudinary_api_secret}"
    signature = hashlib.sha1(to_sign.encode(), usedforsecurity=False).hexdigest()
    resp = httpx.post(
        f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/image/upload",
        data={
            "api_key": settings.cloudinary_api_key,
            "timestamp": ts,
            "folder": folder,
            "signature": signature,
        },
        files={"file": (f.original_filename or f"upload{f.extension}", f.data, f.content_type)},
        timeout=30,
    )
    if resp.status_code != 200:
        raise BadRequest("Image upload failed. Please try again.")
    return resp.json()["secure_url"]
