"""
Tests for skillforge.config — configuration loading and merging.
"""

import os
from unittest.mock import patch

from skillforge.config import SkillForgeConfig, load_config


class TestConfigLoading:
    def test_default_config_loads(self):
        cfg = load_config()
        assert isinstance(cfg, SkillForgeConfig)
        assert cfg.bench_runs > 0
        assert cfg.clawhub_api.startswith("https://")

    def test_env_var_overrides_llm_model(self):
        with patch.dict(os.environ, {"SKILLFORGE_LLM_MODEL": "openai/gpt-4o"}):
            cfg = load_config()
        assert cfg.llm_model == "openai/gpt-4o"

    def test_anthropic_api_key_env_alias(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-123"}):
            cfg = load_config()
        assert cfg.llm_api_key == "test-key-123"

    def test_auto_sign_default_true(self):
        cfg = load_config()
        assert cfg.auto_sign is True

    def test_scan_block_on_high_default_true(self):
        cfg = load_config()
        assert cfg.scan_block_on_high is True

    def test_default_platforms_clawhub(self):
        from skillforge.models import Platform

        cfg = load_config()
        assert Platform.CLAWHUB in cfg.default_platforms
