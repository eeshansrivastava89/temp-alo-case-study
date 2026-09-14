"""Single explicit configuration contract for OpenAI-compatible LLM providers."""

import os
from dataclasses import dataclass, field
from typing import Mapping

REQUIRED_LLM_SETTINGS = (
    "LLM_PROVIDER",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "LLM_API_KEY",
)


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    base_url: str
    api_key: str = field(repr=False)

    @property
    def display_name(self) -> str:
        return f"{self.provider} · {self.model}"


def load_llm_config(overrides: Mapping[str, object] | None = None) -> tuple[LLMConfig | None, tuple[str, ...]]:
    values = {name: os.getenv(name, "") for name in REQUIRED_LLM_SETTINGS}
    if overrides:
        for name in REQUIRED_LLM_SETTINGS:
            if name in overrides:
                values[name] = str(overrides[name]).strip()

    missing = tuple(name for name, value in values.items() if not str(value).strip())
    if missing:
        return None, missing

    base_url = str(values["LLM_BASE_URL"]).rstrip("/")
    if not base_url.startswith(("https://", "http://")):
        raise ValueError("LLM_BASE_URL must be an HTTP or HTTPS URL")

    return (
        LLMConfig(
            provider=str(values["LLM_PROVIDER"]),
            model=str(values["LLM_MODEL"]),
            base_url=base_url,
            api_key=str(values["LLM_API_KEY"]),
        ),
        (),
    )
