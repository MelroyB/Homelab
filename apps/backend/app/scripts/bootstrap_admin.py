from __future__ import annotations

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.user import User
from app.services.auth import create_admin_user


def main() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        existing = db.scalar(select(User).limit(1))
        if existing:
            print("Bootstrap skipped: user already exists")
            return

        email = settings.bootstrap_admin_email
        password = settings.bootstrap_admin_password
        if not password:
            raise SystemExit(
                "Set BOOTSTRAP_ADMIN_PASSWORD or INITIAL_ADMIN_PASSWORD in your "
                "environment before bootstrapping"
            )

        user = create_admin_user(db, email=email, password=password)
        print(f"Created admin user: {user.email}")


if __name__ == "__main__":
    main()
