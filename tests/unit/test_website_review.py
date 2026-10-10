import pytest

from veritern.analysis.website import verification_links, website_topics
from veritern.reporting.reports import assemble, export_markdown
from veritern.schemas import Case, Entity, Source, Usage


def website_case():
    return Case(
        owner="test",
        original_input="https://example.com",
        entity=Entity(name="Example", domain="example.com"),
        mode="manual",
    )


def test_self_published_topics_are_cited_not_verified_findings():
    case = website_case()
    case.sources.append(
        Source(
            title="About",
            url="https://example.com/about",
            kind="official",
            scope_confirmed=True,
            text="Owned and operated by Example Learning, registered as UDYAM-AA-00-1234567.\nTraining includes supervised project work.\nWe charge no fees for this program.",
        )
    )
    report = assemble(case, [], Usage(), [])
    case.assessments.append(report)
    assert report.headline.startswith("Basic website review")
    assert report.findings == []
    assert report.website_topics[0].state == "mentioned"
    assert report.website_topics[1].state == "not_found"
    assert all(s.quote in case.sources[0].text for s in case.spans)
    assert Case.model_validate(case.model_dump())
    assert "UDYAM-AA-00-1234567" in export_markdown(case)
    assert "not completed checks" in export_markdown(case)
    count = len(case.spans)
    website_topics(case)
    assert len(case.spans) == count


def test_blocked_missing_and_unrelated_pages_never_supply_website_claims():
    case = website_case()
    for kind, scope, access in [
        ("official", True, "robots_disallowed"),
        ("third_party", False, "retrieved"),
        ("snippet", False, "retrieved"),
    ]:
        case.sources.append(
            Source(
                title="Unverified",
                kind=kind,
                scope_confirmed=scope,
                access=access,
                text="Registered business provides free training.",
            )
        )
    report = assemble(case, [], Usage(), [])
    assert report.headline.startswith("Website review incomplete")
    assert all(t.state == "not_checked" for t in report.website_topics)
    assert case.spans == []


def test_new_failed_attempt_does_not_present_old_site_text_as_fresh():
    case = website_case()
    case.sources.extend(
        [
            Source(
                title="Earlier",
                url="https://example.com",
                kind="official",
                scope_confirmed=True,
                text="Registered training provider.",
            ),
            Source(
                title="Now",
                url="https://example.com",
                kind="third_party",
                access="robots_unavailable",
            ),
        ]
    )
    assert all(t.state == "not_checked" for t in website_topics(case))


def test_manual_search_is_exact_domain_and_url_encoded():
    links = verification_links("example.com")
    search = next(url for _, url, _ in links if "google.com" in url)
    assert "%22example.com%22" in search
    assert "-site%3Aexample.com" in search


def test_short_contact_and_training_lines_are_not_discarded():
    case = website_case()
    case.sources.append(
        Source(
            title="Contact",
            url="https://example.com",
            kind="official",
            scope_confirmed=True,
            text="Contact\nhr@example.com\nTraining\nSupervised weekly work.",
        )
    )
    topics = website_topics(case)
    assert topics[1].state == "mentioned"
    assert topics[3].state == "mentioned"
    assert all(span.quote in case.sources[0].text for span in case.spans)


@pytest.mark.parametrize("success", [True, False])
async def test_tls_check_verifies_hostname_and_closes_stream(monkeypatch, success):
    import ssl

    import httpcore

    import veritern.identity.technical as module

    class Stream:
        closed = False

        async def start_tls(self, context, server_hostname, timeout):
            assert context.verify_mode == ssl.CERT_REQUIRED
            assert context.check_hostname
            assert server_hostname == "example.com"
            if not success:
                raise httpcore.ConnectError("TLS unavailable")
            return self

        async def aclose(self):
            self.closed = True

    stream = Stream()

    async def resolve(*args):
        return ["93.184.216.34"]

    async def connect(*args, **kwargs):
        return stream

    monkeypatch.setattr(module, "public_addresses", resolve)
    monkeypatch.setattr(module.PublicBackend, "connect_tcp", connect)
    checks = await module.connection_checks("https://example.com")
    assert checks[0].state == "resolved"
    assert checks[1].state == ("resolved" if success else "failed")
    assert stream.closed
