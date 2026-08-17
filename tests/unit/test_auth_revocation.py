"""Tests for token revocation registry and hardened authentication rules."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.media.auth import (
    authenticate_request,
    clear_revoked_tokens,
    create_media_token,
    is_token_revoked,
    revoke_token,
    verify_media_token_user,
)


def test_token_revocation_lifecycle():
    clear_revoked_tokens()
    secret = "test-secret-key-xyz"
    token = create_media_token("item_101", secret, "user_alice")

    # Valid initially
    valid, uid = verify_media_token_user("item_101", token, secret)
    assert valid
    assert uid == "user_alice"
    assert not is_token_revoked(token)

    # Revoke token
    revoke_token(token)
    assert is_token_revoked(token)

    # Verification fails after revocation
    valid_after, _ = verify_media_token_user("item_101", token, secret)
    assert not valid_after

    clear_revoked_tokens()
    assert not is_token_revoked(token)


def test_authenticate_request_rejects_raw_query_secret():
    secret = "top-secret-signing-key"
    req = MagicMock()
    req.app.state.config.jwt_secret = secret
    req.path_params = {"id": "media_item_1"}
    req.headers = {}
    req.state = MagicMock()

    # Raw secret in token query param must be rejected now (no query param bypass)
    with pytest.raises(HTTPException) as exc:
        authenticate_request(req, auth_header=None, token=secret)
    assert exc.value.status_code == 401


def test_authenticate_request_correlation_id():
    secret = "my-secret"
    token = create_media_token("item_1", secret, "bob")

    req = MagicMock()
    req.app.state.config.jwt_secret = secret
    req.path_params = {"id": "item_1"}
    req.headers = {"X-Request-ID": "req-custom-audit-id-123"}
    req.state = MagicMock()

    assert authenticate_request(req, auth_header=None, token=token)
    assert req.state.request_id == "req-custom-audit-id-123"
