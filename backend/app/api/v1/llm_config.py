from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.llm_config import (
    PROVIDER_BASE_URLS,
    PROVIDER_DEFAULT_MODELS,
    get_llm_config,
    mask_key,
    normalize_provider,
    save_llm_config,
)
from app.core.config import get_settings
from app.models.entities import User
from app.schemas.llm_config import LlmConfigIn, LlmConfigOut, LlmTestResult

router = APIRouter(prefix="/llm-config", tags=["llm-config"])


def _public(cfg: dict[str, str]) -> dict[str, object]:
    key = cfg["api_key"]
    return {
        "provider": cfg["provider"],
        "model": cfg["model"],
        "base_url": cfg["base_url"],
        "api_key_masked": mask_key(key),
        "configured": bool(key),
        "status": "up" if key else "down",
    }


@router.get("", response_model=LlmConfigOut)
def read_config(_: Annotated[User, Depends(get_current_user)]) -> dict[str, object]:
    return _public(get_llm_config())


@router.put("", response_model=LlmConfigOut)
def write_config(
    payload: LlmConfigIn,
    _: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    cfg = save_llm_config(
        payload.provider, payload.api_key, payload.model, payload.base_url
    )
    return _public(cfg)


@router.post("/test", response_model=LlmTestResult)
def test_config(
    payload: LlmConfigIn,
    _: Annotated[User, Depends(get_current_user)],
) -> LlmTestResult:
    current = get_llm_config()
    provider = normalize_provider(payload.provider or current["provider"])
    if provider == "ollama":
        settings = get_settings()
        api_key = "ollama"
        base_url = (payload.base_url or "").strip() or settings.ollama_base_url
        model = (payload.model or "").strip() or settings.ollama_model
    else:
        api_key = (payload.api_key or "").strip() or current["api_key"]
        base_url = (payload.base_url or "").strip() or PROVIDER_BASE_URLS[provider]
        model = (payload.model or "").strip() or PROVIDER_DEFAULT_MODELS[provider]
        if not api_key:
            return LlmTestResult(ok=False, message="请先填写 API Key")

    from openai import OpenAI

    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=10)
        client.models.list()
        return LlmTestResult(ok=True, message="连接成功，模型可用")
    except Exception as exc:  # noqa: BLE001  给用户友好提示，不抛给接口
        detail = str(exc)
        if api_key and api_key in detail:
            detail = detail.replace(api_key, "***")
        return LlmTestResult(ok=False, message=f"连接失败：{detail[:200]}")
