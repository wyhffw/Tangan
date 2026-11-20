"""云端模型与本机 Ollama 的调用。

推荐解释只走云端。失败时由调用方改用模板，这里不会改调本机模型。
问答在云端失败后再试 Ollama。
"""

from collections.abc import Callable, Sequence
from typing import Literal

from openai import OpenAI

from app.core.config import Settings, get_settings

Purpose = Literal["recommend", "chat"]
Message = dict[str, str]
Completer = Callable[[Sequence[Message]], str]

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def resolve_cloud_base_url(settings: Settings) -> str:
    provider = settings.llm_provider.strip().lower()
    if provider == "deepseek":
        return DEEPSEEK_BASE_URL
    if provider in {"qwen", "tongyi", "dashscope"}:
        return QWEN_BASE_URL
    if settings.llm_base_url:
        return settings.llm_base_url
    raise ValueError(f"未知的 LLM_PROVIDER: {settings.llm_provider}")


def cloud_client(settings: Settings) -> OpenAI:
    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=resolve_cloud_base_url(settings),
        timeout=30,
    )


def ollama_client(settings: Settings) -> OpenAI:
    return OpenAI(api_key="ollama", base_url=settings.ollama_base_url, timeout=60)


def _complete(client: OpenAI, model: str, messages: Sequence[Message]) -> str:
    response = client.chat.completions.create(model=model, messages=list(messages))
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("模型返回空内容")
    return content


def generate(
    messages: Sequence[Message],
    *,
    purpose: Purpose,
    settings: Settings | None = None,
    cloud_complete: Completer | None = None,
    ollama_complete: Completer | None = None,
) -> str:
    explicit_settings = settings is not None
    settings = settings or get_settings()

    def default_cloud(msgs: Sequence[Message]) -> str:
        if explicit_settings:
            client = cloud_client(settings)
            model = settings.llm_model
        else:
            from app.core.llm_config import get_llm_config

            cfg = get_llm_config(settings)
            client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"], timeout=30)
            model = cfg["model"]
        return _complete(client, model, msgs)

    def default_ollama(msgs: Sequence[Message]) -> str:
        return _complete(ollama_client(settings), settings.ollama_model, msgs)

    cloud = cloud_complete or default_cloud
    local = ollama_complete or default_ollama
    try:
        return cloud(messages)
    except Exception:
        if purpose == "recommend":
            raise
    try:
        return local(messages)
    except Exception as local_exc:
        raise RuntimeError("云端和本机模型都不可用") from local_exc
