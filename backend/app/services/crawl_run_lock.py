from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session


CRAWL_LOCK_KEY = 70420260925


@contextmanager
def crawl_run_lock(db: Session) -> Iterator[None]:
    """Serialize global and Japan crawls on PostgreSQL.

    A dedicated connection keeps the session-level advisory lock held across the
    commits performed by the existing crawl services.
    """

    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        yield
        return

    connection = bind.connect()
    try:
        connection.execute(
            text("SELECT pg_advisory_lock(:lock_key)"),
            {"lock_key": CRAWL_LOCK_KEY},
        )
        yield
    finally:
        try:
            connection.execute(
                text("SELECT pg_advisory_unlock(:lock_key)"),
                {"lock_key": CRAWL_LOCK_KEY},
            )
        except Exception:
            # Never return a possibly locked physical connection to the pool.
            connection.invalidate()
            raise
        finally:
            connection.close()
