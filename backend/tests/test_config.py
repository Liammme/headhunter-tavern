from app.core.config import DEFAULT_SQLITE_PATH, Settings, normalize_database_url, parse_cors_origins


def test_settings_default_cors_origins_allow_common_local_frontends():
    rollout_settings = Settings(_env_file=None)

    assert parse_cors_origins(rollout_settings.cors_origins) == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_parse_cors_origins_supports_comma_separated_values():
    origins = parse_cors_origins(
        "https://example.vercel.app, https://www.example.com ,http://localhost:3000"
    )

    assert origins == [
        "https://example.vercel.app",
        "https://www.example.com",
        "http://localhost:3000",
    ]


def test_parse_cors_origins_ignores_empty_items():
    origins = parse_cors_origins("https://example.vercel.app, , ,")

    assert origins == ["https://example.vercel.app"]


def test_normalize_database_url_keeps_default_sqlite_path_stable():
    assert normalize_database_url(f"sqlite+pysqlite:///{DEFAULT_SQLITE_PATH}") == (
        f"sqlite+pysqlite:///{DEFAULT_SQLITE_PATH}"
    )


def test_normalize_database_url_upgrades_plain_postgresql_scheme():
    url = "postgresql://bounty_pool_user:secret@127.0.0.1:5432/bounty_pool"

    assert normalize_database_url(url) == (
        "postgresql+psycopg://bounty_pool_user:secret@127.0.0.1:5432/bounty_pool"
    )


def test_normalize_database_url_upgrades_legacy_postgres_scheme():
    url = "postgres://bounty_pool_user:secret@127.0.0.1:5432/bounty_pool"

    assert normalize_database_url(url) == (
        "postgresql+psycopg://bounty_pool_user:secret@127.0.0.1:5432/bounty_pool"
    )


def test_settings_support_estimated_bounty_rollout_flags():
    rollout_settings = Settings(
        _env_file=None,
        bounty_pool_estimated_bounty_live_write_enabled=True,
        bounty_pool_estimated_bounty_read_enabled=True,
        bounty_pool_estimated_bounty_startup_audit_enabled=True,
        bounty_pool_estimated_bounty_audit_window_days=21,
    )

    assert rollout_settings.bounty_pool_estimated_bounty_live_write_enabled is True
    assert rollout_settings.bounty_pool_estimated_bounty_read_enabled is True
    assert rollout_settings.bounty_pool_estimated_bounty_startup_audit_enabled is True
    assert rollout_settings.bounty_pool_estimated_bounty_audit_window_days == 21
