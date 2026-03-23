from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_provider: Literal["anthropic", "gemini", "openai"] = "anthropic"
    llm_model: str = ""

    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def check_api_key(self):
        key_map = {
            "anthropic": self.anthropic_api_key,
            "gemini": self.gemini_api_key,
            "openai": self.openai_api_key,
        }
        if not key_map[self.llm_provider]:
            env_name = {
                "anthropic": "ANTHROPIC_API_KEY",
                "gemini": "GEMINI_API_KEY",
                "openai": "OPENAI_API_KEY",
            }[self.llm_provider]
            raise ValueError(
                f"LLM_PROVIDER is '{self.llm_provider}' but {env_name} is not set"
            )
        return self

    @property
    def active_model(self) -> str:
        if self.llm_model:
            return self.llm_model
        defaults = {
            "anthropic": "claude-sonnet-4-6-20250514",
            "gemini": "gemini-2.5-flash",
            "openai": "gpt-4o",
        }
        return defaults[self.llm_provider]


settings = Settings()
