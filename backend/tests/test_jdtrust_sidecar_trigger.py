from types import SimpleNamespace

from app.services.jdtrust_sidecar_trigger import trigger_jdtrust_sidecar_after_crawl


class FakeProcess:
    pid = 1234

    def wait(self):
        return 0


def _settings(**overrides):
    values = {
        "bounty_pool_jdtrust_trigger_enabled": True,
        "bounty_pool_jdtrust_trigger_command": "python -m jdtrust run-latest-postgres --limit 60",
        "bounty_pool_jdtrust_trigger_cwd": None,
        "bounty_pool_jdtrust_trigger_lock_path": None,
        "bounty_pool_jdtrust_assessments_path": None,
        "database_url": "postgresql+psycopg://user:pw@127.0.0.1:5432/bounty_pool",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_trigger_jdtrust_sidecar_skips_when_no_new_jobs():
    calls = []

    result = trigger_jdtrust_sidecar_after_crawl(
        0,
        settings_override=_settings(),
        popen_factory=lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    assert result == {"status": "skipped", "reason": "no_new_jobs"}
    assert calls == []


def test_trigger_jdtrust_sidecar_skips_when_disabled():
    calls = []

    result = trigger_jdtrust_sidecar_after_crawl(
        2,
        settings_override=_settings(bounty_pool_jdtrust_trigger_enabled=False),
        popen_factory=lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    assert result == {"status": "disabled"}
    assert calls == []


def test_trigger_jdtrust_sidecar_starts_configured_command_with_lock(tmp_path):
    calls = []
    lock_path = tmp_path / "jdtrust.lock"

    def fake_popen(args, **kwargs):
        calls.append((args, kwargs))
        return FakeProcess()

    result = trigger_jdtrust_sidecar_after_crawl(
        3,
        settings_override=_settings(
            bounty_pool_jdtrust_trigger_cwd=str(tmp_path),
            bounty_pool_jdtrust_trigger_lock_path=str(lock_path),
        ),
        popen_factory=fake_popen,
        wait_for_process=False,
    )

    assert result == {"status": "started", "pid": 1234}
    assert calls[0][0] == ["python", "-m", "jdtrust", "run-latest-postgres", "--limit", "60"]
    assert calls[0][1]["cwd"] == str(tmp_path)
    assert calls[0][1]["env"]["DATABASE_URL"] == "postgresql+psycopg://user:pw@127.0.0.1:5432/bounty_pool"
    assert lock_path.exists()


def test_trigger_jdtrust_sidecar_skips_when_lock_exists(tmp_path):
    lock_path = tmp_path / "jdtrust.lock"
    lock_path.write_text("1234", encoding="utf-8")
    calls = []

    result = trigger_jdtrust_sidecar_after_crawl(
        2,
        settings_override=_settings(bounty_pool_jdtrust_trigger_lock_path=str(lock_path)),
        popen_factory=lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    assert result == {"status": "already_running"}
    assert calls == []


def test_trigger_jdtrust_sidecar_removes_lock_when_start_fails(tmp_path):
    lock_path = tmp_path / "jdtrust.lock"

    def fail_popen(*args, **kwargs):
        raise OSError("missing executable")

    result = trigger_jdtrust_sidecar_after_crawl(
        2,
        settings_override=_settings(bounty_pool_jdtrust_trigger_lock_path=str(lock_path)),
        popen_factory=fail_popen,
    )

    assert result == {"status": "failed", "error": "OSError: missing executable"}
    assert not lock_path.exists()


def test_trigger_jdtrust_sidecar_skips_when_command_is_missing():
    result = trigger_jdtrust_sidecar_after_crawl(
        2,
        settings_override=_settings(bounty_pool_jdtrust_trigger_command=None),
    )

    assert result == {"status": "skipped", "reason": "missing_command"}
