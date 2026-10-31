# hermes-nanogpt-provider

A [Hermes Agent](https://hermes-agent.nousresearch.com/docs/) skill that adds
[NanoGPT](https://nano-gpt.com/r/AhJbKMxg) to the provider list — including
per-account rows (`nanogpt-duck`, `nanogpt-clown`, …) so each API key is
tracked by name. It bundles a small model-provider plugin that supplies the
display metadata and the **Get key** link in Hermes Desktop.

The helper never changes your active model, never writes an API key, and never
sends a completion.

## Install

```bash
hermes skills install NostrDanish/hermes-nanogpt-provider/skills/hermes-nanogpt-provider
```

Then ask your agent to add NanoGPT, or run the helper from the installed skill
directory:

```bash
python3 scripts/add_nanogpt.py            # preview
python3 scripts/add_nanogpt.py --apply    # register providers.nanogpt
# one row per account/key:
python3 scripts/add_nanogpt.py --apply --slug nanogpt-duck
```

Add your key yourself (never paste an API key into a chat):

```bash
echo 'NANOGPT_API_KEY=sk-nano-...' >> ~/.hermes/.env
chmod 600 ~/.hermes/.env
```

Restart Hermes, then pick NanoGPT in the provider list.

## Provider details

- Base URL: `https://nano-gpt.com/api/v1` (direct API host for larger
  attachments: `https://api.nano-gpt.com`)
- Auth: `Authorization: Bearer sk-nano-<uuid>` (legacy plain-UUID keys
  accepted; `X-API-Key` header also works)
- OpenAI-compatible Chat Completions
- Catalog: `GET /api/v1/models` — keyless requests return the public list;
  your account's visible set may add `:free` variants
- Quota is **per account**: one key covers exactly one account's subscription.
  For several accounts, use `--slug nanogpt-<label>` rows (key slot
  `NANOGPT_<LABEL>_API_KEY`).
- Create keys with billing mode **Subscription only** so models outside that
  account's catalog fail with HTTP 402 instead of draining its cash balance.
- HTTP 429 means that account's daily cap is exhausted; it resets daily.

## Get a key

Sign-up / pricing link: **https://nano-gpt.com/r/AhJbKMxg**

This is the maintainer's referral invite — it costs you nothing extra, gives
you 5% off eligible usage, and keeps these free skills worth maintaining. The
same link is wired into the bundled plugin, so the Get-key button in Hermes
Desktop uses it automatically. API endpoints never use the referral path;
`base_url` is always `https://nano-gpt.com/api/v1`.

## Multi-account pattern

NanoGPT bills each account's subscription quota before its pay-as-you-go
balance, and a key is scoped to its own account only. One provider row per
key keeps usage attributable — and unlike a rotating credential pool, you can
always tell which key served a request (rotation also resets NanoGPT's
per-key prompt caches, so treat it as a failover mechanism, not a per-request
switch).

## License

MIT — see [LICENSE](LICENSE).
