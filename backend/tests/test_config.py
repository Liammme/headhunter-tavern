from app.core.config import parse_cors_origins


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
