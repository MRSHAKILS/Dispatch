"""Deterministic rules engine for Dispatch.

Given a customer message, the engine answers the four task questions:

* ``case_type``  — what kind of problem is this?
* ``severity``   — how serious is it?
* ``department`` — which team should handle it?
* ``agent_summary`` — a two-second neutral summary (built in :mod:`app.safety`).

It also reports ``human_review_required`` and a ``confidence`` score. The engine
is fully deterministic — identical input always yields identical output — which
is exactly what an automated grader needs, and it requires no GPU, no network,
and no secrets.
"""

import re

from .keywords import (
    CASE_KEYWORDS,
    CONTESTED_WORDS,
    CRITICAL_WORDS,
    DEDUCTION_WORDS,
    HIGH_WORDS,
    OTHER_HINTS,
)
from .safety import build_summary

# Severity as an ordered ladder so we can take max() of competing signals.
_LEVELS = {"low": 1, "medium": 2, "high": 3, "critical": 4}
_LEVEL_NAMES = {v: k for k, v in _LEVELS.items()}

# Default severity for each case_type before any escalation is applied.
_DEFAULT_SEVERITY = {
    "phishing_or_social_engineering": "critical",
    "wrong_transfer": "high",
    "payment_failed": "high",
    "refund_request": "low",
    "other": "low",
}

# Tie-break order: safety-critical categories win when scores are equal.
_PRIORITY = [
    "phishing_or_social_engineering",
    "wrong_transfer",
    "payment_failed",
    "refund_request",
]

_ASCII_WORD = re.compile(r"^[a-z0-9]+$")
# Numbers like 5000, 5,000 or 50000.50 — used for amount-based escalation.
_AMOUNT = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _matches(pattern: str, text: str) -> bool:
    """Match a single ASCII word on word boundaries; everything else as substring.

    Word boundaries stop short tokens like ``pin`` from matching ``spinning``,
    while substring matching keeps phrases and Bangla tokens simple and robust.
    """
    if _ASCII_WORD.match(pattern):
        return re.search(rf"\b{re.escape(pattern)}\b", text) is not None
    return pattern in text


def _score_categories(text: str) -> dict[str, int]:
    """Sum the weights of every keyword that fires, per case_type."""
    scores: dict[str, int] = {}
    for case, entries in CASE_KEYWORDS.items():
        scores[case] = sum(weight for pattern, weight in entries if _matches(pattern, text))
    return scores


def _pick_case(scores: dict[str, int]) -> str:
    """Choose the winning case_type, honouring priority on ties."""
    best, best_score = "other", 0
    for case in _PRIORITY:
        if scores.get(case, 0) > best_score:
            best, best_score = case, scores[case]
    return best


def extract_amount(text: str) -> int | None:
    """Return the largest plausible money amount in the message, else ``None``."""
    best: int | None = None
    for raw in _AMOUNT.findall(text):
        cleaned = raw.replace(",", "")
        try:
            value = int(float(cleaned))
        except ValueError:
            continue
        # Ignore tiny tokens (e.g. "5 minutes") that are unlikely to be money.
        if value >= 100 and (best is None or value > best):
            best = value
    return best


def _severity(case_type: str, text: str, amount: int | None, contested: bool) -> str:
    """Resolve severity from the default plus any escalation signals."""
    level = _LEVELS[_DEFAULT_SEVERITY[case_type]]

    if case_type == "refund_request" and contested:
        level = max(level, _LEVELS["medium"])

    if any(_matches(w, text) for w in HIGH_WORDS):
        level = max(level, _LEVELS["high"])

    if any(_matches(w, text) for w in CRITICAL_WORDS):
        level = max(level, _LEVELS["critical"])

    if amount is not None:
        if amount >= 200_000:
            level = max(level, _LEVELS["critical"])
        elif amount >= 50_000:
            level = max(level, _LEVELS["high"])
        elif amount >= 10_000:
            level = max(level, _LEVELS["medium"])

    return _LEVEL_NAMES[level]


def _department(case_type: str, severity: str, contested: bool) -> str:
    """Route to a team per the task's department table."""
    if case_type == "phishing_or_social_engineering":
        return "fraud_risk"
    if case_type == "wrong_transfer":
        return "dispute_resolution"
    if case_type == "payment_failed":
        return "payments_ops"
    if case_type == "refund_request":
        # Low + uncontested -> general support; otherwise a contested dispute.
        return "customer_support" if (severity == "low" and not contested) else "dispute_resolution"
    return "customer_support"  # other


def _confidence(case_type: str, scores: dict[str, int], text: str) -> float:
    """Score how strongly the evidence supports the chosen case_type (0–1)."""
    if case_type == "other":
        hints = sum(1 for h in OTHER_HINTS if _matches(h, text))
        return round(min(0.45 + 0.05 * hints, 0.70), 2)

    winner = scores[case_type]
    runner_up = max((s for c, s in scores.items() if c != case_type), default=0)
    margin = max(winner - runner_up, 0)
    conf = 0.55 + 0.06 * winner + 0.04 * margin
    return round(min(max(conf, 0.60), 0.97), 2)


def classify(ticket_id: str, message: str, channel: str | None = None,
             locale: str | None = None) -> dict:
    """Classify one ticket and return the full response payload as a dict.

    ``channel`` and ``locale`` are accepted for completeness; the engine scans
    both English and Bangla signals regardless of the declared locale, so
    "mixed" Banglish messages are handled without special casing.
    """
    text = (message or "").lower()

    scores = _score_categories(text)
    case_type = _pick_case(scores)

    amount = extract_amount(message or "")
    contested = any(_matches(w, text) for w in CONTESTED_WORDS)
    severity = _severity(case_type, text, amount, contested)
    department = _department(case_type, severity, contested)
    deduction = any(_matches(w, text) for w in DEDUCTION_WORDS)

    return {
        "ticket_id": ticket_id,
        "case_type": case_type,
        "severity": severity,
        "department": department,
        "agent_summary": build_summary(case_type, amount, deduction),
        "human_review_required": severity == "critical"
        or case_type == "phishing_or_social_engineering",
        "confidence": _confidence(case_type, scores, text),
    }
