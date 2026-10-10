from datetime import date

from veritern.schemas import Case, Claim, Dimension, Finding
from veritern.schemas import FactKind as K


def compatible(a: Claim, b: Claim) -> bool:
    return (
        a.program == b.program
        and a.program != "Unspecified program"
        and a.batch is not None
        and a.batch == b.batch
    )


def assess(case: Case, today: date | None = None) -> list[Finding]:
    Case.model_validate(case.model_dump())
    today = today or date.today()
    spans = {span.id: span for span in case.spans}
    sources = {source.id: source for source in case.sources}
    claims = [
        claim
        for claim in case.claims
        if all(
            sources[spans[i].source_id].scope_confirmed
            and sources[spans[i].source_id].access == "retrieved"
            and sources[spans[i].source_id].kind != "snippet"
            and not sources[spans[i].source_id].ocr_review_required
            for i in claim.span_ids
        )
    ]
    findings = []

    def add(rule, dimension, severity, title, explanation, supporting, remedy, opposing=()):
        # One account always stays limited. Quoted primary terms can support a mismatch,
        # but are not authenticated by this application.
        findings.append(
            Finding(
                rule_id=rule,
                dimension=dimension,
                severity=severity,
                title=title,
                explanation=explanation,
                span_ids=list(dict.fromkeys(i for c in supporting for i in c.span_ids)),
                opposing_span_ids=[i for c in opposing for i in c.span_ids],
                scope=f"{supporting[0].program} / {supporting[0].batch or 'batch unknown'}",
                remediation=remedy,
            )
        )

    for claim in claims:
        if claim.kind == K.FEE:
            earlier = [
                c
                for c in claims
                if c.kind == K.NO_FEE
                and compatible(c, claim)
                and c.benefit == claim.benefit
                and c.benefit is not None
                and c.event_date
                and claim.event_date
                and c.event_date < claim.event_date
            ]
            if earlier and claim.mandatory is True:
                add(
                    "FEE01",
                    Dimension.FINANCIAL,
                    "material_concern",
                    "Free promise conflicts with a later required charge",
                    "The cited earlier promise and later demand describe different terms. The submitted materials are not independently authenticated.",
                    [earlier[0], claim],
                    "Ask for the original terms, written explanation and an option to complete without the charge.",
                )
            elif claim.mandatory is False and claim.disclosed_before_joining is True:
                add(
                    "FEE03",
                    Dimension.FINANCIAL,
                    "informational",
                    "Optional charge disclosed before joining",
                    "An optional purchase alone does not establish deception.",
                    [claim],
                    "Confirm that declining it does not affect completion or payment.",
                )
            else:
                add(
                    "FEE02",
                    Dimension.FINANCIAL,
                    "clarification_needed",
                    "Charge needs disclosure clarification",
                    "A charge is described; original promises, timing, mandatory status or compatible batch evidence are incomplete.",
                    [claim],
                    "Request the joining terms and what payment unlocks.",
                )
        elif claim.kind == K.CONDITIONAL:
            promises = [
                c
                for c in claims
                if c.kind == K.GUARANTEE
                and compatible(c, claim)
                and c.event_date
                and claim.event_date
                and c.event_date < claim.event_date
                and claim.disclosed_before_joining is False
            ]
            add(
                "PAY01" if promises else "PAY00",
                Dimension.FINANCIAL,
                "material_concern" if promises else "informational",
                "Compensation promise conflicts with later conditions"
                if promises
                else "Compensation is conditional",
                "Maximum or conditional amounts are not guaranteed earnings. Review the quoted conditions.",
                [*promises[:1], claim],
                "Get guaranteed amount, targets and payment schedule in writing.",
            )
        elif claim.kind == K.UNPAID:
            resolutions = [c for c in claims if c.kind == K.RESOLUTION and compatible(c, claim)]
            overdue = claim.due_date is not None and claim.due_date < today
            add(
                "PAY02" if overdue else "PAY03",
                Dimension.FINANCIAL,
                "clarification_needed",
                "Payment reported overdue" if overdue else "Payment timing unresolved",
                "Participant-reported nonreceipt; not independently established. "
                + (
                    "A later reported resolution is also included."
                    if resolutions
                    else "No authenticated payment record is available."
                ),
                [claim],
                "Confirm due date, grace period and current payment status.",
                resolutions,
            )
        elif claim.kind in (K.MENTOR_DENIAL, K.SIMULATION):
            promise_kind = K.MENTOR_PROMISE if claim.kind == K.MENTOR_DENIAL else K.CLIENT_PROMISE
            promises = [c for c in claims if c.kind == promise_kind and compatible(c, claim)]
            support = [c for c in claims if c.kind == K.MENTOR_SUPPORT and compatible(c, claim)]
            if promises:
                add(
                    "EXP02",
                    Dimension.EXPERIENCE,
                    "clarification_needed",
                    "Reported experience differs from advertised support",
                    "A scoped account describes a possible mismatch; a single report does not establish program-wide delivery. Contrary evidence remains visible.",
                    [promises[0], claim],
                    "Ask for mentor access, review frequency and examples of actual work.",
                    support,
                )
        elif claim.kind == K.TASKS:
            add(
                "EXP01",
                Dimension.EXPERIENCE,
                "informational",
                "Standardized projects described",
                "Repeated educational projects alone do not establish low quality or deception. Supervision must be assessed separately.",
                [claim],
                "Ask how submissions are reviewed and what feedback is provided.",
            )
        elif claim.kind == K.PARTNER:
            confirmations = [
                c
                for c in claims
                if c.kind == K.PARTNER_CONFIRM
                and compatible(c, claim)
                and c.attribution == "authoritative"
            ]
            mismatch = [
                c
                for c in confirmations
                if c.benefit != claim.benefit and c.benefit and claim.benefit
            ]
            add(
                "PART02" if mismatch else "PART01",
                Dimension.MARKETING,
                "clarification_needed",
                "Partnership scope needs clarification"
                if mismatch
                else "Partnership benefit unverified",
                "A logo or technology relationship does not establish recruitment authority or placement guarantees. Missing directory entries are not a denial.",
                [claim, *mismatch[:1]],
                "Request confirmation from the named partner covering this program and benefit.",
            )
        elif claim.kind in (K.REFERRAL, K.PROMOTION):
            hidden = claim.disclosed_before_joining is False and claim.mandatory is True
            add(
                "REF01" if claim.kind == K.REFERRAL else "PROMO01",
                Dimension.FINANCIAL if claim.kind == K.REFERRAL else Dimension.MARKETING,
                "material_concern" if hidden else "clarification_needed",
                "Completion or payment has an additional condition",
                "The quoted referral/promotion condition should be compared with joining terms. Promotional requirements do not prove all reviews are fabricated.",
                [claim],
                "Clarify whether the condition is optional and when it was disclosed.",
            )
        elif claim.kind == K.SENSITIVE:
            add(
                "PRIV01",
                Dimension.FINANCIAL,
                "material_concern",
                "Sensitive action requested",
                "The source requests a sensitive action. The app does not perform the request or authenticate the sender.",
                [claim],
                "Do not share passwords or OTPs; verify the request through an independently obtained contact.",
            )
        elif claim.kind == K.AUTHORITY:
            add(
                "ID01",
                Dimension.IDENTITY,
                "clarification_needed",
                "Recruiting authority needs clarification",
                "Agency domains and brand/legal names may legitimately differ; this is not automatic impersonation.",
                [claim],
                "Verify the specific recruiter's authority with the employer.",
            )
        elif claim.kind == K.DENIAL and claim.attribution == "authoritative":
            add(
                "ID02",
                Dimension.IDENTITY,
                "material_concern",
                "Specific offer denied by authoritative source",
                "The denial applies only to the cited entity, offer and time.",
                [claim],
                "Verify the precise offer directly before proceeding.",
            )
        elif claim.kind in (K.PRESSURE, K.WORK, K.CHANGE):
            rule, title = {
                K.PRESSURE: ("PRESS01", "Pressure needs context"),
                K.WORK: ("WORK01", "Unpaid business work needs clarification"),
                K.CHANGE: ("CHANGE01", "Changed terms reported"),
            }[claim.kind]
            add(
                rule,
                Dimension.EXPERIENCE,
                "clarification_needed",
                title,
                "This contextual statement needs the original agreement and response. It does not establish illegality or deception.",
                [claim],
                "Ask for a written explanation and whether an amendment was mutually accepted.",
            )
    # Identical/reposted quotations produce one finding, not many corroborations.
    unique = {}
    for finding in findings:
        key = (
            finding.rule_id,
            finding.scope,
            tuple(sorted(spans[i].quote for i in finding.span_ids)),
        )
        unique.setdefault(key, finding)
    order = {"material_concern": 0, "clarification_needed": 1, "informational": 2}
    return sorted(unique.values(), key=lambda f: order[f.severity])
