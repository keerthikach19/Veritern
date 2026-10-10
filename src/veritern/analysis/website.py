"""Small, cited website reading aid; patterns identify topics, not truth."""

import re
from urllib.parse import quote_plus

from veritern.schemas import Case, EvidenceSpan, WebsiteTopic

TOPICS = (
    (
        "Operator & registration",
        r"\b(?:owned|operated|managed|registered|registration|CIN|LLPIN|UDYAM|MSME)\b",
        "Match the legal name and registration number against the issuing registry. A logo or number on this website is only a claim.",
    ),
    (
        "Contact & address",
        r"\b(?:address|contact|office|email|e-mail)\b|[\w.+-]+@[\w.-]+\.[a-z]{2,}",
        "Confirm the operator and this exact program using contact details obtained independently. A contact form alone does not establish an employer.",
    ),
    (
        "Fees, stipend & refunds",
        r"\b(?:fees?|charges?|stipend|salary|refund|payment|paid|unpaid)\b|₹|\bINR\b",
        "Obtain written total charges, certificate conditions, refund terms and guaranteed compensation for your batch. Missing wording does not mean free or paid.",
    ),
    (
        "Work, training & supervision",
        r"\b(?:mentor\w*|training|tasks?|projects?|supervis\w*|curriculum)\b",
        "Confirm the supervisor, weekly work, feedback and whether the program is employment, training or a task-based certificate program. Check recent participants independently.",
    ),
)


def website_topics(case: Case) -> list[WebsiteTopic]:
    if case.mode == "demo" or not case.entity.domain:
        return []
    # Keep historical sources for citations, but review only the latest attempt per URL.
    latest = {}
    for source in case.sources:
        if source.kind in ("official", "third_party"):
            latest[source.url] = source
    pages = [
        s
        for s in latest.values()
        if s.kind == "official" and s.scope_confirmed and s.access == "retrieved"
    ]
    result = []
    for title, pattern, next_step in TOPICS:
        matches, seen = [], set()
        for source in pages:
            lines = source.text.splitlines()
            for n, line in enumerate(lines, 1):
                line = line.strip()
                match = re.search(pattern, line, re.I)
                if not match:
                    continue
                if len(line) < 35:
                    # Short headings/contact labels need their adjacent detail, not exclusion.
                    line = "\n".join(lines[n - 1 : n + 2]).strip()
                # Bounded exact excerpt around the term, never generated prose.
                start = max(0, match.start() - 140)
                excerpt = line[start : start + 650]
                normalized = " ".join(excerpt.split())
                if normalized in seen:
                    continue
                seen.add(normalized)
                existing = next(
                    (s for s in case.spans if s.source_id == source.id and s.quote == excerpt), None
                )
                span = existing or EvidenceSpan(
                    source_id=source.id, quote=excerpt, locator=f"website text line {n}; excerpt"
                )
                if existing is None:
                    case.spans.append(span)
                matches.append(span.id)
                if len(matches) == 3:
                    break
            if len(matches) == 3:
                break
        result.append(
            WebsiteTopic(
                title=title,
                state="mentioned" if matches else "not_found" if pages else "not_checked",
                span_ids=matches,
                next_step=next_step,
            )
        )
    return result


def verification_links(target_domain: str) -> list[tuple[str, str, str]]:
    return [
        (
            "Look up domain registration",
            "https://lookup.icann.org/en/lookup?name=" + quote_plus(target_domain),
            "Check registration dates and registrar where available. Redacted ownership and domain age do not establish legitimacy.",
        ),
        (
            "Search independent mentions",
            "https://www.google.com/search?q="
            + quote_plus(f'"{target_domain}" -site:{target_domain} internship review fees'),
            "Opens a search in your browser; Veritern has not checked these results. Match the exact domain, program and dates.",
        ),
        (
            "Verify a claimed Indian MSME registration",
            "https://udyamregistration.gov.in/",
            "Use Print/Verify → Verify Udyam Registration if an Udyam number is claimed. Match the enterprise name; registration does not endorse this internship.",
        ),
        (
            "Check an Indian company or LLP",
            "https://www.mca.gov.in/",
            "Use MCA master data if the operator claims to be a company or LLP. Other business forms need the appropriate registry; this portal has not been checked for this case.",
        ),
    ]
