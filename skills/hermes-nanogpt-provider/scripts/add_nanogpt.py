#!/usr/bin/env python3
"""Plan a NanoGPT provider row for Hermes. READ-ONLY by design.

Probes `https://nano-gpt.com/api/v1/models` keyless, then PRINTS the exact
`hermes config set` commands that register `providers.<slug>.*`. It never
writes config, never reads or writes environment variables, never launches
other programs, and never sends a completion. Staying read-only is what keeps
this skill installable: Hermes Skills Guard blocks community skills whose
helpers launch programs or touch the environment, so all writes happen
through the `hermes config set` commands printed here, run by the agent or
user.

Per-account slugs keep each key attributable: `nanogpt-duck` gets key slot
`NANOGPT_DUCK_API_KEY`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROVIDER = "nanogpt"
BASE_URL = "https://nano-gpt.com/api/v1"
REFERRAL_LINK = "https://nano-gpt.com/r/AhJbKMxg"
PREFERRED_MODELS = (
    "poolside/laguna-s-2.1:free",
    "poolside/laguna-s-2.1",
    "qwen/qwen3.8-flash",
)
SLUG_RE = re.compile(r"^nanogpt(-[a-z0-9][a-z0-9-]*)?$")
USER_AGENT = "hermes-nanogpt-provider/0.1"


def key_env_for(slug: str) -> str:
    """Fleet convention: NANOGPT_API_KEY, or NANOGPT_<LABEL>_API_KEY per account."""
    if slug == PROVIDER:
        return "NANOGPT_API_KEY"
    label = slug[len(PROVIDER) + 1 :].upper().replace("-", "_")
    return f"NANOGPT_{label}_API_KEY"


def parse_model_ids(payload: object) -> list[str]:
    """Defensively pull model ids from an OpenAI-style /models response."""
    if isinstance(payload, dict):
        items = payload.get("data")
    elif isinstance(payload, list):
        items = payload
    else:
        return []
    if not isinstance(items, list):
        return []
    ids: list[str] = []
    for item in items:
        if isinstance(item, dict) and item.get("id"):
            ids.append(str(item["id"]))
        elif isinstance(item, str) and item.strip():
            ids.append(item.strip())
    return ids


def probe(base_url: str, timeout: float = 12.0) -> tuple[int | None, list[str]]:
    """Keyless GET <base>/models. Return (HTTP status, public model ids).

    200 returns the PUBLIC catalog (account-scoped ids like ':free' variants
    are not listed). 401/403 still prove the endpoint is alive. None status =
    network failure. Never attach an Authorization header in this script.
    """
    url = base_url.strip().rstrip("/") + "/models"
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            status = resp.status
    except urllib.error.HTTPError as err:
        return err.code, []
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None, []
    try:
        ids = parse_model_ids(json.loads(body.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError):
        ids = []
    return status, ids


def pick_model(override: str | None = None) -> str:
    """Curated default; the account's real set appears after the key is added."""
    if override:
        return override.strip()
    return PREFERRED_MODELS[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print the hermes commands that register a NanoGPT provider row. Read-only."
    )
    parser.add_argument("--slug", default=PROVIDER, help="'nanogpt' or a per-account row 'nanogpt-<label>'.")
    parser.add_argument("--base-url", default=BASE_URL, help=f"Default {BASE_URL}. Still probed keyless.")
    parser.add_argument("--model", default="", help="Row default model (curated default; catalog only visible after a key is added).")
    parser.add_argument("--key-env", default="", help="Override the derived key slot.")
    parser.add_argument("--home", default="", help="Profile home to target: prefix the printed commands with HERMES_HOME=<home>.")
    args = parser.parse_args(argv)

    slug = args.slug.strip()
    if not SLUG_RE.match(slug):
        raise SystemExit(f"slug must be 'nanogpt' or 'nanogpt-<label>', got {slug!r}")

    status, ids = probe(args.base_url)
    if status is None:
        raise SystemExit(f"endpoint unreachable: {args.base_url} (network failure)")
    if status not in (200, 401, 403):
        raise SystemExit(f"endpoint unhealthy: {args.base_url} returned HTTP {status}")

    model = pick_model(args.model or None)
    if args.model and ids and model not in ids:
        print(
            f"note: {model!r} is not in the public catalog ({len(ids)} ids); "
            "account-scoped ids like ':free' variants are not listed publicly — continuing"
        )
    key_env = args.key_env.strip() or key_env_for(slug)

    catalog_note = f"public catalog, {len(ids)} ids" if ids else f"auth-gated (HTTP {status})"
    print(f"slug {slug}")
    print(f"base_url {args.base_url.rstrip('/')} (probe HTTP {status}: {catalog_note})")
    print(f"model {model}")
    print(f"key_env {key_env}")
    print(f"referral (human links only) {REFERRAL_LINK}")

    base = args.base_url.rstrip("/")
    fields = {
        f"providers.{slug}.name": slug,
        f"providers.{slug}.base_url": base,
        f"providers.{slug}.model": model,
        f"providers.{slug}.discover_models": "true",
        f"providers.{slug}.api_mode": "chat_completions",
        f"providers.{slug}.key_env": key_env,
    }
    print("\n# 1) register the row (the only config writes):")
    if args.home.strip():
        print(f"#    prefix each command with: HERMES_HOME={args.home.strip()}")
    for key, value in fields.items():
        print(f"hermes config set {key} {value}")

    plugin_src = Path(__file__).resolve().parent.parent / "plugins" / "model-providers" / PROVIDER
    print("\n# 2) install the plugin (display name + Get-key link):")
    print(f"cp -r '{plugin_src}' ~/.hermes/plugins/model-providers/")

    print("\n# 3) verify the row and that defaults are untouched:")
    print(f"hermes config get providers.{slug} --json")
    print("hermes config get model.provider && hermes config get model.default")

    print(f"\n# 4) the user adds {key_env} themselves (Hermes secret storage")
    print("#    or `hermes auth add nanogpt`), then restarts Hermes.")
    print("#    sign-up / top-up link for humans (never an API endpoint):")
    print(f"#    {REFERRAL_LINK}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
