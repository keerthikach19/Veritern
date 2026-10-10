from datetime import date

import pytest

from veritern.demo import add_late_fee, fact, new_demo, refresh_demo
from veritern.rules import assess
from veritern.schemas import Access, Case
from veritern.schemas import FactKind as K


@pytest.mark.parametrize(
    "key,expected",
    [
        ("late_fee", {"FEE01", "EXP01"}),
        ("optional_fee", {"FEE03"}),
        ("missing_terms", {"FEE02"}),
        ("mentorship", {"EXP02"}),
        ("conditional_pay", {"PAY00"}),
        ("training", {"EXP01"}),
    ],
)
def test_fictional_rules(key, expected):
    assert {f.rule_id for f in assess(new_demo(key))} == expected


@pytest.mark.parametrize(
    "field,value",
    [
        ("batch", "May 2023"),
        ("program", "Other internship"),
        ("event_date", None),
        ("mandatory", None),
        ("benefit", "completion"),
    ],
)
def test_mismatch_requires_compatible_scope_and_chronology(field, value):
    case = new_demo()
    setattr(case.claims[-1], field, value)
    assert "FEE01" not in {f.rule_id for f in assess(case)}


@pytest.mark.parametrize(
    "field,value",
    [
        ("ocr_review_required", True),
        ("scope_confirmed", False),
        ("kind", "snippet"),
        ("access", "blocked"),
    ],
)
def test_ineligible_source_cannot_trigger_material_concern(field, value):
    case = new_demo()
    setattr(case.sources[-1], field, Access(value) if field == "access" else value)
    assert not any(f.severity == "material_concern" for f in assess(case))


def test_later_fee_creates_new_version_without_erasing_original():
    case = new_demo(stage="initial")
    assert not case.assessments[-1].findings
    add_late_fee(case)
    refresh_demo(case)
    assert len(case.assessments) == 2
    assert not case.assessments[0].findings
    assert case.assessments[1].findings[0].rule_id == "FEE01"
    Case.model_validate(case.model_dump())


def test_due_date_required_and_resolution_retained():
    case = new_demo("training")
    claim = fact(case, K.UNPAID, "I have not received payment.", attribution="participant_reported")
    assert "PAY02" not in {f.rule_id for f in assess(case)}
    claim.due_date = date(2026, 1, 1)
    fact(case, K.RESOLUTION, "The payment was later received.", attribution="participant_reported")
    finding = next(f for f in assess(case, date(2026, 10, 10)) if f.rule_id == "PAY02")
    assert finding.opposing_span_ids


def test_opposing_mentorship_account_visible():
    assert assess(new_demo("mentorship"))[0].opposing_span_ids


def test_missing_citation_and_fabricated_quote_rejected():
    case = new_demo()
    case.spans[0].quote = "Invented quotation absent from source"
    with pytest.raises(ValueError):
        Case.model_validate(case.model_dump())
    case = new_demo()
    case.claims[0].span_ids = ["nonexistent"]
    with pytest.raises(ValueError):
        assess(case)
