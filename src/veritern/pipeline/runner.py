import asyncio
import hashlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from veritern.analysis.origins import cluster_origins
from veritern.config import Settings
from veritern.discovery.search import Search, SearchUnavailable, query_plan
from veritern.identity import domain, normalize_url
from veritern.identity.resolve import in_scope
from veritern.llm.client import AnalysisUnavailable, GroqInference
from veritern.reporting.reports import assemble
from veritern.retrieval.safe import Fetcher
from veritern.schemas import Case, Check, Source
from veritern.storage.repository import Repository


class Runner:
    def __init__(self, settings: Settings, repository: Repository):
        self.settings, self.repo = settings, repository
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="veritern")
        self.lock = threading.Lock()
        self.active = False
        self.repo.recover()
        self.repo.cleanup()

    def start(self, case: Case) -> str:
        key = f"{case.id}:{case.revision}:pipeline-v1"
        if self.repo.job(key, case.owner):
            return key
        with self.lock:
            if self.active:
                raise ValueError(
                    "An investigation is running. Wait or cancel it before starting another."
                )
            if not self.repo.claim_job(key, case.id, case.owner):
                return key
            self.active = True
        self.executor.submit(self._worker, key, case.id, case.owner)
        return key

    def _worker(self, key, case_id, owner):
        try:
            asyncio.run(self.run(key, case_id, owner))
        except Exception:
            self.repo.progress(
                key, "failed", "Investigation interrupted; evidence retained. Reassess to retry."
            )
        finally:
            with self.lock:
                self.active = False

    async def run(self, key, case_id, owner):
        case = self.repo.get(case_id, owner)
        if case is None:
            return
        s = self.settings
        started = time.monotonic()
        deadline = started + s.case_deadline_seconds
        usage = case.budget_usage.model_copy(deep=True)
        checks, limits = [], []
        model = "unavailable"

        def cancelled():
            job = self.repo.job(key, owner)
            return not job or bool(job["cancelled"])

        def progress(phase, message):
            self.repo.progress(key, phase, message)

        def checkpoint():
            if not cancelled():
                self.repo.save(case)

        def persist_usage():
            case.budget_usage = usage.model_copy(deep=True)
            # Preserve spend even when cancellation arrives during an in-flight call.
            # Repository tombstones still reject deleted cases.
            if self.repo.get(case.id, owner) is not None:
                self.repo.save(case)

        async def research():
            nonlocal model
            if case.mode == "demo":
                checks.append(
                    Check(
                        name="Synthetic evidence",
                        state="resolved",
                        reason="Author-created fictional facts; no live checks",
                    )
                )
                model = "synthetic ground truth; no model called"
                return
            fetcher = Fetcher(s)
            semaphore = asyncio.Semaphore(s.fetch_max_concurrent)
            counts = {}
            visited = set()

            async def fetch(url):
                if cancelled() or time.monotonic() >= deadline:
                    return []
                async with semaphore:
                    if cancelled():
                        return []
                    cache_key = "page-v1:" + hashlib.sha256(url.encode()).hexdigest()
                    cached = self.repo.cache_get(cache_key)
                    links = []
                    if cached:
                        source = Source.model_validate(cached["source"])
                        source.cached = True
                        source.scope_confirmed = domain(source.url or url) == case.entity.domain
                        source.kind = "official" if source.scope_confirmed else "third_party"
                        links = cached.get("links", [])
                    else:
                        source, links = await fetcher.fetch(url, case.entity.domain)
                        if source.access == "retrieved":
                            self.repo.cache_put(
                                cache_key,
                                {"source": source.model_dump(mode="json"), "links": links},
                                s.public_cache_ttl_hours,
                            )
                    if source.kind == "third_party":
                        source.scope_confirmed = in_scope(
                            source.text, case.entity.domain, case.program.title
                        )
                    if not any(old.id == source.id for old in case.sources):
                        case.sources.append(source)
                    checks.append(
                        Check(
                            name="Fetch " + url,
                            state="unresolved"
                            if source.access == "retrieved"
                            else "blocked"
                            if source.access in ("blocked", "robots_disallowed")
                            else "failed",
                            reason=f"{source.access}: {source.note or 'Fetched content is not a substantive verification'}",
                            source_ids=[source.id],
                        )
                    )
                    progress(
                        "fetching",
                        f"Checking websites… {sum(x.access == 'retrieved' for x in case.sources)} sources retrieved",
                    )
                    checkpoint()
                    return links

            def reserve(url):
                d = domain(url)
                if (
                    url in visited
                    or len(visited) >= s.fetch_page_limit
                    or counts.get(d, 0) >= s.fetch_max_per_domain
                ):
                    return False
                visited.add(url)
                counts[d] = counts.get(d, 0) + 1
                return True

            progress("fetching", "Checking the selected website…")
            initial = (
                normalize_url(
                    case.original_input
                    if "." in case.original_input and " " not in case.original_input
                    else case.entity.domain
                )
                if case.entity.domain
                else None
            )
            if initial:
                reserve(initial)
            official_links = await fetch(initial) if initial else []
            urls = list(official_links)
            progress("discovering", "Searching reviews, terms and participant experiences…")
            if case.mode == "manual" or not s.search_ready:
                checks.append(
                    Check(
                        name="Automated discovery",
                        state="not_attempted",
                        reason="Manual mode or missing search credentials",
                    )
                )
            else:
                search = Search(s)
                query_gate = asyncio.Semaphore(2)

                async def discover(query):
                    async with query_gate:
                        if cancelled():
                            return
                        try:
                            results = await search.query(query)
                            checks.append(
                                Check(
                                    name="Search: " + query,
                                    state="resolved" if results else "unresolved",
                                    reason=f"{len(results)} discovery leads; snippets are not substantive findings",
                                )
                            )
                            for result in results:
                                case.sources.append(
                                    Source(
                                        title=result.title,
                                        url=result.url,
                                        publisher=domain(result.url),
                                        text=result.snippet,
                                        kind="snippet",
                                        scope_confirmed=False,
                                        note="Search snippet only; origin independence unknown",
                                    )
                                )
                                urls.append(result.url)
                        except SearchUnavailable as exc:
                            checks.append(
                                Check(name="Search: " + query, state="failed", reason=str(exc))
                            )

                await asyncio.gather(
                    *(
                        discover(q)
                        for q in query_plan(case.entity.domain, case.program.title)[
                            : s.search_query_limit
                        ]
                    )
                )
            selected = [url for url in dict.fromkeys(urls) if reserve(url)]
            await asyncio.gather(*(fetch(url) for url in selected))
            for platform in ("LinkedIn", "Glassdoor", "Reddit"):
                checks.append(
                    Check(
                        name=platform + " direct access",
                        state="not_attempted",
                        reason="Not checked: use indexed source links, pasted text or screenshots",
                    )
                )
            cluster_origins(case.sources)
            checkpoint()
            if cancelled():
                return
            progress("extracting", "Extracting source-linked claims in one bounded model batch…")
            fingerprint = hashlib.sha256(
                (
                    s.groq_model
                    + "extract-v1"
                    + "".join(
                        sorted(
                            source.id + source.content_hash
                            for source in case.sources
                            if source.kind != "snippet" and source.scope_confirmed
                        )
                    )
                ).encode()
            ).hexdigest()
            if fingerprint == case.extraction_fingerprint:
                model = s.groq_model
                checks.append(
                    Check(
                        name="Structured extraction",
                        state="resolved",
                        reason="Reused validated extraction from this private case; no new model call",
                    )
                )
                return
            try:
                claims, spans, warnings = await GroqInference(s).extract(
                    case, usage, deadline, cancelled, persist_usage
                )
                case.claims = claims
                case.spans.extend(spans)
                case.extraction_fingerprint = fingerprint
                limits.extend(warnings)
                model = s.groq_model
                checks.append(
                    Check(
                        name="Structured extraction",
                        state="resolved",
                        reason=f"{len(claims)} claims passed citation and scope checks",
                    )
                )
            except AnalysisUnavailable as exc:
                limits.append(str(exc))
                if case.claims:
                    limits.append(
                        "Previous extracted claims retained; newly added evidence could not be analyzed"
                    )
                checks.append(Check(name="Structured extraction", state="failed", reason=str(exc)))

        try:
            async with asyncio.timeout(s.case_deadline_seconds):
                await research()
        except TimeoutError:
            limits.append("Investigation deadline reached; only completed work is included")
            checks.append(
                Check(
                    name="Remaining planned work",
                    state="not_attempted",
                    reason="Case deadline reached",
                )
            )
        if cancelled():
            return
        progress("analyzing", "Comparing promises, conditions and reported experiences…")
        usage.elapsed_seconds = round(time.monotonic() - started, 2)
        checks.extend(
            [
                Check(name=label, state="unresolved", reason=reason)
                for label, reason in (
                    (
                        "Recruiting authority",
                        "Selected website does not independently establish authority",
                    ),
                    (
                        "Participant experience",
                        "Accessible accounts may be incomplete, historical or unauthenticated",
                    ),
                    (
                        "Financial practices",
                        "Private charges and payment history may be unavailable",
                    ),
                    (
                        "Partnership scope",
                        "Partner confirmation requires precise program and benefit evidence",
                    ),
                )
            ]
        )
        case.assessments.append(assemble(case, checks, usage, limits, model))
        checkpoint()
        progress("partial", "Report ready — findings and unresolved checks are shown separately")
