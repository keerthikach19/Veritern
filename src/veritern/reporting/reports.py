import json
import re

from veritern.analysis.local import review_local_documents
from veritern.ingestion.redact import redact
from veritern.rules import assess
from veritern.schemas import Assessment, Case, Check, Usage

QUESTIONS = [
    "What were the written joining terms, including all completion and certificate charges?",
    "Which program and batch do these materials describe, and what mentor feedback was delivered?",
    "What guaranteed compensation, conditions and payment dates were agreed?",
]


def assemble(
    case: Case, checks: list[Check], usage: Usage, limitations: list[str], model="unavailable"
) -> Assessment:
    local_findings = review_local_documents(case)
    findings = assess(case) + local_findings
    if any(f.severity == "material_concern" for f in findings):
        headline = "Material concerns found in reviewed evidence"
    elif any(f.severity == "clarification_needed" for f in findings):
        headline = "Clarification needed before proceeding"
    else:
        headline = "Insufficient evidence to assess the opportunity"
    return Assessment(
        version=len(case.assessments) + 1,
        headline=headline,
        findings=findings,
        checks=checks,
        questions=QUESTIONS,
        usage=usage,
        model=model,
        status="partial",
        limitations=list(
            dict.fromkeys(
                [
                    "A bounded investigation, not comprehensive internet coverage or a safety guarantee.",
                    "User-selected website establishes scope, not independently verified authority.",
                    "Documents and participant accounts are not forensically authenticated.",
                    "English-only evaluation; other languages require manual review.",
                    *limitations,
                ]
            )
        ),
    )


def plain(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()<>#!|])", r"\\\1", redact(text))


def export_json(case: Case) -> str:
    report = case.assessments[-1]
    payload = {
        "application": "Veritern",
        "mode": case.mode,
        "scope": case.entity.domain,
        "program": case.program.model_dump(mode="json"),
        "assessment": report.model_dump(mode="json"),
        "sources": [s.model_dump(mode="json", exclude={"text", "consented"}) for s in case.sources],
        "evidence": [s.model_dump(mode="json") for s in case.spans],
    }

    def clean(value):
        if isinstance(value, str):
            return redact(value)
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [clean(v) for v in value]
        return value

    return json.dumps(clean(payload), ensure_ascii=False, indent=2)


def export_markdown(case: Case) -> str:
    report = case.assessments[-1]
    lines = [
        "# Veritern private report",
        f"Mode: **{case.mode.upper()}**",
        f"Scope: {plain(case.entity.domain)} — {plain(case.program.title)}",
        f"Assessment {report.version} · {report.created_at.isoformat()}",
        f"## {report.headline}",
    ]
    if case.mode == "demo":
        lines.append("**FICTIONAL DEMONSTRATION — no live investigation.**")
    spans = {s.id: s for s in case.spans}
    sources = {s.id: s for s in case.sources}
    for finding in report.findings:
        lines.extend(
            [
                f"### {finding.title}",
                f"{finding.severity} · {finding.strength} evidence · {finding.rule_id}",
                plain(finding.explanation),
            ]
        )
        for span_id in finding.span_ids + finding.opposing_span_ids:
            span = spans[span_id]
            source = sources[span.source_id]
            lines.extend(
                [
                    f"> {plain(span.quote)}",
                    f"Source: {plain(source.title)} · {source.kind} · {plain(span.locator)} · retrieved {source.retrieved_at.isoformat()}",
                ]
            )
            if source.url:
                from veritern.identity import normalize_url

                try:
                    url = normalize_url(source.url).replace("(", "%28").replace(")", "%29")
                    lines.append(f"[Open source]({url})")
                except ValueError:
                    pass
        lines.append(plain(finding.remediation))
    lines.append("## Coverage")
    lines.extend(f"- {plain(c.name)}: {c.state} — {plain(c.reason)}" for c in report.checks)
    lines.append("## Questions")
    lines.extend(f"- {plain(q)}" for q in report.questions)
    lines.append("## Limitations")
    lines.extend(f"- {plain(item)}" for item in report.limitations)
    lines.append(
        f"Rules {report.rule_version}; prompt {report.prompt_version}; model {report.model}. Calls {report.usage.calls}; input tokens {report.usage.input_tokens}; output tokens {report.usage.output_tokens}; unknown usage {report.usage.unknown_usage}."
    )
    return "\n\n".join(lines)
