"""Simulated RBAC authentication layer for v1.

Design:
- v1: caller supplies X-User-Id and X-User-Role HTTP headers (no real token).
- v2: replace _resolve_principal() with a real BankID/SITHS token validator
  without touching any router code.
- The abstraction surface is the Principal dataclass and the
  require_role() dependency factory — both are stable across the v1→v2 change.

Roles (v1):
    viewer  — read-only
    analyst — read + create suggestions + create mappings
    approver — analyst + approve mappings
    admin   — all (import schemas, export, catalog management)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Set

from fastapi import Depends, Header, HTTPException, status


class Role(str, Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    APPROVER = "approver"
    ADMIN = "admin"


_ROLE_HIERARCHY: dict[Role, Set[Role]] = {
    Role.VIEWER: {Role.VIEWER},
    Role.ANALYST: {Role.VIEWER, Role.ANALYST},
    Role.APPROVER: {Role.VIEWER, Role.ANALYST, Role.APPROVER},
    Role.ADMIN: {Role.VIEWER, Role.ANALYST, Role.APPROVER, Role.ADMIN},
}


@dataclass(frozen=True)
class Principal:
    """Authenticated caller identity.

    In v1 this is populated from X- headers.
    In v2 replace _resolve_principal() without changing this dataclass.
    """

    user_id: str
    role: Role


def _resolve_principal(
    x_user_id: str = Header(default="anonymous"),
    x_user_role: str = Header(default="viewer"),
) -> Principal:
    """Extract caller identity from request headers.

    v2 extension point: swap this function for real token validation.
    """
    try:
        role = Role(x_user_role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unknown role '{x_user_role}'. Allowed: {[r.value for r in Role]}.",
        )
    if not x_user_id or x_user_id == "anonymous":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-Id header is required.",
        )
    return Principal(user_id=x_user_id, role=role)


def require_role(minimum_role: Role):
    """FastAPI dependency factory: ensures caller has at least minimum_role.

    Usage:
        @router.post("/...", dependencies=[Depends(require_role(Role.ANALYST))])
    """

    def _check(principal: Principal = Depends(_resolve_principal)) -> Principal:
        if minimum_role not in _ROLE_HIERARCHY.get(principal.role, set()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{principal.role.value}' is insufficient. "
                    f"Requires '{minimum_role.value}' or higher."
                ),
            )
        return principal

    return _check


# Convenience: inject current principal without role restriction
CurrentPrincipal = Depends(_resolve_principal)
