"""Transparent document cues, not a substitute for semantic investigation."""

import re

from veritern.identity import domain
from veritern.schemas import Case, Dimension, EvidenceSpan, Finding


def review_local_documents(case: Case) -> list[Finding]:
    findings = []
    for source in case.sources:
        if source.kind != "private" or source.ocr_review_required or not source.scope_confirmed:
            continue
        for n, line in enumerate(source.text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            candidates = []
            negated = re.search(r"\b(?:no|never|not|without|don't|do not)\b", line, re.I)
            if (
                not negated
                and re.search(r"\b(?:pay|payment|fee|deposit|charge|purchase)\b", line, re.I)
                and re.search(r"₹|\b(?:INR|USD|Rs\.?|rupees)\b|\$", line, re.I)
            ):
                candidates.append(
                    (
                        "LOCAL_FEE",
                        Dimension.FINANCIAL,
                        "Payment wording to review",
                        "A local text pattern found payment wording and a currency. It does not determine whether the charge is mandatory, hidden or improper.",
                        "Check the amount, whether payment is optional, and when the terms were disclosed.",
                    )
                )
            if not negated and re.search(
                r"\b(?:send|share|provide|enter)\b.*\b(?:password|OTP|one.time password)\b",
                line,
                re.I,
            ):
                candidates.append(
                    (
                        "LOCAL_SECRET",
                        Dimension.FINANCIAL,
                        "Sensitive-data wording to verify",
                        "A local pattern found a request involving a password or OTP. Sender identity and intent are unverified.",
                        "Do not disclose credentials; verify the request through an independently obtained contact.",
                    )
                )
            sender = re.search(
                r"(?:From|Reply-To) domain \(unauthenticated\): ([a-z0-9.-]+)", line, re.I
            )
            if sender and case.entity.domain and domain(sender.group(1)) != case.entity.domain:
                candidates.append(
                    (
                        "LOCAL_SENDER",
                        Dimension.IDENTITY,
                        "Sender domain differs from selected website",
                        "A different sender domain can belong to an authorized agency. This comparison does not authenticate email headers or establish impersonation.",
                        "Confirm this specific sender's recruiting authority with the employer.",
                    )
                )
            for rule, dimension, title, explanation, remedy in candidates:
                existing = next(
                    (s for s in case.spans if s.source_id == source.id and s.quote == line), None
                )
                span = existing or EvidenceSpan(
                    source_id=source.id, quote=line, locator=f"line {n}"
                )
                if existing is None:
                    case.spans.append(span)
                findings.append(
                    Finding(
                        rule_id=rule,
                        dimension=dimension,
                        severity="clarification_needed",
                        title=title,
                        explanation=explanation,
                        span_ids=[span.id],
                        scope=case.program.title,
                        remediation=remedy,
                    )
                )
    return findings
