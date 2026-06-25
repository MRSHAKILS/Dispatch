"""Pydantic request/response models and the canonical enums.

Using enums in the response model means the values are validated at the edge and
documented automatically in the interactive ``/docs`` (Swagger) UI.
"""

from enum import Enum

from pydantic import BaseModel, Field


class CaseType(str, Enum):
    wrong_transfer = "wrong_transfer"
    payment_failed = "payment_failed"
    refund_request = "refund_request"
    phishing_or_social_engineering = "phishing_or_social_engineering"
    other = "other"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Department(str, Enum):
    customer_support = "customer_support"
    dispute_resolution = "dispute_resolution"
    payments_ops = "payments_ops"
    fraud_risk = "fraud_risk"


class TicketRequest(BaseModel):
    ticket_id: str = Field(..., description="Echoed back unchanged in the response.")
    message: str = Field(..., description="Free-text customer complaint.")
    # channel/locale are kept as lenient optional strings on purpose: a triage
    # service should classify a ticket rather than reject it over a stray label.
    channel: str | None = Field(
        default=None,
        description="One of: app, sms, call_center, merchant_portal.",
    )
    locale: str | None = Field(default=None, description="One of: bn, en, mixed.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ticket_id": "T-001",
                    "channel": "app",
                    "locale": "en",
                    "message": "I sent 5000 taka to a wrong number this morning, "
                    "please help me get it back",
                }
            ]
        }
    }


class TicketResponse(BaseModel):
    ticket_id: str
    case_type: CaseType
    severity: Severity
    department: Department
    agent_summary: str
    human_review_required: bool
    confidence: float = Field(..., ge=0.0, le=1.0)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "dispatch"
    version: str
    time: str
