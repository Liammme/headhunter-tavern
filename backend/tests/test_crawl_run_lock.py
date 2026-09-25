from app.services.crawl_run_lock import crawl_run_lock
import pytest


class _Dialect:
    name = "postgresql"


class _Connection:
    def __init__(self, events: list[str]):
        self.events = events

    def execute(self, statement, params):
        self.events.append(f"execute:{statement}:{params['lock_key']}")

    def close(self):
        self.events.append("close")


class _Bind:
    dialect = _Dialect()

    def __init__(self, events: list[str]):
        self.events = events

    def connect(self):
        self.events.append("connect")
        return _Connection(self.events)


class _Session:
    def __init__(self, events: list[str]):
        self.bind = _Bind(events)

    def get_bind(self):
        return self.bind


def test_crawl_run_lock_holds_postgres_session_lock_for_entire_block():
    events: list[str] = []

    with crawl_run_lock(_Session(events)):
        events.append("work")

    assert events[0] == "connect"
    assert "pg_advisory_lock" in events[1]
    assert events[2] == "work"
    assert "pg_advisory_unlock" in events[3]
    assert events[4] == "close"


class _SqliteDialect:
    name = "sqlite"


class _SqliteBind:
    dialect = _SqliteDialect()


class _SqliteSession:
    def get_bind(self):
        return _SqliteBind()


def test_crawl_run_lock_is_noop_outside_postgres():
    entered = False

    with crawl_run_lock(_SqliteSession()):
        entered = True

    assert entered is True


def test_crawl_run_lock_releases_after_work_raises():
    events: list[str] = []
    with pytest.raises(RuntimeError, match="failed"):
        with crawl_run_lock(_Session(events)):
            raise RuntimeError("failed")
    assert "pg_advisory_unlock" in events[-2]
    assert events[-1] == "close"


def test_crawl_run_lock_discards_connection_if_unlock_fails(monkeypatch):
    events: list[str] = []
    session = _Session(events)
    connection = _Connection(events)
    original_execute = connection.execute

    def execute(statement, params):
        if "pg_advisory_unlock" in str(statement):
            raise RuntimeError("unlock failed")
        original_execute(statement, params)

    monkeypatch.setattr(connection, "execute", execute)
    monkeypatch.setattr(connection, "invalidate", lambda: events.append("invalidate"), raising=False)
    monkeypatch.setattr(session.bind, "connect", lambda: connection)
    with pytest.raises(RuntimeError, match="unlock failed"):
        with crawl_run_lock(session):
            pass
    assert events[-2:] == ["invalidate", "close"]
