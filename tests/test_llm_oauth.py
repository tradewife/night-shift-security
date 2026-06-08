"""Tests for zero-cost LLM credential resolution."""

import json
from pathlib import Path
from unittest.mock import patch

from night_shift_security.domain.attack_hypotheses.llm_provider import (
    _token_from_auth_file,
    create_llm_provider,
    resolve_litellm_credentials,
)


def test_token_from_auth_file_reads_first_key(tmp_path: Path):
    auth = {
        "https://auth.x.ai::client": {"key": "test-token-abc"},
    }
    path = tmp_path / "auth.json"
    path.write_text(json.dumps(auth))
    assert _token_from_auth_file(path) == "test-token-abc"


def test_resolve_litellm_credentials_prefers_env():
    with patch.dict("os.environ", {"XAI_API_KEY": "env-key"}):
        key, base, source = resolve_litellm_credentials(
            {"api_key_env": "XAI_API_KEY", "api_base": "https://api.x.ai/v1"}
        )
    assert key == "env-key"
    assert source == "XAI_API_KEY"


def test_resolve_litellm_credentials_falls_back_to_grok_oauth(tmp_path: Path):
    auth = {"issuer": {"key": "oauth-token"}}
    grok_path = tmp_path / "auth.json"
    grok_path.write_text(json.dumps(auth))
    with patch.dict("os.environ", {}, clear=True):
        with patch(
            "night_shift_security.domain.attack_hypotheses.llm_provider._GROK_AUTH_PATH",
            grok_path,
        ):
            key, _, source = resolve_litellm_credentials(
                {"api_key_env": "XAI_API_KEY", "auth_source": "grok_oauth"}
            )
    assert key == "oauth-token"
    assert source == "grok_oauth"


def test_create_llm_provider_with_oauth_token(tmp_path: Path):
    auth = {"issuer": {"key": "oauth-token"}}
    grok_path = tmp_path / "auth.json"
    grok_path.write_text(json.dumps(auth))
    with patch.dict("os.environ", {}, clear=True):
        with patch(
            "night_shift_security.domain.attack_hypotheses.llm_provider._GROK_AUTH_PATH",
            grok_path,
        ):
            provider = create_llm_provider(
                {
                    "provider": "litellm",
                    "model": "xai/grok-4",
                    "api_key_env": "XAI_API_KEY",
                    "auth_source": "grok_oauth",
                    "api_base": "https://api.x.ai/v1",
                }
            )
    assert provider is not None
    assert provider.provider_name == "litellm"