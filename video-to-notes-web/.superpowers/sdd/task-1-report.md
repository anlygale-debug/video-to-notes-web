# Task 1 Report: Switch `_call_llm()` from Anthropic to OpenAI-compatible API format

## Status: DONE

## Changes Made

### 1. Replaced `_call_llm()` (lines 354-378)

- Endpoint: `/messages` → `/chat/completions`
- Auth header: `x-api-key: {key}` → `Authorization: Bearer {key}`
- Removed `anthropic-version` header
- Response parsing: `content[].text` iteration → `resp["choices"][0]["message"]["content"]`
- Docstring updated to reflect OpenAI compatibility

### 2. Updated `/api/test-connection` endpoint (extra, not in brief)

- Same set of changes as `_call_llm` for consistency (endpoint, auth header, response check from `"content" in resp` to `"choices" in resp`)

### 3. Verified default `api_base`

- Line 327 already set to `https://api.deepseek.com/v1` — no change needed

### 4. Syntax verification

- `python3 -c "from app import app; print('OK')"` → OK

## Commits

- `b2e6c1d` feat: switch _call_llm to OpenAI-compatible API format

## Notes

- `_read_api_config()` still reads `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_BASE_URL` / `ANTHROPIC_MODEL` env vars. These are just naming conventions and work fine — DeepSeek accepts the same key regardless of API format. No change needed.
- The `/api/test-connection` endpoint was also updated to use `/chat/completions` with `Authorization: Bearer` to match the new format.
