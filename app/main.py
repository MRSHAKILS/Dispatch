"""Dispatch HTTP API.

Endpoints
---------
GET  /health       Liveness probe (used by the grader and by Render).
POST /sort-ticket  Classify one CRM ticket.
GET  /             Triage Console — a zero-dependency visual dashboard.
GET  /docs         Interactive OpenAPI (Swagger) UI, provided by FastAPI.
"""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from . import __version__
from .classifier import classify
from .schemas import HealthResponse, TicketRequest, TicketResponse

app = FastAPI(
    title="Dispatch",
    description=(
        "Support-ticket triage for digital finance. Reads one customer message "
        "and returns its case type, severity, owning department, a neutral "
        "agent summary, and a human-review flag — all from a transparent, "
        "deterministic rules engine (no GPU, no secrets, no LLM required)."
    ),
    version=__version__,
)

# A public triage API: allow cross-origin calls so the dashboard and graders can
# reach it from anywhere.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

_INDEX_HTML = (Path(__file__).resolve().parent.parent / "static" / "index.html").read_text(
    encoding="utf-8"
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Return a simple service health response (well under the 10s budget)."""
    return HealthResponse(
        version=__version__,
        time=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/sort-ticket", response_model=TicketResponse, tags=["triage"])
def sort_ticket(ticket: TicketRequest) -> TicketResponse:
    """Accept one CRM ticket and return a structured classification."""
    result = classify(
        ticket_id=ticket.ticket_id,
        message=ticket.message,
        channel=ticket.channel,
        locale=ticket.locale,
    )
    return TicketResponse(**result)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> str:
    """Serve the Triage Console dashboard."""
    return _INDEX_HTML
