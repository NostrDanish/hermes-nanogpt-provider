"""Offline tests for the NanoGPT registration helper (no network, no writes)."""

import importlib.util
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "hermes-nanogpt-provider"
SCRIPT = SKILL_DIR / "scripts" / "add_nanogpt.py"

spec = importlib.util.spec_from_file_location("add_nanogpt", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_key_env_derivation():
    assert mod.key_env_for("nanogpt") == "NANOGPT_API_KEY"
    assert mod.key_env_for("nanogpt-duck") == "NANOGPT_DUCK_API_KEY"
    assert mod.key_env_for("nanogpt-clown") == "NANOGPT_CLOWN_API_KEY"
    assert mod.key_env_for("nanogpt-second-account") == "NANOGPT_SECOND_ACCOUNT_API_KEY"


def test_slug_guard():
    assert mod.SLUG_RE.match("nanogpt")
    assert mod.SLUG_RE.match("nanogpt-duck")
    # the picker-created nano-gpt row is a different key and must never match
    assert not mod.SLUG_RE.match("nano-gpt")
    assert not mod.SLUG_RE.match("nanogpt_DUCK")
    assert not mod.SLUG_RE.match("openrouter")
    assert not mod.SLUG_RE.match("")


def test_parse_model_ids_defensive():
    assert mod.parse_model_ids({"data": [{"id": "a"}, {"id": "b"}, "c"]}) == ["a", "b", "c"]
    assert mod.parse_model_ids(["x"]) == ["x"]
    assert mod.parse_model_ids({}) == []
    assert mod.parse_model_ids("nope") == []
    assert mod.parse_model_ids({"data": None}) == []


def test_pick_model():
    assert mod.pick_model() == "poolside/laguna-s-2.1:free"
    assert mod.pick_model("z-ai/glm-5.3-flash") == "z-ai/glm-5.3-flash"


def test_plugin_carries_referral_and_clean_endpoint():
    src = (SKILL_DIR / "plugins" / "model-providers" / "nanogpt" / "__init__.py").read_text()
    invite = "https://nano-gpt.com/r/AhJbKMxg"
    assert invite in src, "plugin must surface the referral invite as signup_url"
    assert 'base_url' in src and "https://nano-gpt.com/api/v1" in src
    for line in src.splitlines():
        if "nano-gpt.com/r/" in line:
            assert "base_url" not in line, f"referral path must never be a base_url: {line}"


def test_skill_states_referral_policy():
    skill = (SKILL_DIR / "SKILL.md").read_text()
    assert "https://nano-gpt.com/r/AhJbKMxg" in skill
    assert "https://nano-gpt.com/api/v1" in skill
