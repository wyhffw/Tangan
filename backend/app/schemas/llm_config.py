from pydantic import BaseModel, Field


class LlmConfigIn(BaseModel):
    provider: str = Field(default="deepseek")
    api_key: str = ""
    model: str = ""
    base_url: str = ""


class LlmConfigOut(BaseModel):
    provider: str
    model: str
    base_url: str
    api_key_masked: str
    configured: bool
    status: str


class LlmTestResult(BaseModel):
    ok: bool
    message: str
