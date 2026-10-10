"""Hand-authored fictional evidence. No network/model calls or real company labels."""

from datetime import date

from veritern.reporting.reports import assemble
from veritern.schemas import Case, Check, Claim, Entity, EvidenceSpan, Program, Source, Usage
from veritern.schemas import FactKind as K

DEMOS = {
    "late_fee": "Cedar Learning · a later ₹50 completion charge",
    "optional_fee": "Maple Studio · disclosed optional certificate",
    "missing_terms": "Willow Lab · charge, original terms missing",
    "mentorship": "Birch Academy · mentorship accounts disagree",
    "conditional_pay": "Fern Works · compensation has sales conditions",
    "training": "Acorn School · clearly disclosed project training",
}


def fact(case, kind, quote, *, title="Fictional evidence", attribution="advertised", **fields):
    source = Source(
        title=title,
        text=quote,
        kind="synthetic",
        publisher=case.entity.name,
        scope_confirmed=True,
        event_date=fields.get("event_date"),
    )
    span = EvidenceSpan(source_id=source.id, quote=quote, locator="paragraph 1")
    claim = Claim(
        kind=kind,
        span_ids=[span.id],
        program=case.program.title,
        batch="October 2026",
        attribution=attribution,
        **fields,
    )
    case.sources.append(source)
    case.spans.append(span)
    case.claims.append(claim)
    return claim


def new_demo(key="late_fee", owner="demo", stage="complete"):
    name = DEMOS[key].split(" · ")[0]
    case = Case(
        owner=owner,
        original_input=name,
        entity=Entity(name=name, domain=name.lower().replace(" ", "-") + ".test"),
        program=Program(title="Web Development Internship", batch="October 2026"),
        mode="demo",
    )
    if key == "late_fee":
        fact(
            case,
            K.NO_FEE,
            "October 2026 Web Development Internship: on 2026-10-01 we promise a free certificate. No certificate fee is required.",
            title="Joining advertisement",
            event_date=date(2026, 10, 1),
            benefit="certificate",
        )
        if stage in ("tasks", "complete"):
            fact(
                case,
                K.TASKS,
                "October 2026 tasks: build a calculator, a weather dashboard and a personal portfolio. Every participant receives the same task sheet.",
                title="Task sheet",
            )
        if stage == "complete":
            add_late_fee(case)
    elif key == "optional_fee":
        fact(
            case,
            K.FEE,
            "Before joining the October 2026 program, the terms disclose an optional INR 50 certificate purchase. Completion does not require payment.",
            amount_minor=5000,
            currency="INR",
            mandatory=False,
            disclosed_before_joining=True,
            benefit="certificate",
        )
    elif key == "missing_terms":
        fact(
            case,
            K.FEE,
            "October 2026: I was asked to pay INR 50 for completion after the tasks. I do not have my original joining terms.",
            attribution="participant_reported",
            amount_minor=5000,
            currency="INR",
            mandatory=True,
            benefit="completion",
        )
    elif key == "mentorship":
        fact(
            case,
            K.MENTOR_PROMISE,
            "October 2026 participants will receive weekly individual mentor review.",
        )
        fact(
            case,
            K.MENTOR_DENIAL,
            "I joined the October 2026 batch. My submitted work never received mentor review.",
            attribution="participant_reported",
        )
        fact(
            case,
            K.MENTOR_SUPPORT,
            "In the October 2026 batch my mentor reviewed my dashboard and requested two revisions.",
            attribution="participant_reported",
        )
    elif key == "conditional_pay":
        fact(
            case,
            K.CONDITIONAL,
            "October 2026 trainees may earn up to INR 15000, subject to ten accepted sales. This condition is disclosed before joining.",
            amount_minor=1500000,
            currency="INR",
            condition="subject to ten accepted sales",
            disclosed_before_joining=True,
            benefit="stipend",
        )
    else:
        fact(
            case,
            K.TRAINING,
            "October 2026 is unpaid structured training using simulated projects, with no employment or stipend promise.",
        )
        fact(
            case,
            K.TASKS,
            "The October 2026 curriculum uses standardized dashboard exercises for all students.",
        )
        fact(
            case,
            K.MENTOR_SUPPORT,
            "October 2026 learners receive weekly code review and revise their work after feedback.",
        )
    refresh_demo(case)
    return case


def add_late_fee(case):
    fact(
        case,
        K.FEE,
        "October 2026 completion message dated 2026-10-09: payment of INR 50 is mandatory to release your certificate. Upload a payment screenshot to the form.",
        title="Later completion message — fictional participant submission",
        attribution="participant_reported",
        event_date=date(2026, 10, 9),
        amount_minor=5000,
        currency="INR",
        mandatory=True,
        disclosed_before_joining=False,
        benefit="certificate",
    )


def refresh_demo(case):
    case.assessments.append(
        assemble(
            case,
            [
                Check(
                    name="Fictional evidence bundle",
                    state="resolved",
                    reason="Author-created example; no live research",
                ),
                Check(
                    name="Real-world coverage",
                    state="not_attempted",
                    reason="Demo mode disables all live calls",
                ),
            ],
            Usage(),
            ["Synthetic ground truth demonstrates rules, not model accuracy."],
            "none — synthetic fixtures",
        )
    )
