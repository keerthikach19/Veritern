"""Presentation of supplied case material without attributing it to live tools."""

import streamlit as st

from veritern.analysis.website import verification_links
from veritern.reference import export_reference, load_references, review_reference


def reference_library():
    st.subheader("Case library")
    st.caption("Provided reference text · five companies · original letters not supplied")
    for col, case in zip(st.columns(5), load_references().values(), strict=True):
        with col, st.container(border=True):
            st.markdown(f"**{case.company}**")
            st.caption(case.domains[0])
            if st.button("Open review", key="reference-" + case.id, width="stretch"):
                st.session_state.reference_id = case.id
                st.session_state.pop("case_id", None)
                st.rerun()


def result_header(case):
    result = review_reference(case)
    st.title(case.company)
    st.caption("PROVIDED REFERENCE TEXT · ORIGINAL DOCUMENT NOT SUPPLIED")
    if result.classification == "UNKNOWN":
        st.info("UNKNOWN — authenticity has not been verified")
    else:
        st.warning(result.classification)
    st.write(result.reason)
    st.caption(
        "This result applies to the supplied reference material, not to the company or every offer bearing its name."
    )
    return result


def reference_report(case, settings):
    result = result_header(case)
    review, evidence, checks, provenance = st.tabs(
        ["Review & next steps", "Evidence", "Checks", "Analysis provenance"]
    )
    with review:
        st.subheader("Details in the supplied reference")
        st.dataframe(
            [{"Field": k, "Supplied detail": v} for k, v in case.fields.items()],
            hide_index=True,
            width="stretch",
        )
        st.subheader("Why this result")
        for note in case.notes:
            with st.container(border=True):
                st.markdown(f"**{note.title}**")
                st.caption(
                    {
                        "clarification": "Needs clarification",
                        "positive": "Positive structural indicator",
                        "limitation": "Evidence gap",
                    }[note.category]
                )
                st.write(note.explanation)
                st.text(note.quote)
                st.caption(f"Source: provided reference notes · {case.id} · {case.supplied_on}")
        st.subheader("Five questions for the issuer")
        for index, question in enumerate(case.questions, 1):
            st.write(f"{index}. {question}")
        with st.expander("Open independent verification channels"):
            st.link_button("Open the supplied company website", case.url)
            st.caption("Link supplied with the case. It has not been checked in this report.")
            for title, url, hint in verification_links(case.domains[0]):
                st.link_button(title, url)
                st.caption(hint)
    with evidence:
        st.subheader("Matched phrases in the supplied text")
        for phrase in result.matched_phrases:
            st.text(phrase)
        st.caption(
            "These matches come from the reference text below, not from OCR of an uploaded image. Phrase matching identifies a text family; it cannot authenticate an offer."
        )
        with st.expander("Read complete supplied reference text"):
            st.text(case.reference_text)
        st.info(
            "Images, original offer letters, annexures and participant posts were not supplied. No unsupported payment claim or similarity percentage is added."
        )
    with checks:
        st.dataframe(
            [
                {
                    "Check": "Reference text and quoted notes",
                    "Status": "USER_PROVIDED",
                    "Detail": "Loaded from the bundled, schema-validated case file",
                },
                {
                    "Check": "Phrase matching",
                    "Status": "CHECKED_FOUND",
                    "Detail": f"{len(result.matched_phrases)} phrases matched locally in supplied text",
                },
                {
                    "Check": "OCR / original document inspection",
                    "Status": "NOT_CHECKED",
                    "Detail": "No image or original letter supplied",
                },
                {
                    "Check": "Website, DNS and TLS",
                    "Status": "NOT_CHECKED",
                    "Detail": "No network requests are made by this reference review",
                },
                {
                    "Check": "Registry / issuer authentication",
                    "Status": "NOT_CHECKED",
                    "Detail": "Not independently verified",
                },
                {
                    "Check": "LinkedIn / Reddit / Glassdoor",
                    "Status": "NOT_CHECKED",
                    "Detail": "No external searches or participant posts in this reference review",
                },
                {
                    "Check": "Model inference / saved model output",
                    "Status": "NOT_CHECKED",
                    "Detail": "No model run or recorded output supplied",
                },
            ],
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Unchecked sources are never counted as clean evidence. No trust score is calculated from incomplete reference notes."
        )
    with provenance:
        st.write(
            "**Evidence:** user-provided company patterns and case notes, supplied 10 October 2026."
        )
        st.write(
            "**Execution:** local deterministic matching and reference-note assembly, run when this report is opened."
        )
        st.write("**OCR:** not run; original images not supplied.")
        st.write("**AI:** not run; no recorded AI output used.")
        st.write(
            f"**Configured live model:** `{settings.groq_model}` via Groq; Apache-2.0 open weights. The configured model did not generate this reference report."
        )
        st.write(
            "**External checks:** none for this report. Use the normal website review separately for fresh page and connection checks."
        )
        st.write(
            "**Authenticity:** not verified. A known brand or consistent formatting is not confirmation."
        )
    st.download_button(
        "Download reference report",
        export_reference(case),
        f"veritern-{case.id}-reference.json",
        "application/json",
    )
    st.caption("Verification required: Yes")


def compare_references(settings):
    st.title("Compare references")
    st.caption("Both panels use supplied text; neither authenticates the original offer.")
    cases = load_references()
    left, right = st.columns(2)
    for col, key, index in [(left, "compare-left", 0), (right, "compare-right", 4)]:
        with col:
            selected = st.selectbox(
                "Company",
                list(cases),
                index=index,
                format_func=lambda value: cases[value].company,
                key=key,
            )
            case = cases[selected]
            result_header(case)
            st.dataframe(
                [{"Field": k, "Supplied detail": v} for k, v in case.fields.items()],
                hide_index=True,
            )
            for note in case.notes:
                st.markdown(f"**{note.title}**")
                st.write(note.explanation)
            st.caption("AI, OCR and independent authentication: not run.")


def method_and_model(settings):
    st.title("Method & model")
    st.write(
        "Veritern separates supplied evidence, technical observations and independent verification."
    )
    st.markdown(
        "**Reference review:** exact domain → supplied case text → validated phrase matches and quoted notes → clarification questions. No external service is called."
    )
    st.markdown(
        "**Website review:** confirmed domain → DNS/TLS checks → robots-aware page fetching → cited topic excerpts. Configured search and Groq can add independent discovery and structured claim comparison."
    )
    st.markdown(
        "**Decision rules:** a brand name alone never implies fraud. Training, certificates, probation and a joining date are not standalone red flags. Supplied inconsistencies prompt verification; an incomplete document stays unknown. No prepared case is marked verified genuine."
    )
    st.subheader("Model card")
    st.write(f"Model: `{settings.groq_model}` · open weights · Apache-2.0 weight license.")
    st.write(
        "Serving provider for the existing live adapter: Groq, a proprietary hosted service. No other model is silently substituted. The model extracts source-linked claims; local code validates quotations and determines rule findings."
    )
    st.link_button("Official model card", "https://huggingface.co/openai/gpt-oss-20b")
    st.link_button(
        "Groq model documentation", "https://console.groq.com/docs/model/openai/gpt-oss-20b"
    )
    st.caption(
        "Reference reports use no AI inference. Generic OpenRouter/vLLM endpoint switching and recorded model replay are not implemented in this version."
    )
    st.subheader("Limits")
    st.write(
        "No original images were provided for the five references. OCR, document authenticity, badge recognition, template similarity and claims about unprovided experiences remain unchecked. Accessible websites and domain registration do not establish offer authenticity."
    )
