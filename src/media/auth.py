"""Authentication and authorization middleware for media streaming and API access."""

from __future__ import annotations

import hmac
import time
import uuid
from pathlib import Path

from fastapi import HTTPException, Query, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cloudctl.core.logging import get_logger
from cloudctl.utils.validators import is_safe_path

logger = get_logger("media.auth.audit")
security = HTTPBearer(auto_error=False)

# In-memory revocation registry for active tokens with expiry tracking
_REVOKED_TOKENS: set[str] = set()


def audit_log_auth_event(
    event_type: str, user_id: str, client_ip: str, item_id: str, success: bool, details: str = ""
) -> None:
    """Record a structured security audit trail log entry."""
    status_str = "SUCCESS" if success else "DENIED"
    logger.info(
        f"SECURITY_AUDIT: event={event_type} status={status_str} user={user_id} ip={client_ip} item={item_id} details={details}"
    )


def revoke_token(token: str) -> None:
    """Explicitly revoke an active token before its expiration."""
    if token:
        _REVOKED_TOKENS.add(token)


def is_token_revoked(token: str) -> bool:
    """Check if a token has been revoked."""
    return token in _REVOKED_TOKENS


def clear_revoked_tokens() -> None:
    """Clear revocation registry (primarily for test environments)."""
    _REVOKED_TOKENS.clear()


def create_media_token(
    item_id: str, secret: str, user_id: str = "default_user", expires_in_seconds: int = 86400
) -> str:
    """Create a time-limited HMAC authentication token for direct media playback."""
    expiry = int(time.time()) + expires_in_seconds
    msg = f"{user_id}:{item_id}:{expiry}"
    sig = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), "sha256").hexdigest()
    return f"{user_id}:{expiry}:{sig}"


def verify_media_token_user(
    item_id: str, token: str, secret: str, clock_skew_seconds: int = 0
) -> tuple[bool, str]:
    """Verify an expiring media playback token and return (is_valid, user_id)."""
    if not token or not secret or ":" not in token or is_token_revoked(token):
        return False, ""
    try:
        parts = token.split(":")
        if len(parts) == 3:
            user_id, expiry_str, sig = parts
            expiry = int(expiry_str)
            if time.time() > (expiry + clock_skew_seconds):
                return False, ""  # Expired token

            expected_msg = f"{user_id}:{item_id}:{expiry}"
            expected_sig = hmac.new(
                secret.encode("utf-8"), expected_msg.encode("utf-8"), "sha256"
            ).hexdigest()
            if hmac.compare_digest(sig, expected_sig):
                return True, user_id
        elif len(parts) == 2:
            # Backward compatibility with 2-part tokens: expiry:sig
            expiry_str, sig = parts
            expiry = int(expiry_str)
            if time.time() > (expiry + clock_skew_seconds):
                return False, ""

            expected_msg = f"{item_id}:{expiry}"
            expected_sig = hmac.new(
                secret.encode("utf-8"), expected_msg.encode("utf-8"), "sha256"
            ).hexdigest()
            if hmac.compare_digest(sig, expected_sig):
                return True, "default_user"
        return False, ""
    except Exception:
        return False, ""


def verify_media_token(item_id: str, token: str, secret: str, clock_skew_seconds: int = 0) -> bool:
    """Verify an expiring media playback token."""
    valid, _ = verify_media_token_user(
        item_id, token, secret, clock_skew_seconds=clock_skew_seconds
    )
    return valid


def validate_file_access(base_dir: Path, requested_path: Path) -> Path:
    """Ensure path is within base storage directory and prevent directory traversal."""
    resolved_base = base_dir.resolve()
    resolved_path = requested_path.resolve()

    if not is_safe_path(resolved_base, resolved_path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Path traversal attempt detected",
        )
    return resolved_path


def authenticate_request(
    request: Request,
    auth_header: HTTPAuthorizationCredentials | None = Security(security),
    token: str | None = Query(None),
) -> bool:
    """Validate Bearer header or token query parameter against configured secret."""
    # Assign request correlation ID for audit trail
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = req_id

    secret: str = getattr(request.app.state.config, "jwt_secret", "")
    item_id = request.path_params.get("item_id") or request.path_params.get("id") or "global"

    # Check query param token (e.g. for <video src="/api/media/123/stream?token=...">)
    # Strictly requires valid cryptographic HMAC signature; raw secret query params are rejected
    if token and item_id:
        valid, user_id = verify_media_token_user(item_id, token, secret)
        if valid:
            request.state.user_id = user_id
            return True

    # Check Bearer token (CLI / API requests)
    if auth_header and auth_header.credentials:
        cred = auth_header.credentials
        # Constant-time comparison for master admin secret
        if secret and hmac.compare_digest(cred, secret):
            request.state.user_id = "admin"
            return True
        valid, user_id = verify_media_token_user("global", cred, secret)
        if valid:
            request.state.user_id = user_id
            return True
        if item_id:
            valid, user_id = verify_media_token_user(item_id, cred, secret)
            if valid:
                request.state.user_id = user_id
                return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required for media access",
        headers={"WWW-Authenticate": "Bearer"},
    )
