from app.core.config import Settings


def test_settings_parse_documented_csv_lists(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    monkeypatch.setenv("TRUSTED_HOSTS", "localhost,127.0.0.1,backend")

    settings = Settings(_env_file=None)

    assert settings.cors_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    assert settings.trusted_hosts == ["localhost", "127.0.0.1", "backend"]
