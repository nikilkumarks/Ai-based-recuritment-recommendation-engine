"""Idempotent CS/IT ontology seed. No users, jobs, scores, or ML artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.db import SessionLocal  # noqa: E402
from app.modules.ontology.seed import seed_ontology  # noqa: E402


def main() -> None:
    session = SessionLocal()
    try:
        first = seed_ontology(session)
        second = seed_ontology(session)
        session.commit()
        print(
            f"Ontology seed applied ({first.version}, checksum={first.checksum[:12]}…). "
            f"Second run kept version={second.version}. No users, jobs, or scores were created."
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
