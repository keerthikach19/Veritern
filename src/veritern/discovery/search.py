from dataclasses import dataclass

import httpx

from veritern.config import Settings
from veritern.identity import domain, normalize_url


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    engine: str


class SearchUnavailable(Exception):
    pass


def query_plan(target_domain: str, program: str) -> list[str]:
    # Only the confirmed public domain goes to external search, never private evidence.
    return [
        f'"{target_domain}" {suffix}'
        for suffix in (
            "internship program terms fees",
            "internship experience mentor feedback",
            "stipend payment conditions",
            "certificate completion fee",
            "internship review positive negative",
            "site:reddit.com OR site:linkedin.com OR site:glassdoor.com internship",
            "projects curriculum supervision",
            "partnership recruitment authorization",
        )
    ]


class Search:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def query(self, query: str) -> list[SearchResult]:
        s = self.settings
        if s.app_mode == "demo":
            raise SearchUnavailable("Demo mode disables network access")
        if not s.search_ready:
            raise SearchUnavailable("Search not configured; enter a URL or add evidence manually")
        async with httpx.AsyncClient(timeout=12, trust_env=False, follow_redirects=False) as client:
            try:
                if s.search_backend == "serper":
                    response = await client.post(
                        "https://google.serper.dev/search",
                        headers={"X-API-KEY": s.serper_api_key.get_secret_value()},
                        json={"q": query, "num": s.search_results_per_query},
                    )
                elif s.search_backend == "brave":
                    response = await client.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        headers={"X-Subscription-Token": s.brave_api_key.get_secret_value()},
                        params={"q": query, "count": s.search_results_per_query},
                    )
                else:
                    headers = (
                        {"Authorization": "Bearer " + s.searxng_auth_token.get_secret_value()}
                        if s.searxng_auth_token.get_secret_value()
                        else {}
                    )
                    response = await client.get(
                        s.searxng_base_url.rstrip("/") + "/search",
                        params={"q": query, "format": "json"},
                        headers=headers,
                    )
                response.raise_for_status()
                data = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                status = getattr(getattr(exc, "response", None), "status_code", "connection/format")
                raise SearchUnavailable(
                    f"{s.search_backend} unavailable ({status}); no fallback used"
                ) from None
        rows = (
            data.get("organic", [])
            if s.search_backend == "serper"
            else data.get("web", {}).get("results", [])
            if s.search_backend == "brave"
            else data.get("results", [])
        )
        results = []
        for row in rows[: s.search_results_per_query]:
            try:
                url = normalize_url(row.get("link") or row.get("url", ""))
            except ValueError:
                continue
            results.append(
                SearchResult(
                    str(row.get("title", "Untitled"))[:300],
                    url,
                    str(row.get("snippet") or row.get("description") or row.get("content", ""))[
                        :2000
                    ],
                    s.search_backend,
                )
            )
        return results

    async def candidates(self, name: str) -> list[SearchResult]:
        if not name.strip() or len(name) > 120 or any(c in name for c in "@\n\r"):
            raise ValueError("Use a public company name, without personal details")
        results = await self.query(f'"{name}" official internship website')
        seen = set()
        candidates = []
        for result in results:
            d = domain(result.url)
            if d not in seen:
                seen.add(d)
                candidates.append(result)
        return candidates[:5]
