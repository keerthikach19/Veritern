import hashlib
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def uid() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(UTC)


def normalized(text: str) -> str:
    return " ".join(text.split())


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Dimension(StrEnum):
    IDENTITY = "Identity & authority"
    EXPERIENCE = "Experience & learning"
    MARKETING = "Marketing & partnerships"
    FINANCIAL = "Fees & compensation"


class Access(StrEnum):
    RETRIEVED = "retrieved"
    NOT_FOUND = "not_found"
    BLOCKED = "blocked"
    ROBOTS = "robots_disallowed"
    LOGIN = "login_required"
    TIMEOUT = "timeout"
    PARSE = "parse_failed"
    UNSUPPORTED = "unsupported"
    NOT_ATTEMPTED = "not_attempted"


class Entity(Record):
    id: str = Field(default_factory=uid)
    name: str
    domain: str
    role: str = "unverified provider"
    match_state: str = "user_selected_scope"


class Program(Record):
    id: str = Field(default_factory=uid)
    title: str = "Unspecified program"
    batch: str | None = None
    country: str | None = None
    discipline: str | None = None


class Source(Record):
    id: str = Field(default_factory=uid)
    title: str
    url: str | None = None
    publisher: str = "unknown"
    text: str = ""
    kind: Literal["official", "third_party", "private", "snippet", "synthetic"]
    access: Access = Access.RETRIEVED
    retrieved_at: datetime = Field(default_factory=now)
    published_at: date | None = None
    event_date: date | None = None
    scope_confirmed: bool = False
    ocr_review_required: bool = False
    consented: bool = False
    cached: bool = False
    truncated: bool = False
    note: str = ""
    origin_group: str | None = None
    extraction_version: str = "text-v1"

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(normalized(self.text).encode()).hexdigest()


class EvidenceSpan(Record):
    id: str = Field(default_factory=uid)
    source_id: str
    quote: str
    locator: str
    verified: bool = True


class FactKind(StrEnum):
    NO_FEE = "no_fee_promise"
    FEE = "fee_request"
    GUARANTEE = "stipend_guarantee"
    CONDITIONAL = "conditional_stipend"
    UNPAID = "reported_unpaid"
    MENTOR_PROMISE = "mentorship_promise"
    MENTOR_DENIAL = "mentorship_denial"
    MENTOR_SUPPORT = "mentorship_received"
    CLIENT_PROMISE = "client_work_promise"
    SIMULATION = "simulation_report"
    TASKS = "standardized_tasks"
    PARTNER = "partnership_claim"
    PARTNER_CONFIRM = "partnership_confirmation"
    REFERRAL = "referral_condition"
    PROMOTION = "promotion_condition"
    SENSITIVE = "sensitive_request"
    AUTHORITY = "authority_mismatch"
    DENIAL = "authoritative_denial"
    PRESSURE = "pressure"
    WORK = "unpaid_business_test"
    RESOLUTION = "reported_resolution"
    CHANGE = "changed_terms"
    TRAINING = "disclosed_training"


class Claim(Record):
    id: str = Field(default_factory=uid)
    kind: FactKind
    span_ids: list[str]
    program: str
    batch: str | None = None
    event_date: date | None = None
    due_date: date | None = None
    amount_minor: int | None = Field(None, ge=0)
    currency: str | None = None
    mandatory: bool | None = None
    disclosed_before_joining: bool | None = None
    condition: str | None = None
    benefit: str | None = None
    attribution: Literal["advertised", "participant_reported", "authoritative", "user_statement"]
    verification: str = "unverified"


class Finding(Record):
    id: str = Field(default_factory=uid)
    rule_id: str
    dimension: Dimension
    severity: Literal["informational", "clarification_needed", "material_concern"]
    strength: Literal["limited", "moderate", "strong"] = "limited"
    title: str
    explanation: str
    span_ids: list[str]
    opposing_span_ids: list[str] = Field(default_factory=list)
    scope: str
    remediation: str


class Check(Record):
    name: str
    state: Literal["resolved", "unresolved", "blocked", "failed", "not_attempted"]
    reason: str
    source_ids: list[str] = Field(default_factory=list)


class Usage(Record):
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    unknown_usage: bool = False
    elapsed_seconds: float = 0
    reserved_input_tokens: int = 0
    reserved_output_tokens: int = 0


class Assessment(Record):
    id: str = Field(default_factory=uid)
    version: int
    created_at: datetime = Field(default_factory=now)
    status: Literal["complete", "partial", "cancelled"] = "partial"
    headline: str
    findings: list[Finding] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    checks: list[Check] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    limitations: list[str] = Field(default_factory=list)
    model: str = "unavailable"
    rule_version: str = "1.0"
    prompt_version: str = "extract-v1"


class Case(Record):
    id: str = Field(default_factory=uid)
    owner: str
    original_input: str
    entity: Entity
    program: Program = Field(default_factory=Program)
    mode: Literal["live", "manual", "demo"]
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
    revision: int = 0
    saved: bool = False
    extraction_fingerprint: str | None = None
    budget_usage: Usage = Field(default_factory=Usage)
    sources: list[Source] = Field(default_factory=list)
    spans: list[EvidenceSpan] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    assessments: list[Assessment] = Field(default_factory=list)

    @model_validator(mode="after")
    def provenance(self):
        sources = {s.id: s for s in self.sources}
        spans = {s.id: s for s in self.spans}
        for span in self.spans:
            if span.source_id not in sources or not normalized(span.quote):
                raise ValueError("Invalid evidence reference")
            if normalized(span.quote) not in normalized(sources[span.source_id].text):
                raise ValueError("Quotation is absent from source")
        for claim in self.claims:
            if not claim.span_ids or any(i not in spans for i in claim.span_ids):
                raise ValueError("Invalid claim evidence")
        for assessment in self.assessments:
            for finding in assessment.findings:
                if not finding.span_ids or any(
                    i not in spans for i in finding.span_ids + finding.opposing_span_ids
                ):
                    raise ValueError("Invalid finding evidence")
        return self
