"""Unit tests for the Dispatch rules engine, including the 5 public sample cases."""

import pytest

from app.classifier import classify
from app.safety import build_summary, enforce_safety, is_safe

# (message, expected_case_type, expected_severity) — the five public sample cases.
PUBLIC_SAMPLES = [
    ("I sent 3000 to wrong number", "wrong_transfer", "high"),
    ("Payment failed but balance deducted", "payment_failed", "high"),
    ("Someone called asking for my OTP to verify my account", "phishing_or_social_engineering", "critical"),
    ("Please refund my last transaction, I changed my mind", "refund_request", "low"),
    ("App crashed when I opened it", "other", "low"),
]


@pytest.mark.parametrize("message, case_type, severity", PUBLIC_SAMPLES)
def test_public_samples(message, case_type, severity):
    r = classify("T-001", message)
    assert r["case_type"] == case_type
    assert r["severity"] == severity


def test_ticket_id_is_echoed():
    assert classify("T-XYZ", "anything")["ticket_id"] == "T-XYZ"


def test_phishing_forces_human_review():
    r = classify("T-1", "Someone called asking my OTP")
    assert r["human_review_required"] is True
    assert r["department"] == "fraud_risk"


def test_critical_forces_human_review():
    r = classify("T-1", "My account was hacked and money stolen")
    assert r["severity"] == "critical"
    assert r["human_review_required"] is True


def test_low_refund_routes_to_customer_support():
    r = classify("T-1", "Please refund, I changed my mind")
    assert r["department"] == "customer_support"
    assert r["human_review_required"] is False


def test_contested_refund_routes_to_dispute():
    r = classify("T-1", "I want a refund, the item was never received")
    assert r["department"] == "dispute_resolution"


def test_department_mapping():
    assert classify("T", "sent to wrong number")["department"] == "dispute_resolution"
    assert classify("T", "payment failed, balance deducted")["department"] == "payments_ops"
    assert classify("T", "app crashed")["department"] == "customer_support"


def test_large_amount_escalates_severity():
    r = classify("T-1", "Please refund my 80000 purchase")
    assert r["severity"] in {"high", "critical"}


def test_bangla_wrong_transfer():
    r = classify("T-1", "ভুল নাম্বারে ৫০০০ টাকা পাঠিয়েছি, ফেরত দরকার")
    assert r["case_type"] == "wrong_transfer"


def test_confidence_in_range():
    for message, *_ in PUBLIC_SAMPLES:
        c = classify("T", message)["confidence"]
        assert 0.0 <= c <= 1.0


def test_amount_appears_in_summary():
    r = classify("T-1", "I sent 5000 taka to a wrong number")
    assert "5,000" in r["agent_summary"]


# --- safety layer ---------------------------------------------------------- #

def test_generated_summaries_never_request_secrets():
    for ct in [
        "wrong_transfer",
        "payment_failed",
        "refund_request",
        "phishing_or_social_engineering",
        "other",
    ]:
        assert is_safe(build_summary(ct))


def test_enforce_safety_blocks_unsafe_text():
    unsafe = "Please share your OTP and PIN with the agent to verify."
    assert is_safe(unsafe) is False
    assert "OTP" not in enforce_safety(unsafe)
    assert "withheld" in enforce_safety(unsafe)


def test_phishing_summary_avoids_secret_tokens():
    summary = classify("T-1", "Someone called asking my OTP and PIN")["agent_summary"]
    lowered = summary.lower()
    for token in ["otp", "pin", "password", "card number"]:
        assert token not in lowered
