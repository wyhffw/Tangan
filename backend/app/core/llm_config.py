"""网页端配置大模型的运行时存储。

Key 存到 backend/data/llm_config.json（.gitignore 已忽略），进程内缓存，
保存后无需重启即可生效。健康检查和 generate 都优先读这里的配置。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock

from app.core.config import Settings, get_settings

PROVIDER_BASE_URLS = {
    "deepseek": "https://api.deepseek.com",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}
PROVIDER_DEFAULT_MODELS = {
    "deepseek": "deepseek-chat",
    "qwen": "qwen-plus",
}

CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "llm_config.json"

_lock = Lock()
_cache: dict[str, str] | None = None
_loaded = False


def normalize_provider(provider: str) -> str:
    name = (provider or "").strip().lower()
    if name in {"qwen", "tongyi", "dashscope"}:
        return "qwen"
    if name == "ollama":
        return "ollama"
    return "deepseek"


def _load() -> dict[str, str]:
    global _cache, _loaded
    with _lock:
        if not _loaded:
            _cache = {}
            try:
                if CONFIG_PATH.exists():
                    _cache = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                _cache = {}
            _loaded = True
        return dict(_cache or {})


def get_llm_config(settings: Settings | None = None) -> dict[str, str]:
    """返回生效的 LLM 配置，运行时配置优先，缺省回退 .env。"""
    settings = settings or get_settings()
    runtime = _load()
    provider = normalize_provider(runtime.get("provider") or settings.llm_provider)
    if provider == "ollama":
        base_url = (runtime.get("base_url") or "").strip() or settings.ollama_base_url
        model = (runtime.get("model") or "").strip() or settings.ollama_model
        return {"provider": provider, "api_key": "ollama", "base_url": base_url, "model": model}
    base_url = (runtime.get("base_url") or "").strip() or PROVIDER_BASE_URLS[provider]
    model = (runtime.get("model") or "").strip() or PROVIDER_DEFAULT_MODELS[provider]
    api_key = runtime.get("api_key") or settings.llm_api_key or ""
    return {
        "provider": provider,
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
    }


def save_llm_config(
    provider: str,
    api_key: str,
    model: str = "",
    base_url: str = "",
) -> dict[str, str]:
    global _cache, _loaded
    provider = normalize_provider(provider)
    settings = get_settings()
    if provider == "ollama":
        data = {
            "provider": provider,
            "api_key": "",
            "model": (model or "").strip() or settings.ollama_model,
            "base_url": (base_url or "").strip() or settings.ollama_base_url,
        }
    else:
        data = {
            "provider": provider,
            "api_key": (api_key or "").strip(),
            "model": (model or "").strip() or PROVIDER_DEFAULT_MODELS[provider],
            "base_url": (base_url or "").strip() or PROVIDER_BASE_URLS[provider],
        }
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        _cache = dict(data)
        _loaded = True
        CONFIG_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        try:
            os.chmod(CONFIG_PATH, 0o600)
        except OSError:
            pass
    return dict(data)


def mask_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"
