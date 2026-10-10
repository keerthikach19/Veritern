import asyncio
from collections import Counter
from uuid import uuid4
from zoneinfo import ZoneInfo

import streamlit as st

from veritern.analysis.website import verification_links
from veritern.config import Settings
from veritern.demo import DEMOS, add_late_fee, fact, new_demo, refresh_demo
from veritern.discovery.search import Search, SearchUnavailable
from veritern.identity import domain, normalize_url
from veritern.ingestion.parser import parse_upload
from veritern.ingestion.redact import redact
from veritern.pipeline.runner import Runner
from veritern.reference import load_references, reference_for_url
from veritern.reporting.reports import export_json, export_markdown
from veritern.schemas import Case, Dimension, Entity, FactKind, Program, Source
from veritern.storage.repository import Repository
from veritern.ui.reference import (
    compare_references,
    method_and_model,
    reference_library,
    reference_report,
)


@st.cache_resource
def services():
    settings = Settings()
    repo = Repository(settings.storage_dir)
    return settings, repo, Runner(settings, repo)


def activate(case, repo):
    repo.create(case)
    st.session_state.case_id = case.id
    st.session_state.pop("job_key", None)
    st.session_state.pop("preview", None)
    st.session_state.pop("candidates", None)
    st.session_state.pop("reference_id", None)


def begin(url, program, mode, repo, runner, settings):
    url = normalize_url(url)
    case = Case(
        owner=st.session_state.owner,
        original_input=url,
        entity=Entity(name=domain(url), domain=domain(url)),
        program=Program(title=program.strip() or "Unspecified program"),
        mode=mode,
        saved=settings.save_case_history,
    )
    activate(case, repo)
    st.session_state.job_key = runner.start(case)


def home(settings, repo, runner):
    st.caption("EVIDENCE BEFORE COMMITMENT")
    st.title("Look beyond the offer.")
    st.markdown("Compare what an internship promises with what the evidence actually supports.")
    if settings.reference_cases_enabled:
        st.caption(
            "Enter a supported company URL to review its supplied reference text. Uncheck ‘Use provided reference text’ for fresh website checks."
        )
    elif settings.app_mode != "demo":
        readiness(settings)
    with st.container(border=True):
        with st.form("investigation"):
            target = st.text_input(
                "Company name or website URL" if settings.search_ready else "Website URL",
                placeholder="e.g. company.com or a company name",
                max_chars=250,
            )
            program = st.text_input(
                "Program name (optional)",
                placeholder="A specific program improves matching",
                max_chars=120,
                help="Used for live research. Reference reviews retain the program and dates in their supplied source material.",
            )
            use_reference = (
                st.checkbox("Use provided reference text", value=True)
                if settings.reference_cases_enabled
                else False
            )
            manual = (
                st.checkbox("Manual discovery — use the website and evidence I add")
                if not settings.reference_cases_enabled
                else False
            )
            confirmed = st.checkbox("For a URL: this is the website I want to investigate")
            submitted = st.form_submit_button(
                "Review →"
                if settings.reference_cases_enabled
                else "Investigate →"
                if settings.search_ready
                else "Review website →",
                type="primary",
                disabled=settings.app_mode == "demo" and not settings.reference_cases_enabled,
            )
        st.caption(
            "No document upload needed. Selecting a site sets the scope; it does not verify the business."
        )
    if submitted:
        try:
            is_url = "." in target and " " not in target.strip()
            if is_url:
                if not confirmed:
                    st.warning(
                        "Confirm the website above to keep unrelated companies out of this case."
                    )
                else:
                    if use_reference:
                        reference = reference_for_url(target)
                        if reference is None:
                            st.warning(
                                "No supplied reference exists for this domain. Uncheck ‘Use provided reference text’ to run a website review; no company result will be guessed."
                            )
                        else:
                            st.session_state.reference_id = reference.id
                            st.session_state.pop("case_id", None)
                            st.rerun()
                    elif settings.app_mode == "demo":
                        st.warning(
                            "Live website access is disabled by APP_MODE. Set APP_MODE=live to run network checks."
                        )
                    else:
                        begin(
                            target,
                            program,
                            "manual" if manual or settings.search_backend == "manual" else "live",
                            repo,
                            runner,
                            settings,
                        )
                        st.rerun()
            elif target.strip() and not settings.search_ready:
                st.warning(
                    "Company-name discovery needs a search provider. Enter the exact website URL for a basic review."
                )
            elif target.strip():
                with st.spinner("Finding candidate websites…"):
                    candidates = asyncio.run(Search(settings).candidates(target))
                st.session_state.candidates = candidates
                st.session_state.candidate_program = program
                if not candidates:
                    st.warning(
                        "No candidates found. Enter the website URL; the app will not guess."
                    )
            else:
                st.warning("Enter a company name or website URL.")
        except (ValueError, SearchUnavailable) as exc:
            st.warning(str(exc))
    candidates = st.session_state.get("candidates", [])
    if candidates:
        st.subheader("Choose the intended company")
        st.caption("Search candidates are unverified. A matching name alone is not sufficient.")
        for i, result in enumerate(candidates):
            with st.container(border=True):
                st.text(result.title)
                st.caption(domain(result.url))
                st.text(result.snippet)
                if st.button("Investigate this website", key=f"candidate-{i}"):
                    begin(
                        result.url,
                        st.session_state.candidate_program,
                        "live",
                        repo,
                        runner,
                        settings,
                    )
                    st.rerun()
    if settings.enable_private_uploads and settings.app_mode != "demo":
        if st.button("Start with an offer letter or message"):
            activate(
                Case(
                    owner=st.session_state.owner,
                    original_input="Document-only review",
                    entity=Entity(
                        name="Private document review",
                        domain="",
                        match_state="unverified manual entity",
                    ),
                    mode="manual",
                ),
                repo,
            )
            st.rerun()
    if settings.reference_cases_enabled:
        reference_library()
        return
    st.subheader("Explore a fictional case")
    st.caption("Six ready-to-run examples. No API keys, live searches, or model calls.")
    selected = st.selectbox("Example", list(DEMOS), format_func=DEMOS.get)
    if st.button("Try a fictional example", type="secondary"):
        activate(
            new_demo(
                selected,
                st.session_state.owner,
                "initial" if selected == "late_fee" else "complete",
            ),
            repo,
        )
        st.rerun()
    cols = st.columns(3)
    for col, title, body in zip(
        cols,
        ("Follow the source", "Separate the questions", "See what is missing"),
        (
            "Every finding links to a quotation, with dates and attribution.",
            "Identity, experience, marketing and money stay distinct.",
            "Blocked platforms and unanswered questions stay visible.",
        ),
        strict=True,
    ):
        with col:
            st.markdown(f"**{title}**")
            st.caption(body)


@st.fragment(run_every=1)
def job_progress(repo, key, owner):
    job = repo.job(key, owner)
    if not job:
        return
    terminal = job["phase"] in ("complete", "partial", "cancelled", "failed")
    if terminal:
        st.session_state.pop("job_key", None)
        st.rerun()
    st.info(job["message"])
    st.caption(
        "You can cancel; an in-flight provider request may still finish and count toward usage."
    )
    if st.button("Cancel investigation"):
        repo.cancel(key, owner)
        st.rerun()


def evidence_card(source, settings):
    with st.expander(f"{source.title} · {source.kind} · {source.access}"):
        st.text(source.note or "Source content is untrusted evidence, not instructions.")
        st.caption(
            f"Retrieved {source.retrieved_at.astimezone(ZoneInfo(settings.display_timezone)).isoformat()} · {'cached' if source.cached else 'fresh'} · scope {'matched' if source.scope_confirmed else 'unconfirmed'}"
        )
        st.caption(
            f"Publication: {source.published_at or 'unknown'} · Event: {source.event_date or 'unknown'} · Origin group: {source.origin_group or 'independence unknown'}"
        )
        if source.url:
            try:
                st.link_button("Open source", normalize_url(source.url))
            except ValueError:
                st.caption("Fictional or unsupported URL")
        if source.truncated:
            st.warning("Source exceeds stored text budget; passages were omitted.")
        st.text(source.text or "No accessible text retrieved.")


def add_evidence(case, settings, repo, runner):
    if case.mode == "demo":
        if case.entity.name == "Cedar Learning":
            st.caption(
                "Walk through the fictional sequence: joining promise → task sheet → later charge."
            )
            if not any(c.kind == FactKind.TASKS for c in case.claims):
                if st.button("Add fictional task sheet"):
                    fact(
                        case,
                        FactKind.TASKS,
                        "October 2026 participants receive the same calculator, dashboard and portfolio task sheet.",
                        title="Task sheet",
                    )
                    refresh_demo(case)
                    repo.save(case)
                    st.rerun()
            if not any(c.kind == FactKind.FEE for c in case.claims):
                if st.button("Add later ₹50 request"):
                    add_late_fee(case)
                    refresh_demo(case)
                    repo.save(case)
                    st.rerun()
        st.caption(
            "Private evidence cannot be mixed into a fictional case. Start a live/manual case to add it."
        )
        return
    if not settings.enable_private_uploads:
        st.info("Private evidence is disabled for this deployment.")
        return
    st.caption(
        "Files are parsed locally in a bounded subprocess and discarded. Only approved text goes to Groq. Redaction is best effort: remove names, addresses and identifiers yourself."
    )
    pasted = st.text_area("Paste relevant evidence", max_chars=60000, key=f"paste-{case.id}")
    files = st.file_uploader(
        "Or add PDF, PNG/JPEG, TXT or EML",
        type=["pdf", "png", "jpg", "jpeg", "txt", "eml"],
        accept_multiple_files=True,
    )
    if st.button("Prepare redaction preview"):
        try:
            if len(files) > settings.upload_max_files:
                raise ValueError("Too many files")
            texts = [pasted] if pasted.strip() else []
            ocr_required = False
            ocr_count = 0
            total = 0
            for file in files:
                total += file.size
                if total > settings.upload_max_bytes:
                    raise ValueError("Combined files exceed upload byte budget")
                parsed = parse_upload(file.getvalue(), file.name, settings)
                ocr_count += parsed["ocr_pages"]
                if ocr_count > settings.ocr_max_pages_per_case:
                    raise ValueError("Combined OCR pages exceed case budget")
                texts.append(parsed["text"])
                ocr_required |= parsed["ocr_review_required"]
            joined = "\n\n".join(texts)
            if not joined.strip() or len(joined) > 60000:
                raise ValueError("Provide 1–60,000 characters of relevant evidence")
            st.session_state.preview = {
                "text": redact(joined),
                "ocr": ocr_required,
                "case": case.id,
            }
            st.session_state.pop("approved_preview", None)
        except ValueError as exc:
            st.error(str(exc))
    preview = st.session_state.get("preview")
    if preview and preview["case"] == case.id:
        with st.form("consent"):
            edited = st.text_area(
                "Exact text approved for Groq (edit before sending)",
                value=preview["text"],
                height=260,
                max_chars=60000,
            )
            scope = st.checkbox(
                "This evidence belongs to the company/program or document case being reviewed"
            )
            critical = st.checkbox(
                "I checked names, amounts, fee conditions and dates against the original",
                disabled=False,
            )
            consent = st.checkbox(
                "I consent to sending this exact edited text to Groq for analysis"
            )
            send = st.form_submit_button("Add evidence and review", type="primary")
        if send:
            if not scope or not critical:
                st.warning(
                    "Scope and critical-field review are required. Cloud consent is optional; without it only local text cues are checked."
                )
            elif not edited.strip():
                st.warning("Approved text is empty.")
            else:
                case.sources.append(
                    Source(
                        title=f"User evidence revision {case.revision + 1}",
                        text=edited,
                        kind="private",
                        publisher="User submission",
                        scope_confirmed=True,
                        consented=consent,
                        note="User-reviewed text; authenticity unverified. Corrections are new versions.",
                    )
                )
                case.revision += 1
                repo.save(case)
                st.session_state.pop("preview", None)
                try:
                    st.session_state.job_key = runner.start(case)
                    st.rerun()
                except ValueError as exc:
                    st.warning(str(exc))


def report_view(case, settings, repo, runner):
    st.caption(f"{case.mode.upper()} INVESTIGATION · {case.entity.domain}")
    st.title(case.entity.name)
    st.text(f"{case.program.title} · {case.program.batch or 'batch unknown'}")
    if case.mode == "demo":
        st.warning(
            "FICTIONAL DEMO — these are invented examples, not findings about real companies."
        )
    if key := st.session_state.get("job_key"):
        job_progress(repo, key, case.owner)
        return
    if not case.assessments:
        st.info("No assessment yet. Reassess to start or resume the investigation.")
    else:
        assessment = case.assessments[-1]
        if case.mode != "demo":
            readiness(settings, manual=case.mode == "manual")
        st.subheader(assessment.headline)
        st.caption(
            f"Assessment {assessment.version} · {assessment.created_at.astimezone(ZoneInfo(settings.display_timezone)).strftime('%d %b %Y, %H:%M')} · {assessment.status}"
        )
        if case.entity.domain and case.mode != "demo":
            website_review(case, assessment)
        for col, dimension in zip(st.columns(4), Dimension, strict=True):
            findings = [f for f in assessment.findings if f.dimension == dimension]
            with col, st.container(border=True):
                st.markdown(f"**{dimension.value}**")
                label = "Unknown / incomplete"
                if any(f.severity == "material_concern" for f in findings):
                    label = "⚠ Material concern"
                elif any(f.severity == "clarification_needed" for f in findings):
                    label = "? Clarification needed"
                elif findings:
                    label = "ⓘ Information found"
                st.write(label)
        summary, evidence, coverage, history = st.tabs(
            ["Findings & next steps", "Evidence library", "Checks & limits", "Assessment history"]
        )
        with summary:
            spans = {s.id: s for s in case.spans}
            sources = {s.id: s for s in case.sources}
            if not assessment.findings:
                st.info(
                    "No rule-based finding is available from this review. Read the website excerpts and complete the independent checks above before drawing a conclusion."
                )
            for finding in assessment.findings:
                with st.container(border=True):
                    st.markdown(f"**{finding.title}**")
                    st.caption(
                        f"{finding.severity.replace('_', ' ')} · {finding.strength} evidence · {finding.rule_id}"
                    )
                    st.write(finding.explanation)
                    st.caption("Scope: " + finding.scope)
                    with st.expander("Read supporting and opposing evidence"):
                        for span_id in finding.span_ids + finding.opposing_span_ids:
                            span = spans[span_id]
                            source = sources[span.source_id]
                            st.caption(
                                (
                                    "Opposing / resolution evidence · "
                                    if span_id in finding.opposing_span_ids
                                    else "Supporting evidence · "
                                )
                                + source.title
                                + " · "
                                + span.locator
                            )
                            st.text(span.quote)
                            if source.url:
                                st.link_button(
                                    "Source link",
                                    normalize_url(source.url),
                                    key=f"{finding.id}-{span_id}",
                                )
                    st.write("Next step: " + finding.remediation)
            st.markdown("**Three questions to resolve**")
            for question in assessment.questions[:3]:
                st.write("• " + question)
            st.caption(
                "If you don't know, leave the field unknown. Add written evidence when available."
            )
        with evidence:
            for source in case.sources:
                evidence_card(source, settings)
        with coverage:
            counts = Counter(c.state for c in assessment.checks)
            st.metric("Resolved planned checks", f"{counts['resolved']} / {len(assessment.checks)}")
            st.caption(
                "Includes operational search/extraction checks. Successful retrieval does not resolve business claims. This is not a trust score."
            )
            st.dataframe(
                [c.model_dump(exclude={"source_ids"}) for c in assessment.checks],
                hide_index=True,
                width="stretch",
            )
            for limitation in assessment.limitations:
                st.write("• " + limitation)
            st.caption(
                f"{assessment.usage.calls} model calls · {assessment.usage.input_tokens} input / {assessment.usage.output_tokens} output tokens · {assessment.usage.elapsed_seconds}s · cost not estimated (account pricing not configured)"
            )
        with history:
            previous = set()
            for old in case.assessments:
                rules = {f.rule_id for f in old.findings}
                st.write(f"Version {old.version}: {old.headline}")
                st.caption(
                    f"New rule findings: {', '.join(sorted(rules - previous)) or 'none'} · No longer raised: {', '.join(sorted(previous - rules)) or 'none'}"
                )
                previous = rules
        a, b = st.columns(2)
        a.download_button(
            "Download redacted Markdown",
            export_markdown(case),
            "veritern-report.md",
            "text/markdown",
        )
        b.download_button(
            "Download redacted JSON",
            export_json(case),
            "veritern-report.json",
            "application/json",
        )
    with st.expander(
        "Add evidence or a correction",
        expanded=case.mode == "demo"
        or (
            bool(case.assessments)
            and all(t.state == "not_checked" for t in case.assessments[-1].website_topics)
            and bool(case.assessments[-1].website_topics)
        ),
    ):
        add_evidence(case, settings, repo, runner)
    if case.mode != "demo" and st.button("Reassess / resume with current evidence"):
        case.revision += 1
        repo.save(case)
        try:
            st.session_state.job_key = runner.start(case)
            st.rerun()
        except ValueError as exc:
            st.warning(str(exc))
    if settings.app_env == "local":
        saved = st.checkbox("Save history on this computer", value=case.saved)
        if saved != case.saved:
            case.saved = saved
            repo.save(case)
        st.caption(
            "Local SQLite is not encrypted. Unsaved cases expire after 24 hours and are removed at next startup/cleanup; saved excerpts persist until deletion."
        )
    if st.button("Delete this case", type="secondary"):
        repo.delete(case.id, case.owner)
        for key in ("case_id", "job_key", "preview"):
            st.session_state.pop(key, None)
        st.rerun()


def readiness(settings, manual=False):
    search = settings.search_ready and not manual
    ai = bool(settings.groq_api_key.get_secret_value())
    if not search or not ai:
        missing = []
        if not search:
            missing.append("Independent web search is off")
        if not ai:
            missing.append("AI claim comparison is off")
        st.warning(
            "Basic review available. "
            + ". ".join(missing)
            + ". Website excerpts and connection checks do not verify the business."
        )
        with st.expander("Enable independent search and claim comparison"):
            st.write(
                "For automated outside evidence, configure a Serper or Brave Search key. For semantic comparison, configure a Groq key. Enter keys locally in .env using .env.example, then restart Veritern. Do not paste keys into evidence or reports."
            )
            if manual and settings.search_ready:
                st.caption(
                    "This case uses manual discovery. Start a new investigation with manual discovery unchecked to use your configured search provider."
                )


def website_review(case, assessment):
    st.subheader("What this review actually checked")
    technical = [c for c in assessment.checks if c.name in ("Public DNS", "HTTPS connection")]
    for check in technical:
        st.write(f"**{check.name}: {'passed' if check.state == 'resolved' else 'not verified'}**")
        st.caption(check.reason)
    pages = {s.url: s for s in case.sources if s.kind in ("official", "third_party")}
    official = [
        s
        for s in pages.values()
        if s.kind == "official" and s.scope_confirmed and s.access == "retrieved"
    ]
    snippets = [s for s in case.sources if s.kind == "snippet"]
    third_party = [
        s
        for s in pages.values()
        if s.kind == "third_party" and s.scope_confirmed and s.access == "retrieved"
    ]
    st.write(
        f"{len(official)} website pages read · {len(third_party)} matched outside pages read · {len(snippets)} search snippets collected"
    )
    if not official:
        st.error(
            "The website's content was not read. This is an incomplete check, not evidence that the company is fake."
        )
        for source in list(pages.values())[:3]:
            st.caption(source.note or source.access)
        st.write(
            "Open the site in your browser. If it loads, paste its About, fees or program text in ‘Add evidence’ below, or upload a screenshot. Use the independent-check links below when the site is unavailable."
        )
        st.link_button(
            "Open selected website",
            normalize_url(
                case.original_input
                if "." in case.original_input and " " not in case.original_input
                else case.entity.domain
            ),
        )
    if assessment.website_topics and official:
        st.markdown("**What the website says**")
        st.caption(
            "Keyword-selected excerpts from the selected domain, not verified facts or an AI assessment. A missing topic only means it was not found in these fetched pages."
        )
        spans = {s.id: s for s in case.spans}
        sources = {s.id: s for s in case.sources}
        for topic in assessment.website_topics:
            label = "wording found" if topic.state == "mentioned" else "not found in fetched text"
            with st.expander(
                f"{topic.title} · {label}", expanded=topic.title == "Operator & registration"
            ):
                for span_id in topic.span_ids:
                    span = spans[span_id]
                    source = sources[span.source_id]
                    st.text(span.quote)
                    st.link_button(
                        "Read original page", source.url, key="website-" + topic.title + span_id
                    )
                st.write("Verify next: " + topic.next_step)
    st.markdown("**Verify the business and this offer separately**")
    st.write(
        "Match the legal operator to an independent registry record. Confirm that the operator uses this exact domain and authorizes this recruiter. Then verify the program's work, supervision, charges and stipend with written terms and recent participants."
    )
    with st.expander(
        "Open independent checks — these have not been run by Veritern", expanded=not official
    ):
        for title, url, hint in verification_links(case.entity.domain):
            st.link_button(title, url)
            st.caption(hint)


def main():
    st.set_page_config(
        page_title="Veritern · Evidence before commitment", page_icon="◈", layout="wide"
    )
    try:
        settings, repo, runner = services()
    except ValueError:
        st.error(
            "Configuration is invalid. Check .env against .env.example; secret values are not displayed."
        )
        st.stop()
    if "owner" not in st.session_state:
        st.session_state.owner = str(uuid4())
    active_case = repo.get(st.session_state.get("case_id", ""), st.session_state.owner)
    with st.sidebar:
        st.title("◈ Veritern")
        st.caption("An evidence-first second look.")
        st.divider()
        display_mode = (
            "reference"
            if st.session_state.get("reference_id") and settings.reference_cases_enabled
            else active_case.mode
            if active_case
            else "basic review"
            if settings.app_mode == "live" and not settings.search_ready
            else settings.app_mode
        )
        st.markdown(f"**{display_mode.upper()} MODE**")
        st.caption(
            f"Discovery: {settings.search_backend} · {'configured' if settings.search_ready else 'not configured'}"
        )
        st.caption(
            f"Groq: {'key present' if settings.groq_api_key.get_secret_value() else 'not configured'}"
        )
        if settings.ephemeral_storage:
            st.warning("Ephemeral storage: saved cases may disappear after a host restart.")
        if st.button("New investigation", width="stretch", disabled=runner.active):
            for key in ("case_id", "preview", "candidates", "reference_id"):
                st.session_state.pop(key, None)
            st.session_state.workspace_page = "Review"
            st.rerun()
        if settings.app_env == "local":
            saved = repo.list_saved()
            if saved:
                selected = st.selectbox(
                    "Saved on this computer",
                    saved,
                    format_func=lambda c: c.entity.name + " · " + c.created_at.strftime("%d %b"),
                )
                if st.button("Open saved case"):
                    st.session_state.owner = selected.owner
                    st.session_state.case_id = selected.id
                    st.session_state.pop("reference_id", None)
                    st.rerun()
        if st.button("Clear public page cache"):
            repo.clear_cache()
            st.success("Public page cache cleared.")
        st.divider()
        st.caption("No scam scores. No safety seals. Missing evidence stays missing.")
        page = (
            st.radio(
                "Workspace",
                ["Review", "Compare references", "Method & model"],
                key="workspace_page",
            )
            if settings.reference_cases_enabled
            else "Review"
        )
    if page == "Compare references":
        compare_references(settings)
        return
    if page == "Method & model":
        method_and_model(settings)
        return
    if settings.reference_cases_enabled and (reference_id := st.session_state.get("reference_id")):
        reference_report(load_references()[reference_id], settings)
        return
    case = repo.get(st.session_state.get("case_id", ""), st.session_state.owner)
    if case:
        report_view(case, settings, repo, runner)
    else:
        home(settings, repo, runner)
