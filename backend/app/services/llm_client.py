import json
from urllib import error, request

from app.core.config import settings


class LlmClientError(RuntimeError):
    pass


def should_use_llm() -> bool:
    return settings.bounty_pool_intelligence_llm_enabled and bool(active_llm_api_key())


def request_structured_json(messages: list[dict]) -> str:
    errors: list[str] = []
    for model_name in iter_llm_models():
        try:
            return request_chat_completion_with_model(messages, model_name)
        except Exception as exc:
            errors.append(f"{model_name}: {exc}")

    raise LlmClientError("; ".join(errors))


def request_chat_completion_with_model(messages: list[dict], model_name: str) -> str:
    payload = build_chat_completion_payload(messages, model_name)
    endpoint = f"{active_llm_base_url().rstrip('/')}/chat/completions"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    http_request = request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {active_llm_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=20) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise LlmClientError(f"LLM request failed with {exc.code}: {error_body}") from exc
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LlmClientError("LLM request failed") from exc

    try:
        message_content = response_body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmClientError("LLM response is missing content") from exc

    if not isinstance(message_content, str):
        raise LlmClientError("LLM response content must be a string")

    return message_content


def build_chat_completion_payload(messages: list[dict], model_name: str) -> dict:
    return {
        "model": model_name,
        "temperature": 0.55,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }


def iter_llm_models() -> list[str]:
    if settings.bounty_pool_llm_model:
        models = [settings.bounty_pool_llm_model]
        fallback_models = settings.bounty_pool_llm_fallback_models
    else:
        models = [settings.bounty_pool_zhipu_model]
        fallback_models = settings.bounty_pool_zhipu_fallback_models
    models.extend(item.strip() for item in fallback_models.split(",") if item.strip())

    deduped: list[str] = []
    for item in models:
        if item not in deduped:
            deduped.append(item)
    return deduped


def active_llm_api_key() -> str | None:
    return settings.bounty_pool_llm_api_key or settings.bounty_pool_zhipu_api_key


def active_llm_base_url() -> str:
    return settings.bounty_pool_llm_base_url or settings.bounty_pool_zhipu_base_url
