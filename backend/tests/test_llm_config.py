from pathlib import Path

import pytest

from app.core import llm_config
from app.core.config import Settings


@pytest.fixture(autouse=True)
def _reset_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_config, "CONFIG_PATH", tmp_path / "llm_config.json")
    monkeypatch.setattr(llm_config, "_cache", None)
    monkeypatch.setattr(llm_config, "_loaded", False)


def test_normalize_provider() -> None:
    assert llm_config.normalize_provider("deepseek") == "deepseek"
    assert llm_config.normalize_provider("qwen") == "qwen"
    assert llm_config.normalize_provider("tongyi") == "qwen"
    assert llm_config.normalize_provider("unknown") == "deepseek"


def test_mask_key() -> None:
    assert llm_config.mask_key("") == ""
    assert llm_config.mask_key("short") == "*****"
    masked = llm_config.mask_key("sk-abcdefghijklmnop")
    assert masked.startswith("sk-a")
    assert masked.endswith("mnop")
    assert "*" in masked


def test_get_llm_config_falls_back_to_settings() -> None:
    cfg = llm_config.get_llm_config(Settings(llm_provider="qwen", llm_api_key="k"))
    assert cfg["provider"] == "qwen"
    assert cfg["api_key"] == "k"
    assert cfg["base_url"] == llm_config.PROVIDER_BASE_URLS["qwen"]
    assert cfg["model"] == llm_config.PROVIDER_DEFAULT_MODELS["qwen"]


def test_save_then_get_roundtrip() -> None:
    llm_config.save_llm_config("deepseek", "sk-test", model="deepseek-reasoner")
    cfg = llm_config.get_llm_config(Settings(llm_api_key=""))
    assert cfg["api_key"] == "sk-test"
    assert cfg["model"] == "deepseek-reasoner"
    assert cfg["base_url"] == llm_config.PROVIDER_BASE_URLS["deepseek"]


def test_runtime_config_overrides_env() -> None:
    llm_config.save_llm_config("deepseek", "sk-runtime")
    cfg = llm_config.get_llm_config(Settings(llm_api_key="sk-env"))
    assert cfg["api_key"] == "sk-runtime"


def test_config_file_is_persisted(tmp_path: Path) -> None:
    llm_config.save_llm_config("qwen", "sk-persist")
    assert (tmp_path / "llm_config.json").exists()
    text = (tmp_path / "llm_config.json").read_text(encoding="utf-8")
    assert "sk-persist" in text
