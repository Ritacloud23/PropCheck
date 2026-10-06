from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.errors import NotFound
from app.security import verify_file_token
from app.services import storage

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{token}")
def download_private_file(token: str) -> FileResponse:
    """Serve a private document. Tokens are HMAC-signed, expire after 10 minutes, and are only
    issued to authorised viewers (owner/listing agent, the uploader, or reviewers)."""
    key = verify_file_token(token)
    path = storage.private_path(key) if key else None
    if path is None:
        raise NotFound("This link has expired or is invalid.")
    return FileResponse(
        path,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )
