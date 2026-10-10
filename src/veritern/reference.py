"""Reproducible reviews of supplied reference material, with explicit provenance."""

import json
import re
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import model_validator

from veritern.identity import domain, normalize_url
from veritern.schemas.models import Record


class ReferenceNote(Record):
    title: str
    category: Literal["clarification", "positive", "limitation"]
    quote: str
    explanation: str


class ReferenceCase(Record):
    id: str
    company: str
    domains: list[str]
    url: str
    supplied_on: date
    source_type: Literal["provided_reference_text"]
    reference_text: str
    identifying_phrases: list[str]
    fields: dict[str, str]
    notes: list[ReferenceNote]
    questions: list[str]

    @model_validator(mode="after")
    def validate_evidence(self):
        if len(self.identifying_phrases) < 2:
            raise ValueError("Reference needs multiple identifying phrases")
        for phrase in self.identifying_phrases:
            if phrase not in self.reference_text:
                raise ValueError("Reference phrase absent from provided text")
        for note in self.notes:
            if not note.quote or note.quote not in self.reference_text:
                raise ValueError("Reference observation lacks an exact source excerpt")
        if domain(normalize_url(self.url)) not in self.domains:
            raise ValueError("Reference URL not in domain scope")
        if len(self.questions) != 5:
            raise ValueError("Each reference requires five verification questions")
        return self


class ReferenceResult(Record):
    company: str
    classification: Literal["SUSPICIOUS — VERIFICATION REQUIRED", "UNKNOWN"]
    matched_phrases: list[str]
    reason: str
    verification_required: Literal[True] = True
    evidence_basis: Literal["Provided reference text; original document not supplied"] = (
        "Provided reference text; original document not supplied"
    )
    model_executed: Literal[False] = False
    ocr_executed: Literal[False] = False
    live_checks_executed: Literal[False] = False
    source_id: str


def load_references() -> dict[str, ReferenceCase]:
    path = Path(__file__).parent / "data" / "reference_cases.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    cases = [ReferenceCase.model_validate(row) for row in rows]
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Duplicate reference id")
    domains = [d for case in cases for d in case.domains]
    if len(set(domains)) != len(domains):
        raise ValueError("Ambiguous reference domains")
    return {case.id: case for case in cases}


def reference_for_url(url: str) -> ReferenceCase | None:
    target = domain(normalize_url(url))
    return next((case for case in load_references().values() if target in case.domains), None)


def matched_phrases(text: str, case: ReferenceCase) -> list[str]:
    result = []
    for phrase in case.identifying_phrases:
        match = re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.I)
        if match:
            result.append(match.group())
    return result


def identify_reference(text: str) -> tuple[str | None, list[str]]:
    """Matching identifies a text family, never authenticates or classifies an offer."""
    candidates = []
    for case in load_references().values():
        matches = matched_phrases(text, case)
        # Require a company-specific name/domain plus another distinctive phrase.
        anchors = [case.company, *case.domains]
        if len(matches) >= 2 and any(
            re.search(r"(?<![\w.-])" + re.escape(anchor) + r"(?![\w.-])", text, re.I)
            for anchor in anchors
        ):
            candidates.append((case.id, matches))
    return candidates[0] if len(candidates) == 1 else (None, [])


def review_reference(case: ReferenceCase) -> ReferenceResult:
    concerns = [note for note in case.notes if note.category == "clarification"]
    return ReferenceResult(
        company=case.company,
        classification="SUSPICIOUS — VERIFICATION REQUIRED" if concerns else "UNKNOWN",
        matched_phrases=matched_phrases(case.reference_text, case),
        reason=(
            "The supplied reference notes raise these issues: "
            + "; ".join(note.title.lower() for note in concerns[:2])
            + ". The original letter and issuer have not been authenticated; this is not a finding about every offer from this company."
            if concerns
            else "The supplied Wipro reference describes structured employment terms, but only part of the document is described. No original document or official authentication was provided."
        ),
        source_id=case.id,
    )


def export_reference(case: ReferenceCase) -> str:
    return json.dumps(
        {
            "application": "Veritern",
            "result": review_reference(case).model_dump(mode="json"),
            "reference": case.model_dump(mode="json"),
            "provenance": {
                "source": "User-supplied company patterns and case notes, 2026-10-10",
                "execution": "Local deterministic reference review",
                "configured_model": "openai/gpt-oss-20b",
                "model_run": "Not run; no recorded model output supplied",
                "ocr": "Not run; no image supplied",
                "web_search": "Not run for this reference report",
                "authentication": "Not performed",
            },
        },
        indent=2,
        ensure_ascii=False,
    )
