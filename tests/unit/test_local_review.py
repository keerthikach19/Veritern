from veritern.analysis.local import review_local_documents
from veritern.demo import new_demo
from veritern.schemas import Source


def test_local_review_without_cloud_consent():
    case = new_demo(stage="initial")
    case.sources = [
        Source(
            title="Private letter",
            text="Pay INR 50 for the certificate.\nSend your password and OTP.\nFrom domain (unauthenticated): different.example.com",
            kind="private",
            scope_confirmed=True,
        )
    ]
    case.spans = []
    findings = review_local_documents(case)
    assert {f.rule_id for f in findings} == {"LOCAL_FEE", "LOCAL_SECRET", "LOCAL_SENDER"}
    assert all(f.severity == "clarification_needed" for f in findings)
    assert not case.sources[0].consented


def test_local_negation_and_ocr_abstention():
    case = new_demo(stage="initial")
    case.sources = [
        Source(
            title="Advice",
            text="Never send your password or OTP.\nNo fee of INR 50 is required.",
            kind="private",
            scope_confirmed=True,
        )
    ]
    assert not review_local_documents(case)
    case.sources[0].text = "Pay INR 50."
    case.sources[0].ocr_review_required = True
    assert not review_local_documents(case)
