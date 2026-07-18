"""
Shared rate limiter (slowapi) for auth routes — see ROADMAP.md Phase 4
guardrails. Lives in its own module (not main.py) so route files can import it
without a circular import back to the app factory.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
