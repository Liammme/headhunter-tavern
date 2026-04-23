from app.core.config import DEFAULT_SQLITE_PATH, normalize_database_url, parse_cors_origins


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
