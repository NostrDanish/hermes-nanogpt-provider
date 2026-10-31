#!/usr/bin/env python3
"""Register NanoGPT in Hermes providers: so the Desktop list shows it.

Probes `https://nano-gpt.com/api/v1/models` keyless (HTTP 200 returns the
public catalog; 401/403 = endpoint alive), copies the bundled model-provider
plugin, then writes `providers.<slug>.*` via `hermes config set`. Supports
per-account slugs (`nanogpt-duck`) so each API key is tracked by name.
Registration never sends a key, never changes model.provider or model.default,
and never sends a completion.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
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
    """Curated default; the live catalog is only visible after a key is added."""
    if override:
        return override.strip()
    return PREFERRED_MODELS[0]


def hermes_bin() -> str:
    found = shutil.which("hermes")
    if not found:
        raise SystemExit("hermes not on PATH")
    return found


def hermes_env(home: str | None) -> dict[str, str]:
    env = os.environ.copy()
    if home:
        env["HERMES_HOME"] = home
    return env


def hermes_run(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [hermes_bin(), "config", *args], env=env, capture_output=True, text=True, timeout=30
    )


def hermes_get(key: str, env: dict[str, str], *, as_json: bool = False) -> str:
    args = ["get", key] + (["--json"] if as_json else [])
    proc = hermes_run(args, env)
    if proc.returncode != 0:
        raise SystemExit(f"hermes config get {key} failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout.strip()


def hermes_get_optional(key: str, env: dict[str, str]) -> str:
    proc = hermes_run(["get", key], env)
    if proc.returncode != 0 or not proc.stdout.strip():
        return "(unset)"
    return proc.stdout.strip()


def hermes_set(key: str, value: str, env: dict[str, str]) -> None:
    proc = hermes_run(["set", key, value], env)
    if proc.returncode != 0:
        raise SystemExit(f"hermes config set {key} failed: {proc.stderr.strip() or proc.stdout.strip()}")


def row_exists(slug: str, env: dict[str, str]) -> bool:
    proc = hermes_run(["get", f"providers.{slug}", "--json"], env)
    if proc.returncode != 0:
        return False
    out = proc.stdout.strip()
    return bool(out) and out not in ("null", "{}")


def snapshot_defaults(env: dict[str, str]) -> tuple[str, str]:
    return hermes_get_optional("model.provider", env), hermes_get_optional("model.default", env)


def resolve_home(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    env_home = os.environ.get("HERMES_HOME")
    if env_home:
        return Path(env_home)
    return Path.home() / ".hermes"


def copy_plugin(home: Path) -> Path:
    """Copy the bundled plugin into <home>/plugins/model-providers/nanogpt."""
    src = Path(__file__).resolve().parent.parent / "plugins" / "model-providers" / PROVIDER
    if not src.is_dir():
        raise SystemExit(f"bundled plugin not found at {src}")
    dst = home / "plugins" / "model-providers" / PROVIDER
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return dst


def apply_row(slug: str, base_url: str, model: str, key_env: str, env: dict[str, str]) -> None:
    fields = {
        f"providers.{slug}.name": slug,
        f"providers.{slug}.base_url": base_url,
        f"providers.{slug}.model": model,
        f"providers.{slug}.discover_models": "true",
        f"providers.{slug}.api_mode": "chat_completions",
        f"providers.{slug}.key_env": key_env,
    }
    for key, value in fields.items():
        hermes_set(key, value, env)


def verify(slug: str, base_url: str, model: str, key_env: str, before: tuple[str, str], env: dict[str, str]) -> dict:
    entry = json.loads(hermes_get(f"providers.{slug}", env, as_json=True))
    expected = {
        "name": slug,
        "base_url": base_url,
        "model": model,
        "api_mode": "chat_completions",
        "key_env": key_env,
    }
    mismatches = [k for k, v in expected.items() if entry.get(k) != v]
    if entry.get("discover_models") is not True:
        mismatches.append("discover_models")
    after = snapshot_defaults(env)
    if after != before:
        raise SystemExit(f"default model changed: {before} -> {after}")
    if mismatches:
        raise SystemExit(f"readback mismatch: {mismatches} entry={entry}")
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add NanoGPT to the Hermes provider list.")
    parser.add_argument("--apply", action="store_true", help="Write providers.<slug> via hermes config set.")
    parser.add_argument("--slug", default=PROVIDER, help="'nanogpt' or a per-account row 'nanogpt-<label>'.")
    parser.add_argument("--base-url", default=BASE_URL, help=f"Default {BASE_URL}. Still probed keyless.")
    parser.add_argument("--model", default="", help="Row default model (curated default; catalog only visible after a key is added).")
    parser.add_argument("--key-env", default="", help="Override the derived key slot.")
    parser.add_argument("--force", action="store_true", help="Allow overwriting an existing providers.<slug> row.")
    parser.add_argument("--home", default="", help="HERMES_HOME for this run. Does not change the process default.")
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

    print(f"slug {slug}")
    catalog_note = f"public catalog, {len(ids)} ids" if ids else f"auth-gated (HTTP {status})"
    print(f"base_url {args.base_url.rstrip('/')} (probe HTTP {status}: {catalog_note})")
    print(f"model {model}")
    print(f"key_env {key_env}")
    print(f"referral (human links only) {REFERRAL_LINK}")
    if not args.apply:
        print("dry-run (pass --apply to write this row only)")
        return 0

    env = hermes_env(args.home.strip() or None)
    if row_exists(slug, env) and not args.force:
        raise SystemExit(f"providers.{slug} already exists; pass --force to overwrite")

    before = snapshot_defaults(env)
    apply_row(slug, args.base_url.rstrip("/"), model, key_env, env)
    entry = verify(slug, args.base_url.rstrip("/"), model, key_env, before, env)

    plugin_dst = copy_plugin(resolve_home(args.home.strip() or None))
    print(f"plugin {plugin_dst}")

    print("verified")
    print(json.dumps({f"providers.{slug}": entry, "model.provider": before[0], "model.default": before[1]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
