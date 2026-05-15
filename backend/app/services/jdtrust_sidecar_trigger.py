from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable

from app.core.config import settings


PopenFactory = Callable[..., subprocess.Popen]
STALE_LOCK_SECONDS = 24 * 60 * 60


def trigger_jdtrust_sidecar_after_crawl(
    new_jobs: int,
    *,
    settings_override: Any | None = None,
    popen_factory: PopenFactory = subprocess.Popen,
    wait_for_process: bool = True,
) -> dict:
    if new_jobs <= 0:
        return {"status": "skipped", "reason": "no_new_jobs"}

    current_settings = settings_override or settings
    if not current_settings.bounty_pool_jdtrust_trigger_enabled:
        return {"status": "disabled"}

    command = _optional_str(current_settings.bounty_pool_jdtrust_trigger_command)
    if command is None:
        return {"status": "skipped", "reason": "missing_command"}

    cwd = _optional_path(current_settings.bounty_pool_jdtrust_trigger_cwd)
    if cwd is not None and not cwd.is_dir():
        return {"status": "failed", "error": "trigger cwd does not exist"}

    lock_path = _lock_path(current_settings)
    if not _acquire_lock(lock_path):
        return {"status": "already_running"}

    env = os.environ.copy()
    database_url = _optional_str(getattr(current_settings, "database_url", None))
    if database_url is not None:
        env["DATABASE_URL"] = database_url

    try:
        process = popen_factory(
            _split_command(command),
            cwd=str(cwd) if cwd is not None else None,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:  # noqa: BLE001
        _release_lock(lock_path)
        return {"status": "failed", "error": f"{type(exc).__name__}: {str(exc)}"}

    if wait_for_process:
        thread = threading.Thread(target=_wait_and_release_lock, args=(process, lock_path), daemon=True)
        thread.start()

    return {"status": "started", "pid": process.pid}


def _split_command(command: str) -> list[str]:
    return shlex.split(command, posix=os.name != "nt")


def _lock_path(current_settings: Any) -> Path:
    configured = _optional_path(current_settings.bounty_pool_jdtrust_trigger_lock_path)
    if configured is not None:
        return configured

    assessments_path = _optional_path(current_settings.bounty_pool_jdtrust_assessments_path)
    if assessments_path is not None:
        return assessments_path.with_suffix(".lock")

    return Path(tempfile.gettempdir()) / "bounty-pool-jdtrust-trigger.lock"


def _acquire_lock(path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if not _release_stale_lock(path):
            return False
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    return True


def _release_stale_lock(path: Path) -> bool:
    try:
        lock_age_seconds = max(0, time.time() - path.stat().st_mtime)
    except FileNotFoundError:
        return True
    if lock_age_seconds < STALE_LOCK_SECONDS:
        return False
    _release_lock(path)
    return True


def _wait_and_release_lock(process: subprocess.Popen, lock_path: Path) -> None:
    try:
        process.wait()
    finally:
        _release_lock(lock_path)


def _release_lock(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _optional_path(value: Any) -> Path | None:
    text = _optional_str(value)
    return Path(text) if text is not None else None
