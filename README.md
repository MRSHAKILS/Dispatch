# Dispatch

**Support-ticket triage for digital finance.** Dispatch reads one customer
message and instantly answers four questions about it — *what kind of problem is
this, how serious is it, which team should handle it,* and *what is a two-second
summary an agent can read* — then raises a flag whenever a human must step in.

> **Engine:** transparent, deterministic, rules-based · **No GPU · No secrets · No LLM required**

---

## Table of contents

- [Why rules-based](#why-rules-based)
- [Live demo](#live-demo)
- [API reference](#api-reference)
- [How classification works](#how-classification-works)
- [Safety guarantee](#safety-guarantee)
- [Run it locally](#run-it-locally)
- [Tests](#tests)
- [Deployment](#deployment)
- [Deployment replication runbook](#deployment-replication-runbook)
- [Project structure](#project-structure)
- [Submission details](#submission-details)

---

## Why rules-based

The grader checks **exact** enum outputs against known cases and a strict safety
rule. A deterministic rules engine is the right tool here:

| Concern | Rules engine (this project) | LLM |
| --- | --- | --- |
| Same input → same output | ✅ Guaranteed | ⚠️ Non-deterministic |
| Latency | ✅ Single-digit ms | ⚠️ Hundreds of ms–seconds |
| Cost | ✅ Free | ⚠️ Per-request billing |
| Secrets to leak | ✅ None | ⚠️ API key |
| Can produce an unsafe summary | ✅ Impossible by construction | ⚠️ Possible; needs guarding |

The architecture isolates the engine behind a clean interface, so an LLM could be
slotted in later without touching the API or the safety layer. For this task it
adds risk and latency for no benefit, so **Dispatch answers "LLM used: No."**

A real bonus of the rules approach: Dispatch handles **English, Bangla, and
mixed "Banglish"** messages out of the box (the keyword tables are bilingual and
the amount parser understands Bangla numerals like `৪০০০`).

## Live demo

- **Dashboard (Triage Console):** `https://<your-app>.onrender.com/`
- **Health:** `https://<your-app>.onrender.com/health`
- **Interactive API docs (Swagger):** `https://<your-app>.onrender.com/docs`

The dashboard is a zero-dependency single page served by the API itself: paste a
message, pick a channel/locale, and see the case type, a colour-coded severity
badge, the routed department, a confidence meter, the agent summary, and a
human-review alert banner — plus one-click sample cases (including a Bangla one).

## API reference

### `GET /health`

```json
{ "status": "ok", "service": "dispatch", "version": "1.0.0", "time": "2026-06-25T15:46:32Z" }
```

### `POST /sort-ticket`

Request:

```json
{
  "ticket_id": "T-001",
  "channel": "app",
  "locale": "en",
  "message": "I sent 5000 taka to a wrong number this morning, please help me get it back"
}
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `ticket_id` | string | yes | Echoed back unchanged |
| `message` | string | yes | Free-text complaint |
| `channel` | string | no | `app`, `sms`, `call_center`, `merchant_portal` |
| `locale` | string | no | `bn`, `en`, `mixed` |

Response:

```json
{
  "ticket_id": "T-001",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports transferring BDT 5,000 to an unintended recipient and is requesting assistance to recover the money.",
  "human_review_required": false,
  "confidence": 0.97
}
```

Try it from the command line:

```bash
curl -X POST https://<your-app>.onrender.com/sort-ticket \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-003","message":"Someone called asking for my OTP to verify my account"}'
```

## How classification works

**`case_type`** — keyword signals are scored per category; the highest score
wins. On ties, the safety-critical categories win first (phishing → wrong
transfer → payment failed → refund → other).

| `case_type` | Triggered by (examples) |
| --- | --- |
| `phishing_or_social_engineering` | OTP / PIN / password requests, "someone called", "claiming to be", scam, lottery, suspicious link |
| `wrong_transfer` | "wrong number", "wrong recipient", "sent by mistake", "ভুল নাম্বার" |
| `payment_failed` | "payment failed", "balance deducted", "debited but", "টাকা কেটে" |
| `refund_request` | "refund", "money back", "changed my mind", "রিফান্ড" |
| `other` | anything else (e.g. "app crashed") |

**`severity`** — each `case_type` has a default level, then escalates on signals:
words like *stolen / hacked / unauthorized* force `critical`; *urgent / salary*
force at least `high`; large amounts bump it up (≥10k → medium, ≥50k → high,
≥200k → critical).

**`department`** — routed per the task table:

| `department` | Handles |
| --- | --- |
| `customer_support` | `other`, and low-severity `refund_request` |
| `dispute_resolution` | `wrong_transfer`, contested `refund_request` |
| `payments_ops` | `payment_failed` |
| `fraud_risk` | `phishing_or_social_engineering` |

**`human_review_required`** — `true` for any `critical` severity or phishing case.

**`confidence`** — derived from how strongly the evidence supports the chosen
category and how far it beats the runner-up (0.0–1.0).

### The five public sample cases (all verified)

| # | Message | `case_type` | `severity` |
| --- | --- | --- | --- |
| 1 | I sent 3000 to wrong number | `wrong_transfer` | high |
| 2 | Payment failed but balance deducted | `payment_failed` | high |
| 3 | Someone called asking for my OTP to verify my account | `phishing_or_social_engineering` | critical |
| 4 | Please refund my last transaction, I changed my mind | `refund_request` | low |
| 5 | App crashed when I opened it | `other` | low |

## Safety guarantee

The `agent_summary` must **never** ask the customer to share a PIN, OTP,
password, or full card number. Dispatch enforces this twice over:

1. **By construction** — summaries come from fixed neutral templates that do not
   contain those tokens at all.
2. **By backstop** — every summary passes through `enforce_safety()`, which
   detects any text that *requests* a secret and replaces it with a neutral
   fallback.

See [`app/safety.py`](app/safety.py) and the safety tests in
[`tests/test_classifier.py`](tests/test_classifier.py).

## Run it locally

Requires **Python 3.12+**.

```bash
# 1. (optional) create a virtual environment
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

# 2. install
pip install -r requirements.txt

# 3. run
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open <http://localhost:8000/> for the dashboard, or hit the API directly at
`/health` and `/sort-ticket`. Interactive docs are at `/docs`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The suite covers all five public samples, the department routing table, severity
escalation, the Bangla path, confidence bounds, and the safety guarantee.

## Deployment

Primary target: **Render** (free tier, automatic HTTPS).

### Option A — Render Blueprint (recommended)

1. Push this repo to GitHub (public).
2. In Render: **New + → Blueprint** and select the repo.
   Render reads [`render.yaml`](render.yaml) and provisions everything:
   - build: `pip install -r requirements.txt`
   - start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - health check path: `/health`
3. Wait for the first deploy. Your base URL is `https://<service>.onrender.com`.

### Option B — Render manual web service

New + → **Web Service** → connect the repo → Runtime **Python 3**, then paste the
same build/start commands above and set the health check path to `/health`.

### Other platforms

Dispatch is a standard ASGI app, so any host that can run a Python web process
works. Use the same start command on Railway, Fly.io, Cloud Run, or EC2:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

No environment variables are required. `.env.example` documents the (currently
unused) slots reserved for an optional future LLM provider.

> **Free-tier note:** Render's free web services sleep after inactivity, so the
> first request can take ~30–50s to wake. `/health` responds well within the 10s
> budget once awake; keep the service warm before grading if needed.

## Deployment replication runbook

For a grader reproducing the service **locally** from a clean checkout (no live
URL needed):

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verify:

```bash
# health
curl http://localhost:8000/health

# classification (expect case_type=wrong_transfer, severity=high)
curl -X POST http://localhost:8000/sort-ticket \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-001","message":"I sent 3000 to wrong number"}'
```

## Project structure

```
app/
  main.py        FastAPI app and routes (/health, /sort-ticket, /, /docs)
  schemas.py     Pydantic models + canonical enums
  classifier.py  Deterministic rules engine
  safety.py      Agent-summary generation + secret-request guard
  keywords.py    Bilingual (EN + BN) signal tables
static/
  index.html     Triage Console dashboard (no build step, zero deps)
tests/
  test_classifier.py   Engine + safety + 5 public samples
  test_api.py          Endpoint contract tests
render.yaml · requirements*.txt · runtime.txt · .env.example
```

## Submission details

| Field | Value |
| --- | --- |
| Team name | _<your registered team name>_ |
| GitHub repository URL | _<your public repo URL>_ |
| Live API base URL | `https://<your-app>.onrender.com` |
| Deployment platform | Render |
| LLM used | **No** — deterministic rules engine |
| Known issues / blockers | Render free tier cold-starts after idle (first request may take ~30–50s) |

## License

MIT — see [`LICENSE`](LICENSE).
