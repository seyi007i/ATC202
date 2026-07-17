# SafeBank Companion

A locally-run, Claude-powered web assistant that helps Nigerian mobile-money
users recognize scams, understand fraud risk, and learn how to stay safe.
SafeBank Companion focuses entirely on **fraud awareness and education** — it
never gives legal, investment, or financial advice, and never helps commit
fraud of any kind.

## Overview

SafeBank Companion is a FastAPI + Jinja2 + vanilla JS web app backed by the
Anthropic Claude API. Users chat with the assistant, paste suspicious SMS /
email / WhatsApp messages, and receive:

- A plain-English explanation of whether a message looks like a scam.
- A structured risk assessment (risk level, confidence, red flags, and
  recommended next actions).
- Clear next steps if they believe they've already been targeted (e.g. a lost
  phone or an active scam).
- A simulated escalation ticket for high-risk cases.

## Features

- **Chat interface** — a modern chat window with conversation history, a
  loading indicator, a risk-assessment card, a recommended-actions list, and a
  fraud warning banner for high-risk messages.
- **Fraud red-flag tool** — `fraud_red_flag_check(message)`, a deterministic
  heuristic tool exposed to Claude that detects OTP/PIN/BVN/password
  requests, suspicious URLs, fake urgency, threats, account-suspension
  scams, prize scams, and fake customer support. Claude decides when to call
  it — the app does not hardcode "if scam keyword, call tool" routing.
- **Structured, validated output** — every fraud assessment is validated
  against a Pydantic model (`risk_level`, `confidence` in `[0, 1]`,
  `flags`, non-empty `recommended_actions`, `should_escalate`).
- **Multi-turn conversation management** — tracks prior scam discussions,
  recommendations, and escalation state per session; summarizes older turns
  after ~10 exchanges to keep token usage down.
- **PII redaction** — passwords, PINs, OTPs, BVNs, and full account numbers
  are redacted from user text *before* it is stored or sent to Claude, so raw
  secrets never persist or leave the machine, even transiently.
- **Reliability layer** — hand-rolled exponential backoff (1s / 2s / 4s, max
  3 retries) for transient API failures, a 30-second request timeout, and
  friendly error messages for invalid input, API failures, malformed JSON,
  validation errors, a missing API key, tool failures, and network issues.
- **6-step agent loop** — one call to the main model per step; a tool call
  loops for another step, a plain-text reply ends the turn. Stops when the
  user's request is answered, an escalation is completed, or 6 steps are
  reached.
- **Fraud-analysis subagent** — a specialist call to `claude-sonnet-4-5-20250929`,
  invoked only when multiple red flags are present, confidence is below 70%,
  evidence conflicts, or active fraud is suspected. It never talks to the
  user directly; its reasoning is folded into the main model's next system
  prompt only.
- **Simulated escalation** — high-risk, `should_escalate: true` cases create
  a local ticket (`ESC-XXXXXXXX`) appended to a JSONL file. No real external
  system is contacted.

## Architecture

```
                         ┌─────────────────────────┐
                         │        Browser          │
                         │  index.html / chat.html │
                         │       + chat.js         │
                         └───────────┬─────────────┘
                                     │ fetch("/api/chat")
                                     ▼
┌────────────────────────────────────────────────────────────────────┐
│                          FastAPI (app/main.py)                     │
│  GET /  GET /chat  GET /api/health  POST /api/chat                 │
└───────────────────────────────┬────────────────────────────────────┘
                                 ▼
                     ┌───────────────────────┐
                     │   AgentLoop (≤6 steps) │
                     │   app/agent_loop.py    │
                     └──┬───────────┬─────────┘
                        │           │
             tool_use   │           │ plain text
                        ▼           ▼
        ┌───────────────────┐   ┌─────────────────────────────┐
        │ fraud_red_flag_    │   │ Extract trailing            │
        │ check (app/tools)  │   │ ```safebank-assessment```    │
        └─────────┬──────────┘   │ block → Pydantic validate    │
                  │               └─────────────┬───────────────┘
     ≥2 flags /   │                             │
     low confidence▼                            ▼
        ┌───────────────────────┐    ┌───────────────────────────┐
        │ Fraud-analysis        │    │ should_escalate?           │
        │ subagent               │   │  → EscalationStore          │
        │ (claude-sonnet-4-5)    │    │    (simulated JSONL ticket)│
        │ app/subagent.py        │    └───────────────────────────┘
        │ → notes folded into    │
        │   next system prompt   │
        │   (never shown to user)│
        └───────────────────────┘

        ConversationManager (app/conversation.py): per-session history,
        redaction-before-store, summarization after ~10 exchanges.

        AnthropicAgentClient (app/anthropic_client.py) + retry.py:
        1s/2s/4s backoff, max 3 retries, 30s timeout, exception translation.
```

## Installation

Requires Python 3.12+.

```bash
cd task3
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Configuration

Copy the example environment file and add your Anthropic API key:

```bash
cp .env.example .env
```

Edit `.env`:

```
ANTHROPIC_API_KEY=sk-ant-your-real-key-here
```

All other settings in `.env.example` (models, timeouts, retry counts, agent
step cap, summarization threshold) have sensible defaults and are optional
overrides.

## Claude API setup

1. Create an account at [console.anthropic.com](https://console.anthropic.com/).
2. Generate an API key.
3. Set `ANTHROPIC_API_KEY` in `.env` (never commit this file or hardcode the
   key in source).

The app fails fast with a friendly message at startup if the key is missing.

## Running locally

```bash
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/` in a browser, click **Start Chat**, and
try pasting a suspicious message or asking a safety question.

## Testing

```bash
pytest
```

This runs the full suite (unit tests for every module, end-to-end agent-loop
scenarios, and FastAPI route tests) against hand-rolled fakes for the
Anthropic client — no test makes a real network call or sleeps for real
seconds. Coverage is reported automatically (configured in `pytest.ini`) and
sits around 98%, comfortably above the ~90% target.

An optional, opt-in test against the *real* Claude API (verifying live
fraud-refusal behavior) is marked `@pytest.mark.live` and is skipped by
default. To run it (requires a real `ANTHROPIC_API_KEY`):

```bash
pytest -m live -o addopts=""
```

## Project structure

```
task3/
  app/
    config.py            # Environment/config loading, fail-fast API key check
    models.py             # Pydantic schemas + exception hierarchy
    anthropic_client.py   # Anthropic SDK wrapper (retry/timeout integrated)
    retry.py              # Hand-rolled exponential backoff (1s/2s/4s, max 3)
    json_utils.py         # Tolerant JSON extraction from model output
    redaction.py          # OTP/PIN/BVN/password/account-number scrubbing
    prompts.py            # System prompts + prompt composition
    tools.py               # fraud_red_flag_check tool + schema
    subagent.py            # Fraud-analysis subagent (claude-sonnet-4-5)
    conversation.py        # Multi-turn state, summarization, redaction
    escalation.py           # Simulated escalation ticket store
    agent_loop.py           # The 6-step agent loop
    dependencies.py         # FastAPI DI providers
    main.py                 # FastAPI app, routes, startup
  templates/                # Jinja2 templates (home, chat)
  static/                    # CSS + vanilla JS frontend
  tests/                      # pytest suite (see below)
  requirements.txt
  .env.example
  pytest.ini
```

### Test files

| File | Covers |
|---|---|
| `test_json_utils.py` | Tolerant JSON extraction (raw / fenced / brace fallback) |
| `test_redaction.py` | OTP/PIN/BVN/password/account-number scrubbing |
| `test_retry.py` | Backoff schedule, retry/non-retry classification |
| `test_anthropic_client.py` | SDK exception translation, response parsing |
| `test_models_fraud_assessment.py` | Pydantic validation rules |
| `test_tools_fraud_red_flag_check.py` | Red-flag heuristics per scam type |
| `test_subagent.py` | Subagent trigger conditions |
| `test_conversation_manager.py` | History, summarization, session isolation |
| `test_agent_loop.py` | All 3 loop stop conditions, subagent isolation |
| `test_escalation.py` | Simulated ticket creation and persistence |
| `test_scenarios.py` | The 7 required rubric scenarios end-to-end |
| `test_routes.py` | FastAPI endpoints, error-to-HTTP-status mapping |
| `test_startup_config.py` | Missing API key fail-fast behavior |

## Limitations

- The fraud red-flag tool is a deterministic regex/keyword heuristic, not a
  machine-learned classifier — it can miss novel scam wording or flag
  unusual-but-legitimate messages.
- Escalation is fully simulated (a local JSONL file); there is no real
  connection to a bank's fraud desk.
- Conversation state is in-memory per process; it does not persist across
  server restarts.
- The scenario tests script plausible Claude responses to verify the
  harness; they cannot guarantee what the *live* model will say (see the
  optional `@pytest.mark.live` test).
- Bare 10/11-digit numbers are redacted unconditionally, which can
  occasionally redact an unrelated long number (favoring safety over
  precision).

## Future enhancements

- Persist conversation and escalation state to a real database.
- Replace the regex-based tool with a fine-tuned or embeddings-based
  classifier for red-flag detection.
- Add user accounts and multi-device session continuity.
- Wire real escalation into a bank's actual fraud-reporting workflow.
- Add streaming responses in the chat UI.
