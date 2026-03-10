from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter()


@router.get("/profile")
def profile(
    current_user: User = Depends(get_current_user),
    _db: Session = Depends(get_db),
) -> dict[str, str]:
    # TODO(phase-5): replace this placeholder with persisted user settings + RBAC policy controls.
    return {
        "email": current_user.email,
        "role": current_user.role,
        "message": "RBAC and user self-service settings land in Phase 5.",
    }
