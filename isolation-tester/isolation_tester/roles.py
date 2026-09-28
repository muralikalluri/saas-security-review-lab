"""Deliberately insecure for demonstration. Do not deploy.

Shared role hierarchy used by any probe that needs to know "is this
actor's role privileged enough to even attempt this operation, before
the tenant-isolation question is meaningful at all" (role-restricted AND
mass-assignment probes both need this - a fixed API may legitimately
403 a low-privileged role for reasons unrelated to tenant isolation).
"""

ROLE_RANK = {"owner": 3, "admin": 2, "accountant": 1, "viewer": 0}


def rank_of(role: str) -> int:
    return ROLE_RANK.get(role, 0)
