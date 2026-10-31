# NanoGPT provider plugin

OpenAI-compatible NanoGPT endpoint for Hermes. Does not change
`model.default`, does not store a key, does not send completions.

## Endpoint

- Base: `https://nano-gpt.com/api/v1` (direct API host for larger
  attachments: `https://api.nano-gpt.com`)
- Auth: `Authorization: Bearer sk-nano-<uuid>` (legacy plain-UUID keys also
  accepted; `X-API-Key` header works too)
- Subscription-only fence: `https://nano-gpt.com/api/subscription/v1/<path>`

## Keys (per account)

A key is scoped to ONE account's subscription — never reuse one key across
accounts. For per-key tracking, register one provider row per account:
`nanogpt-duck` → `NANOGPT_DUCK_API_KEY`, `nanogpt-clown` →
`NANOGPT_CLOWN_API_KEY` (`add_nanogpt.py --slug nanogpt-<label>`).

Create each key with billing mode **Subscription only** so out-of-catalog
models fail with HTTP 402 instead of draining the account's cash balance.

## Connect

Add `NANOGPT_API_KEY=sk-nano-...` yourself — never paste a key into chat.
Use `hermes auth add nanogpt` or your Hermes secret storage (mode 600), then
restart Hermes so the gateway reloads credentials.

HTTP 429 = that account's daily cap is exhausted (resets daily).

## Referral link (humans only)

Sign-up / pricing / top-up links for people:
**https://nano-gpt.com/r/AhJbKMxg** (code `AhJbKMxg`, 5% off eligible
usage; not on provider-selection pricing such as Caching mode or a pinned
provider). API endpoints NEVER use the `/r/` path — `base_url` stays
`https://nano-gpt.com/api/v1` in config, code, and docs.
