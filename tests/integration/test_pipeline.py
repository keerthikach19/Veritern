import httpx
import pytest
import respx

from veritern.demo import new_demo
from veritern.discovery.search import Search, SearchUnavailable
from veritern.pipeline.runner import Runner
from veritern.schemas import Case, Entity, Program
from veritern.storage.repository import Repository


async def test_demo_pipeline_no_network(settings):
    repo = Repository(settings.storage_dir)
    case = new_demo()
    repo.create(case)
    runner = Runner(settings, repo)
    repo.claim_job("job", case.id, case.owner)
    await runner.run("job", case.id, case.owner)
    result = repo.get(case.id, case.owner)
    assert len(result.assessments) == 2
    assert result.assessments[-1].usage.calls == 0
    assert repo.job("job", case.owner)["phase"] == "partial"


@respx.mock
@pytest.mark.parametrize(
    "backend,url,data",
    [
        (
            "serper",
            "https://google.serper.dev/search",
            {"organic": [{"title": "Example", "link": "https://example.com", "snippet": "test"}]},
        ),
        (
            "brave",
            "https://api.search.brave.com/res/v1/web/search",
            {
                "web": {
                    "results": [
                        {"title": "Example", "url": "https://example.com", "description": "test"}
                    ]
                }
            },
        ),
        (
            "searxng",
            "http://127.0.0.1:8080/search",
            {"results": [{"title": "Example", "url": "https://example.com", "content": "test"}]},
        ),
    ],
)
async def test_provider_adapters(settings, backend, url, data):
    from pydantic import SecretStr

    settings.search_backend = backend
    settings.serper_api_key = SecretStr("test")
    settings.brave_api_key = SecretStr("test")
    respx.route(url__startswith=url).mock(return_value=httpx.Response(200, json=data))
    results = await Search(settings).query("example")
    assert results[0].url == "https://example.com/"
    assert results[0].engine == backend


@respx.mock
async def test_searxng_json_disabled(settings):
    settings.search_backend = "searxng"
    respx.get("http://127.0.0.1:8080/search").mock(return_value=httpx.Response(403))
    with pytest.raises(SearchUnavailable, match="403"):
        await Search(settings).query("example")


async def test_manual_pipeline_missing_model_is_honest(settings, monkeypatch):
    from veritern.schemas import Source

    async def fetch(*args):
        return Source(
            title="Website",
            url="https://example.com/",
            text="Example.com offers a public internship program with clear terms.",
            kind="official",
            scope_confirmed=True,
        ), []

    monkeypatch.setattr("veritern.pipeline.runner.Fetcher.fetch", fetch)
    repo = Repository(settings.storage_dir)
    case = Case(
        owner="test",
        original_input="https://example.com",
        entity=Entity(name="Example", domain="example.com"),
        program=Program(),
        mode="manual",
    )
    repo.create(case)
    runner = Runner(settings, repo)
    repo.claim_job("job", case.id, case.owner)
    await runner.run("job", case.id, case.owner)
    result = repo.get(case.id, case.owner)
    assert result.assessments[-1].headline.startswith("Insufficient")
    assert any("key missing" in s for s in result.assessments[-1].limitations)
    assert result.assessments[-1].usage.calls == 0


async def test_cancel_before_call(settings):
    repo = Repository(settings.storage_dir)
    case = new_demo()
    repo.create(case)
    runner = Runner(settings, repo)
    repo.claim_job("job", case.id, case.owner)
    repo.cancel("job", case.owner)
    await runner.run("job", case.id, case.owner)
    assert len(repo.get(case.id, case.owner).assessments) == 1
