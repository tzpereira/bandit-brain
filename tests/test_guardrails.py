from unittest.mock import patch

import pytest
from fastapi import HTTPException

from banditbrain.api import guardrails


def _user(is_demo: bool) -> dict:
    return {"id": 1, "email": "x@example.com", "password": "hashed", "created_at": "2026-01-01", "is_demo": is_demo}


def test_allows_a_non_demo_user():
    with patch.object(guardrails, "get_user_by_id", return_value=_user(is_demo=False)):
        assert guardrails.block_demo_writes(user_id=1, x_seed_secret=None) == 1


def test_blocks_a_demo_user_with_no_secret_configured():
    with (
        patch.object(guardrails, "get_user_by_id", return_value=_user(is_demo=True)),
        patch.object(guardrails, "DEMO_SEED_SECRET", None),
    ):
        with pytest.raises(HTTPException) as exc_info:
            guardrails.block_demo_writes(user_id=1, x_seed_secret=None)
        assert exc_info.value.status_code == 403


def test_blocks_a_demo_user_with_wrong_secret():
    with (
        patch.object(guardrails, "get_user_by_id", return_value=_user(is_demo=True)),
        patch.object(guardrails, "DEMO_SEED_SECRET", "correct-secret"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            guardrails.block_demo_writes(user_id=1, x_seed_secret="wrong-secret")
        assert exc_info.value.status_code == 403


def test_bypasses_a_demo_user_with_the_matching_secret():
    with (
        patch.object(guardrails, "get_user_by_id", return_value=_user(is_demo=True)),
        patch.object(guardrails, "DEMO_SEED_SECRET", "correct-secret"),
    ):
        assert guardrails.block_demo_writes(user_id=1, x_seed_secret="correct-secret") == 1


def test_allows_when_user_lookup_returns_none():
    # Defensive: verify_token already validated the JWT, so this shouldn't happen
    # in practice, but an unknown user must not be treated as a demo account.
    with patch.object(guardrails, "get_user_by_id", return_value=None):
        assert guardrails.block_demo_writes(user_id=999, x_seed_secret=None) == 999
