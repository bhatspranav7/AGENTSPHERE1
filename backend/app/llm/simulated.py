"""Deterministic stand-in for an LLM.

Used when no LLM is configured so the whole platform (planning, DAG execution,
supervision, retries) can be demonstrated for free. Output is generated from
domain templates keyed on the objective, not from a model, and every run is
labelled `llm_mode: simulated` in the API and UI.
"""
import hashlib
import random
import re
import time
from dataclasses import dataclass

from ..core.config import settings
from . import LLMResponse


@dataclass(frozen=True)
class Domain:
    key: str
    label: str
    entity: str
    fields: tuple[tuple[str, str], ...]
    statuses: tuple[str, ...]
    systems: tuple[str, ...]
    stakeholders: str
    compliance: str
    kpi: str
    risks: tuple[str, ...]


DOMAINS = [
    Domain(
        "healthcare", "Healthcare operations", "EmergencyCase",
        (("patient_name", "str"), ("severity", "int"), ("location", "str"), ("assigned_unit", "str | None")),
        ("reported", "triaged", "dispatched", "admitted", "closed"),
        ("EHR (FHIR R4 API)", "Ambulance dispatch CAD", "Bed management system", "SMS / paging gateway"),
        "ER doctors, triage nurses and dispatch operators",
        "HIPAA-grade handling of patient identifiers and a full audit trail",
        "door-to-triage time",
        ("Patient data exposure through verbose logs", "Dispatch delays when the CAD API is rate limited",
         "Duplicate cases from repeated emergency calls"),
    ),
    Domain(
        "finance", "Finance operations", "Invoice",
        (("vendor", "str"), ("amount", "float"), ("currency", "str"), ("due_date", "date")),
        ("received", "validated", "approved", "paid", "rejected"),
        ("ERP ledger", "Payment gateway", "Approval workflow (Slack)", "Document OCR service"),
        "AP clerks, finance controllers and vendors",
        "SOX-style segregation of duties and immutable approval logs",
        "invoice cycle time",
        ("Duplicate payments from re-submitted invoices", "Currency rounding errors",
         "Approvals bypassed during month-end rush"),
    ),
    Domain(
        "hr", "People operations", "OnboardingTask",
        (("employee_email", "str"), ("department", "str"), ("start_date", "date"), ("owner", "str")),
        ("pending", "in_progress", "blocked", "done"),
        ("HRIS (Workday)", "Identity provider (Okta)", "IT asset tracker", "Slack"),
        "new hires, hiring managers and IT admins",
        "least-privilege access provisioning and PII minimisation",
        "time to productive first day",
        ("Accounts provisioned before contracts are signed", "Orphaned access after role changes",
         "Hardware not shipped before start date"),
    ),
    Domain(
        "itops", "IT operations", "Incident",
        (("service", "str"), ("severity", "str"), ("summary", "str"), ("on_call", "str | None")),
        ("detected", "acknowledged", "mitigating", "resolved", "postmortem"),
        ("Prometheus / Alertmanager", "PagerDuty", "Kubernetes API", "Status page"),
        "SREs, on-call engineers and customer support",
        "change management with every automated action logged and reversible",
        "mean time to recovery (MTTR)",
        ("Alert storms paging the wrong team", "Automated rollback of a healthy deploy",
         "Status page lagging the real incident state"),
    ),
    Domain(
        "commerce", "E-commerce operations", "Order",
        (("customer_id", "str"), ("items", "list[str]"), ("total", "float"), ("shipping_address", "str")),
        ("placed", "paid", "packed", "shipped", "delivered", "refunded"),
        ("Order management system", "Inventory service", "Payment provider (Stripe)", "Shipping carrier API"),
        "customers, warehouse staff and support agents",
        "PCI-DSS scope reduction by never storing card data",
        "order-to-ship time",
        ("Overselling when inventory sync lags", "Refunds issued twice from retried webhooks",
         "Carrier API outages stalling fulfilment"),
    ),
]

GENERIC = Domain(
    "generic", "Business operations", "WorkItem",
    (("title", "str"), ("priority", "int"), ("owner", "str"), ("due_date", "date | None")),
    ("new", "in_progress", "review", "done"),
    ("Internal REST API", "PostgreSQL", "Notification service", "Scheduler"),
    "operations staff and team leads",
    "role-based access and an auditable change history",
    "throughput per week",
    ("Unclear ownership of edge cases", "Silent failures in scheduled jobs", "Scope creep beyond the MVP"),
)

KEYWORDS = {
    "healthcare": r"hospital|patient|ambulance|emergency|clinic|triage|medical|doctor|nurse|health",
    "finance": r"invoice|payment|expense|account|finance|loan|billing|payroll|tax|ledger|refund polic",
    "hr": r"onboard|employee|hiring|recruit|hr\b|leave|offboard|candidate|interview",
    "itops": r"incident|deploy|server|outage|devops|monitor|alert|kubernetes|ci/cd|pipeline|sre|ticket",
    "commerce": r"order|inventory|e-?commerce|shop|cart|shipping|customer|product|retail|refund",
}


def detect_domain(objective: str) -> Domain:
    text = objective.lower()
    scores = {k: len(re.findall(p, text)) for k, p in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return GENERIC
    return next(d for d in DOMAINS if d.key == best)


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _an(word: str) -> str:
    return ("an " if word[:1].lower() in "aeiou" else "a ") + word


def _topic(objective: str) -> str:
    t = re.sub(r"\s+", " ", objective.strip().rstrip("."))
    return t[0].upper() + t[1:] if t else "the workflow"


class SimulatedLLM:
    mode = "simulated"
    model = "agentsphere-sim-1"

    def complete_json(self, task, system, user, sim) -> LLMResponse:
        objective = sim.get("objective", "")
        seed = int(hashlib.sha256(f"{task}:{objective}:{sim.get('step_id')}:{sim.get('attempt')}".encode()).hexdigest(), 16)
        rng = random.Random(seed)

        # Pretend to think so the live UI has something to animate
        started = time.perf_counter()
        time.sleep(rng.uniform(0.6, 1.6) * settings.SIMULATED_LATENCY)

        domain = detect_domain(objective)
        builder = getattr(self, f"_{task}")
        data = builder(sim, domain, rng)

        text = str(data)
        return LLMResponse(
            data=data,
            tokens=len(system + user + text) // 4,
            latency_ms=int((time.perf_counter() - started) * 1000),
            model=self.model,
        )

    # -------------------------------------------------
    # PLANNER
    # -------------------------------------------------
    def _plan(self, sim, d: Domain, rng):
        topic = _topic(sim["objective"])
        steps = [
            {"step_id": 1, "agent": "research", "title": "Map requirements",
             "objective": f"Identify the actors, inputs and success criteria for: {topic}. Focus on {d.stakeholders}.",
             "depends_on": [], "expected_output": "Requirements, constraints and success metrics"},
            {"step_id": 2, "agent": "research", "title": "Assess risk & compliance",
             "objective": f"Review failure modes and compliance needs ({d.compliance}) for {topic.lower()}.",
             "depends_on": [], "expected_output": "Ranked risks with mitigations"},
            {"step_id": 3, "agent": "code", "title": f"Build {d.entity} service",
             "objective": f"Implement a typed {d.entity} API with lifecycle states {', '.join(d.statuses)} and validation.",
             "depends_on": [1, 2], "expected_output": "Service code and tests"},
            {"step_id": 4, "agent": "automation", "title": "Wire up integrations",
             "objective": f"Connect the service to {d.systems[0]} and {d.systems[1]} and run the end-to-end flow.",
             "depends_on": [3], "expected_output": "Executed integration actions with results"},
            {"step_id": 5, "agent": "automation", "title": "Monitoring & alerts",
             "objective": f"Set up dashboards and alerting on {d.kpi} and failed transitions.",
             "depends_on": [3], "expected_output": "Alert rules and dashboard provisioned"},
        ]
        return {"summary": f"{d.label} plan: research in parallel, build the {d.entity} service, then integrate and monitor it.",
                "steps": steps}

    # -------------------------------------------------
    # RESEARCH
    # -------------------------------------------------
    def _research(self, sim, d: Domain, rng):
        topic = _topic(sim["objective"])
        step = sim["step"]
        if "risk" in step["title"].lower() or "compliance" in step["objective"].lower():
            findings = [
                f"Compliance baseline: {d.compliance}.",
                f"Every state change of {_an(d.entity)} must be attributable to a user or agent.",
                f"Integrations with {d.systems[0]} need idempotent retries; duplicate events are the norm, not the exception.",
            ]
            risks = list(d.risks)
            recs = [f"Mask sensitive fields at the logging layer.",
                    f"Use idempotency keys on every call to {d.systems[1]}.",
                    "Require supervisor approval before irreversible actions."]
            summary = f"Risk review for {topic.lower()}: {len(risks)} material risks found, all mitigable with idempotency, masking and approval gates."
        else:
            findings = [
                f"Primary users are {d.stakeholders}.",
                f"The core record is {_an(d.entity)} moving through {' → '.join(d.statuses)}.",
                f"Upstream/downstream systems: {', '.join(d.systems)}.",
                f"The success metric that matters most is {d.kpi}.",
            ]
            risks = [d.risks[rng.randrange(len(d.risks))]]
            recs = [f"Model the {d.entity} lifecycle as an explicit state machine.",
                    f"Expose a small REST API first; integrate {d.systems[0]} second."]
            summary = f"Requirements for {topic.lower()}: {_an(d.entity)} workflow serving {d.stakeholders}, measured by {d.kpi}."
        return {"summary": summary, "findings": findings, "risks": risks, "recommendations": recs}

    # -------------------------------------------------
    # CODE
    # -------------------------------------------------
    def _code(self, sim, d: Domain, rng):
        entity = d.entity
        table = _snake(entity) + "s"
        status_enum = "\n".join(f'    {s.upper()} = "{s}"' for s in d.statuses)
        fields = "\n".join(f"    {n}: {t}" for n, t in d.fields)
        transitions = ",\n".join(
            f'    Status.{a.upper()}: {{Status.{b.upper()}}}' for a, b in zip(d.statuses, d.statuses[1:])
        )
        service = f'''"""{entity} service generated by AgentSphere CodeAgent."""
from datetime import date, datetime
from enum import Enum
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="{entity} service")


class Status(str, Enum):
{status_enum}


# Allowed lifecycle transitions; anything else is rejected
TRANSITIONS = {{
{transitions},
}}


class {entity}In(BaseModel):
{fields}


class {entity}({entity}In):
    id: UUID
    status: Status = Status.{d.statuses[0].upper()}
    updated_at: datetime


DB: dict[UUID, {entity}] = {{}}


@app.post("/{table}", response_model={entity}, status_code=201)
def create(payload: {entity}In) -> {entity}:
    item = {entity}(id=uuid4(), updated_at=datetime.utcnow(), **payload.model_dump())
    DB[item.id] = item
    return item


@app.post("/{table}/{{item_id}}/advance", response_model={entity})
def advance(item_id: UUID, to: Status) -> {entity}:
    item = DB.get(item_id)
    if item is None:
        raise HTTPException(404, "{entity} not found")
    if to not in TRANSITIONS.get(item.status, set()):
        raise HTTPException(409, f"Cannot move from {{item.status}} to {{to}}")
    item.status, item.updated_at = to, datetime.utcnow()
    return item
'''
        first, second = d.statuses[0], d.statuses[1]
        sample = ", ".join(
            f'"{n}": {"3" if t == "int" else "12.5" if t == "float" else "[]" if t.startswith("list") else "None" if "None" in t else chr(34) + "2026-01-01" + chr(34) if t.startswith("date") else chr(34) + "demo" + chr(34)}'
            for n, t in d.fields
        )
        tests = f'''from fastapi.testclient import TestClient

from service import app

client = TestClient(app)


def test_lifecycle_happy_path():
    created = client.post("/{table}", json={{{sample}}}).json()
    assert created["status"] == "{first}"

    moved = client.post(f"/{table}/{{created['id']}}/advance", params={{"to": "{second}"}})
    assert moved.status_code == 200
    assert moved.json()["status"] == "{second}"


def test_illegal_transition_is_rejected():
    created = client.post("/{table}", json={{{sample}}}).json()
    resp = client.post(f"/{table}/{{created['id']}}/advance", params={{"to": "{d.statuses[-1]}"}})
    assert resp.status_code == 409
'''
        return {
            "summary": f"FastAPI {entity} service with an explicit state machine ({len(d.statuses)} states) and tests for legal and illegal transitions.",
            "language": "python",
            "files": [{"path": "service.py", "content": service}, {"path": "test_service.py", "content": tests}],
            "how_to_run": "pip install fastapi uvicorn pytest httpx && pytest -q && uvicorn service:app --reload",
        }

    # -------------------------------------------------
    # AUTOMATION
    # -------------------------------------------------
    def _automation(self, sim, d: Domain, rng):
        step = sim["step"]
        if "monitor" in step["title"].lower() or "alert" in step["objective"].lower():
            actions = [
                {"name": f"Provision {d.kpi} dashboard", "system": "Grafana", "status": "success",
                 "detail": f"Panels for {d.kpi}, throughput and error rate per {d.entity} state."},
                {"name": "Create alert rule", "system": "Alertmanager", "status": "success",
                 "detail": f"Page on-call when {d.kpi} breaches p95 target for 10 minutes."},
                {"name": "Dead-letter queue alarm", "system": d.systems[-1], "status": "success",
                 "detail": "Alert when any integration message is retried more than 3 times."},
            ]
            outcome = f"Observability live: {d.kpi} is tracked and failed transitions page the owning team."
        else:
            n = rng.randint(180, 900)
            actions = [
                {"name": f"Register webhook with {d.systems[0]}", "system": d.systems[0], "status": "success",
                 "detail": f"Subscribed to {d.entity} events with signed payloads."},
                {"name": f"Sync reference data", "system": d.systems[1], "status": "success",
                 "detail": f"Imported {n} records, 0 conflicts."},
                {"name": "Dry-run end-to-end flow", "system": "AgentSphere sandbox", "status": "success",
                 "detail": f"{d.entity} moved {' → '.join(d.statuses[:3])} in {rng.randint(120, 480)} ms."},
                {"name": f"Notify {d.stakeholders.split(',')[0]}", "system": d.systems[-1], "status": "skipped",
                 "detail": "Held until supervisor approval of the whole run."},
            ]
            outcome = f"{d.entity} workflow connected to {d.systems[0]} and {d.systems[1]}; sandbox run passed."
        return {"summary": f"{step['title']}: executed {len(actions)} actions against {len({a['system'] for a in actions})} systems.",
                "actions": actions, "outcome": outcome}

    # -------------------------------------------------
    # SUPERVISOR (LLM judge)
    # -------------------------------------------------
    def _review(self, sim, d: Domain, rng):
        score = round(rng.uniform(0.82, 0.97), 2)
        return {"score": score, "approved": True,
                "reason": f"Output is specific to the {d.label.lower()} context and satisfies the step objective."}

    # -------------------------------------------------
    # REPORTER
    # -------------------------------------------------
    def _report(self, sim, d: Domain, rng):
        topic = _topic(sim["objective"])
        steps = sim.get("steps", [])
        return {
            "title": topic,
            "executive_summary": (
                f"AgentSphere planned and executed {len(steps)} steps for {topic.lower()}. "
                f"The {d.entity} service was designed around {d.compliance}, integrated with "
                f"{d.systems[0]} and {d.systems[1]}, and put under monitoring on {d.kpi}."
            ),
            "key_outcomes": [f"{s['title']}: {s['status']}" for s in steps],
            "next_steps": [f"Run the generated tests in CI and deploy the {d.entity} service to staging.",
                           f"Review the {len(d.risks)} risks with {d.stakeholders.split(',')[0]}.",
                           "Replace sandbox credentials with production secrets via the vault."],
        }
