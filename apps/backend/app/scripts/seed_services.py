from __future__ import annotations

from app.db.init_db import seed_services
from app.db.session import SessionLocal


def main() -> None:
    with SessionLocal() as db:
        seed_services(db)
        print("Service registry seeded")


if __name__ == "__main__":
    main()
