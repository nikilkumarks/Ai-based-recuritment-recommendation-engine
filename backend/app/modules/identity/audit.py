from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog

# Actions recorded for security review. Never include passwords or tokens.
REGISTER = "auth.register"
LOGIN_SUCCESS = "auth.login_success"
LOGIN_FAILURE = "auth.login_failure"
LOGOUT = "auth.logout"
REFRESH = "auth.refresh"
LOGOUT_ALL = "auth.logout_all"
AUTHZ_DENIED = "authz.denied"


def record_audit(
    db: Session,
    *,
    action: str,
    resource_type: str,
    actor_user_id: uuid.UUID | None = None,
    resource_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            audit_metadata=metadata or {},
        )
    )
