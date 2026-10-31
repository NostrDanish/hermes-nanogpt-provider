"""NanoGPT provider (OpenAI-compatible, per-account subscription quota).

One fixed endpoint: ``https://nano-gpt.com/api/v1`` (direct API host
``https://api.nano-gpt.com`` for larger attachments). Keys are scoped to a
single account's subscription — never share one key across accounts expecting
pooled quota. Per-account tracking uses separate config rows
(``providers.nanogpt-<label>``) each with its own ``key_env``.
"""

from __future__ import annotations

from providers import register_provider
from providers.base import ProviderProfile

_DEFAULT_BASE = "https://nano-gpt.com/api/v1"

# House referral link for HUMAN-FACING surfaces only (sign-up, pricing,
# "get a key"). API calls must always hit the plain endpoint — the /r/
# referral path must never appear in a base_url, curl, or SDK call.
_SIGNUP = "https://nano-gpt.com/r/AhJbKMxg"


nanogpt = ProviderProfile(
    name="nanogpt",
    display_name="NanoGPT",
    description="NanoGPT — OpenAI-compatible inference with per-account subscriptions",
    signup_url=_SIGNUP,
    # NANOGPT_API_KEY is the fleet convention; the Desktop picker-created
    # nano-gpt row uses HERMES_CUSTOM_NANO_GPT_API_KEY. Both accepted.
    env_vars=("NANOGPT_API_KEY", "HERMES_CUSTOM_NANO_GPT_API_KEY"),
    base_url=_DEFAULT_BASE,
    auth_type="api_key",
    api_mode="chat_completions",
    aggregator=True,
    default_aux_model="poolside/laguna-s-2.1:free",
    default_headers={"User-Agent": "hermes-nanogpt-plugin/0.1.0"},
    # Curated-first in the picker; live GET /api/v1/models (needs a key)
    # replaces this list once a key is configured and Hermes restarts.
    fallback_models=(
        "poolside/laguna-s-2.1:free",
        "poolside/laguna-s-2.1",
        "qwen/qwen3.8-flash",
        "google/gemma4-31b-splituntied",
        "z-ai/glm-5.3-flash",
        "mistralai/mistral-small-24b-instruct-2501",
    ),
)

register_provider(nanogpt)
