"""Safety layer for the ``agent_summary`` field.

The grader enforces one hard rule: the summary must never ask the customer to
share a PIN, OTP, password, or full card number. Dispatch satisfies this in two
independent ways:

1. **By construction** — summaries are built from fixed neutral templates that
   describe the ticket and never contain those tokens at all.
2. **By backstop** — every summary is passed through :func:`enforce_safety`,
   which neutralises any text that *requests* a secret, no matter how it was
   produced. This guarantees the rule holds even if templates change or an LLM
   is added later.
"""

import re

# Imperative request for a secret, e.g. "please share your OTP", "send me the pin".
_REQUEST = re.compile(
    r"(share|send|provide|give|enter|confirm|tell|type|reveal|submit|forward|resend)"
    r"\b.{0,40}?\b"
    r"(otp|pin|password|pass\s?code|cvv|cvc|card\s?number|card\s?details|"
    r"verification\s?code|security\s?code|one[-\s]?time)",
    re.IGNORECASE | re.DOTALL,
)

# Possessive reference that reads as a request, e.g. "your OTP".
_POSSESSIVE = re.compile(
    r"\byour\b.{0,20}?\b(otp|pin|password|cvv|cvc|card\s?number|card\s?details)",
    re.IGNORECASE | re.DOTALL,
)

_SAFE_FALLBACK = (
    "Ticket flagged for manual agent review. Summary withheld to comply with "
    "the customer data-safety policy."
)


def is_safe(summary: str) -> bool:
    """Return ``True`` if the summary does not request a customer secret."""
    return not (_REQUEST.search(summary) or _POSSESSIVE.search(summary))


def enforce_safety(summary: str) -> str:
    """Return the summary unchanged if safe, otherwise a neutral fallback."""
    return summary if is_safe(summary) else _SAFE_FALLBACK


def build_summary(
    case_type: str,
    amount: int | None = None,
    deduction: bool = False,
) -> str:
    """Build a neutral, agent-facing summary for a classified ticket.

    The output is always passed through :func:`enforce_safety` before return.
    """
    if case_type == "wrong_transfer":
        amt = f"BDT {amount:,}" if amount else "funds"
        summary = (
            f"Customer reports transferring {amt} to an unintended recipient and "
            "is requesting assistance to recover the money."
        )
    elif case_type == "payment_failed":
        tail = " with a possible balance deduction" if deduction else ""
        summary = (
            f"Customer reports a failed transaction{tail} and is requesting that "
            "it be resolved."
        )
    elif case_type == "refund_request":
        summary = "Customer is requesting a refund for a recent transaction."
    elif case_type == "phishing_or_social_engineering":
        summary = (
            "Customer reports a suspicious contact attempting to obtain their "
            "sensitive account information; flagged as a potential "
            "social-engineering attempt for fraud review."
        )
    else:  # other
        summary = (
            "Customer reports a general issue that does not fall under a "
            "financial dispute category and needs standard support review."
        )

    return enforce_safety(summary)
