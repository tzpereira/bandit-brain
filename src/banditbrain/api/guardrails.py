"""
Guardrails for a public-facing deployment (see ROADMAP.md Phase 4). Protects
a designated read-only demo account from write/destructive actions,
independent of what real users can do with their own accounts.
"""

import os

from fastapi import Depends, Header, HTTPException

from banditbrain.api.jwt_auth import verify_token
from banditbrain.api.repositories.users import get_user_by_id

# Operational bypass for scripts/seed.py and scripts/reset_demo_data.py to
# refresh the demo account's data without granting real visitors write access.
# Unset (the default) means no bypass is possible - the demo account is
# strictly read-only until an operator explicitly configures this.
DEMO_SEED_SECRET = os.getenv("DEMO_SEED_SECRET")


def block_demo_writes(
    user_id: int = Depends(verify_token),
    x_seed_secret: str | None = Header(default=None),
) -> int:
    """
    Dependency for write/destructive routes: raises 403 if the authenticated
    user is flagged `is_demo`, unless the request carries a valid
    `X-Seed-Secret` header matching DEMO_SEED_SECRET.
    """
    user = get_user_by_id(user_id)
    is_demo = bool(user and user.get("is_demo"))
    bypassed = bool(DEMO_SEED_SECRET) and x_seed_secret == DEMO_SEED_SECRET
    if is_demo and not bypassed:
        raise HTTPException(status_code=403, detail="This is a read-only demo account.")
    return user_id
