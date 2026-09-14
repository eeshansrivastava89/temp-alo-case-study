from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import load_llm_config


class LLMConfigTests(unittest.TestCase):
    def test_missing_configuration_has_no_default_provider_or_model(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config, missing = load_llm_config()
        self.assertIsNone(config)
        self.assertEqual(set(missing), {"LLM_PROVIDER", "LLM_MODEL", "LLM_BASE_URL", "LLM_API_KEY"})

    def test_complete_configuration_is_loaded_from_one_contract(self) -> None:
        values = {
            "LLM_PROVIDER": "Example provider",
            "LLM_MODEL": "example/model",
            "LLM_BASE_URL": "https://example.com/v1/",
            "LLM_API_KEY": "secret",
        }
        config, missing = load_llm_config(values)
        self.assertFalse(missing)
        self.assertEqual(config.provider, "Example provider")
        self.assertEqual(config.model, "example/model")
        self.assertEqual(config.base_url, "https://example.com/v1")
        self.assertNotIn("secret", repr(config))

    def test_invalid_base_url_is_rejected(self) -> None:
        values = {
            "LLM_PROVIDER": "Example provider",
            "LLM_MODEL": "example/model",
            "LLM_BASE_URL": "example.com/v1",
            "LLM_API_KEY": "secret",
        }
        with self.assertRaises(ValueError):
            load_llm_config(values)


if __name__ == "__main__":
    unittest.main()
