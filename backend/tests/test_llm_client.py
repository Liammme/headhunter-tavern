import json

from app.core.config import settings
from app.services.llm_client import iter_llm_models, request_chat_completion_with_model, request_structured_json, should_use_llm


def test_generic_llm_config_overrides_zhipu_config(monkeypatch):
    monkeypatch.setattr(settings, "bounty_pool_intelligence_llm_enabled", True)
    monkeypatch.setattr(settings, "bounty_pool_zhipu_api_key", None)
    monkeypatch.setattr(settings, "bounty_pool_zhipu_model", "glm-4-flash-250414")
    monkeypatch.setattr(settings, "bounty_pool_zhipu_fallback_models", "glm-4.7-flash")
    monkeypatch.setattr(settings, "bounty_pool_llm_api_key", "generic-key")
    monkeypatch.setattr(settings, "bounty_pool_llm_model", "deepseek-chat")
    monkeypatch.setattr(settings, "bounty_pool_llm_fallback_models", "deepseek-reasoner")

    assert should_use_llm() is True
    assert iter_llm_models() == ["deepseek-chat", "deepseek-reasoner"]


def test_generic_llm_config_requires_generic_key(monkeypatch):
    monkeypatch.setattr(settings, "bounty_pool_intelligence_llm_enabled", True)
    monkeypatch.setattr(settings, "bounty_pool_zhipu_api_key", "zhipu-key")
    monkeypatch.setattr(settings, "bounty_pool_llm_api_key", "")
    monkeypatch.setattr(settings, "bounty_pool_llm_model", "gpt-5.4-nano")
    monkeypatch.setattr(settings, "bounty_pool_llm_base_url", "https://yunwu.ai/v1")

    assert should_use_llm() is False


def test_generic_llm_request_uses_generic_base_url_and_key(monkeypatch):
    monkeypatch.setattr(settings, "bounty_pool_llm_api_key", "generic-key")
    monkeypatch.setattr(settings, "bounty_pool_llm_base_url", "https://llm.example.com/v1")
    monkeypatch.setattr(settings, "bounty_pool_llm_timeout_seconds", 60)

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"choices":[{"message":{"content":"{\\"ok\\":true}"}}]}'

    def fake_urlopen(http_request, timeout):
        captured["url"] = http_request.full_url
        captured["authorization"] = http_request.headers["Authorization"]
        captured["timeout"] = timeout
        captured["payload"] = http_request.data
        return FakeResponse()

    monkeypatch.setattr("app.services.llm_client.request.urlopen", fake_urlopen)

    result = request_chat_completion_with_model([{"role": "user", "content": "hi"}], "deepseek-chat")

    assert result == '{"ok":true}'
    assert {key: captured[key] for key in ("url", "authorization", "timeout")} == {
        "url": "https://llm.example.com/v1/chat/completions",
        "authorization": "Bearer generic-key",
        "timeout": 60,
    }
    assert json.loads(captured["payload"].decode("utf-8"))["temperature"] == 0.2


def test_structured_json_allows_timeout_override(monkeypatch):
    monkeypatch.setattr(settings, "bounty_pool_llm_api_key", "generic-key")
    monkeypatch.setattr(settings, "bounty_pool_llm_model", "deepseek-chat")
    monkeypatch.setattr(settings, "bounty_pool_llm_base_url", "https://llm.example.com/v1")
    monkeypatch.setattr(settings, "bounty_pool_llm_timeout_seconds", 60)

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"choices":[{"message":{"content":"{\\"ok\\":true}"}}]}'

    def fake_urlopen(_http_request, timeout):
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.services.llm_client.request.urlopen", fake_urlopen)

    result = request_structured_json([{"role": "user", "content": "hi"}], timeout_seconds=120)

    assert result == '{"ok":true}'
    assert captured["timeout"] == 120
