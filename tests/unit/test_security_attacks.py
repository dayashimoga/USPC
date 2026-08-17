"""Comprehensive security attack tests covering authentication, authorization, IDOR, path traversal, and secret rotation."""

import hmac
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.media.auth import (
    authenticate_request,
    clear_revoked_tokens,
    create_media_token,
    is_token_revoked,
    revoke_token,
    validate_file_access,
    verify_media_token,
    verify_media_token_user,
)


@pytest.fixture(autouse=True)
def _cleanup_revocations():
    clear_revoked_tokens()
    yield
    clear_revoked_tokens()


def test_token_tampering_and_forgery():
    secret = "production_super_secret_key_32_chars!"
    item_id = "video-item-42"
    valid_token = create_media_token(item_id, secret, user_id="alice", expires_in_seconds=3600)

    # Valid token works
    valid, user = verify_media_token_user(item_id, valid_token, secret)
    assert valid is True
    assert user == "alice"

    # Tampered signature
    parts = valid_token.split(":")
    tampered_sig = parts[0] + ":" + parts[1] + ":" + "0" * len(parts[2])
    valid, _ = verify_media_token_user(item_id, tampered_sig, secret)
    assert valid is False

    # Tampered user_id
    tampered_user = "bob:" + parts[1] + ":" + parts[2]
    valid, _ = verify_media_token_user(item_id, tampered_user, secret)
    assert valid is False

    # Tampered expiry (extended into future)
    tampered_exp = parts[0] + ":" + str(int(parts[1]) + 86400) + ":" + parts[2]
    valid, _ = verify_media_token_user(item_id, tampered_exp, secret)
    assert valid is False

    # Wrong item_id (IDOR attempt)
    valid, _ = verify_media_token_user("video-item-99", valid_token, secret)
    assert valid is False

    # Wrong secret
    valid, _ = verify_media_token_user(item_id, valid_token, "wrong_secret_key_1234567890123456")
    assert valid is False


def test_token_malformed_and_edge_cases():
    secret = "secret123"
    assert verify_media_token_user("item1", "", secret) == (False, "")
    assert verify_media_token_user("item1", "no_colons", secret) == (False, "")
    assert verify_media_token_user("item1", "a:b:c:d", secret) == (False, "")
    assert verify_media_token_user("item1", "user:not_an_int:sig", secret) == (False, "")
    assert verify_media_token_user("item1", ":::", secret) == (False, "")
    assert verify_media_token_user("item1", None, secret) == (False, "")
    assert verify_media_token_user("item1", "token", "") == (False, "")
    assert verify_media_token("item1", "", secret) is False


def test_token_expiration_and_clock_skew():
    secret = "test_skew_secret"
    item_id = "skew-item"

    # Token expired 10 seconds ago
    expired_token = create_media_token(item_id, secret, user_id="user1", expires_in_seconds=-10)

    # Strictly expired with 0 skew
    valid, _ = verify_media_token_user(item_id, expired_token, secret, clock_skew_seconds=0)
    assert valid is False

    # Valid when allowed 30 seconds clock skew
    valid, user = verify_media_token_user(item_id, expired_token, secret, clock_skew_seconds=30)
    assert valid is True
    assert user == "user1"

    # Expired token with 2-part legacy format
    msg = f"{item_id}:{int(time.time()) - 10}"
    sig = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), "sha256").hexdigest()
    legacy_expired = f"{int(time.time()) - 10}:{sig}"

    assert verify_media_token_user(item_id, legacy_expired, secret, clock_skew_seconds=0) == (
        False,
        "",
    )
    assert verify_media_token_user(item_id, legacy_expired, secret, clock_skew_seconds=30) == (
        True,
        "default_user",
    )


def test_token_revocation_and_replay():
    secret = "revocation_secret"
    token = create_media_token("item_rev", secret, user_id="charlie")

    assert is_token_revoked(token) is False
    assert verify_media_token("item_rev", token, secret) is True

    # Revoke token
    revoke_token(token)
    assert is_token_revoked(token) is True
    assert verify_media_token("item_rev", token, secret) is False

    # Revoking empty token is a no-op
    revoke_token("")
    assert is_token_revoked("") is False


def test_secret_rotation():
    old_secret = "old_master_secret_key_32_characters"
    new_secret = "new_master_secret_key_32_characters"
    item_id = "rotation_test_item"

    token_old = create_media_token(item_id, old_secret, user_id="dave")

    # Works with old secret
    assert verify_media_token(item_id, token_old, old_secret) is True
    # Fails immediately with new rotated secret
    assert verify_media_token(item_id, token_old, new_secret) is False

    # New token with new secret works
    token_new = create_media_token(item_id, new_secret, user_id="dave")
    assert verify_media_token(item_id, token_new, new_secret) is True


def test_path_traversal_attack_vectors(tmp_path):
    base_dir = tmp_path / "storage"
    base_dir.mkdir()
    secret_file = tmp_path / "sensitive.txt"
    secret_file.write_text("TOP_SECRET", encoding="utf-8")

    attack_payloads = [
        tmp_path / "sensitive.txt",
        base_dir / ".." / "sensitive.txt",
        base_dir / "nested" / ".." / ".." / "sensitive.txt",
        Path("/etc/passwd"),
        Path("C:/Windows/system32/cmd.exe"),
    ]

    for target in attack_payloads:
        with pytest.raises(HTTPException) as exc_info:
            validate_file_access(base_dir, target)
        assert exc_info.value.status_code == 403

    # Direct valid subpath works
    safe_file = base_dir / "safe.mp4"
    safe_file.write_text("video_content", encoding="utf-8")
    resolved = validate_file_access(base_dir, safe_file)
    assert resolved == safe_file.resolve()


def test_authenticate_request_security_matrix():
    secret = "auth_matrix_secret"
    mock_app = MagicMock()
    mock_app.state.config.jwt_secret = secret

    # 1. Bearer master secret authentication
    req_admin = MagicMock()
    req_admin.app = mock_app
    req_admin.headers = {"X-Request-ID": "req-123"}
    req_admin.path_params = {}
    auth_header = MagicMock(credentials=secret)
    assert authenticate_request(req_admin, auth_header=auth_header, token=None) is True
    assert req_admin.state.user_id == "admin"
    assert req_admin.state.request_id == "req-123"

    # 2. Bearer global HMAC token authentication
    global_token = create_media_token("global", secret, user_id="eve")
    auth_header_global = MagicMock(credentials=global_token)
    req_eve = MagicMock()
    req_eve.app = mock_app
    req_eve.headers = {}
    req_eve.path_params = {}
    assert authenticate_request(req_eve, auth_header=auth_header_global, token=None) is True
    assert req_eve.state.user_id == "eve"

    # 3. Query param HMAC token for specific item
    item_token = create_media_token("item-99", secret, user_id="frank")
    req_frank = MagicMock()
    req_frank.app = mock_app
    req_frank.headers = {}
    req_frank.path_params = {"item_id": "item-99"}
    assert authenticate_request(req_frank, auth_header=None, token=item_token) is True
    assert req_frank.state.user_id == "frank"

    # 4. Query param with raw secret MUST be rejected (backdoor prevention)
    req_attack = MagicMock()
    req_attack.app = mock_app
    req_attack.headers = {}
    req_attack.path_params = {"item_id": "item-99"}
    with pytest.raises(HTTPException) as exc_info:
        authenticate_request(req_attack, auth_header=None, token=secret)
    assert exc_info.value.status_code == 401
