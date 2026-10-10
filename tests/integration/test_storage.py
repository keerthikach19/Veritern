from datetime import timedelta

import pytest

from veritern.demo import new_demo
from veritern.schemas import now
from veritern.storage.repository import Repository


def test_owner_isolation_and_tombstone(tmp_path):
    repo = Repository(tmp_path / "private")
    case = new_demo(owner="alice")
    repo.create(case)
    assert repo.get(case.id, "bob") is None
    assert repo.claim_job("job", case.id, "alice")
    assert not repo.claim_job("job", case.id, "alice")
    repo.delete(case.id, "bob")
    assert repo.get(case.id, "alice")
    repo.delete(case.id, "alice")
    assert repo.get(case.id, "alice") is None
    assert repo.job("job", "alice")["cancelled"]
    with pytest.raises(ValueError):
        repo.save(case)


def test_expiry_recovery_and_cache(tmp_path):
    repo = Repository(tmp_path / "private")
    case = new_demo(owner="alice")
    repo.create(case)
    repo.claim_job("job", case.id, case.owner)
    repo.recover()
    assert repo.job("job", case.owner)["phase"] == "partial"
    repo.cache_put("key", {"public": "text"}, 24)
    assert repo.cache_get("key") == {"public": "text"}
    with repo.connect() as con:
        con.execute("UPDATE cases SET updated=?", ((now() - timedelta(days=2)).isoformat(),))
    repo.cleanup()
    assert repo.get(case.id, case.owner) is None
    repo.clear_cache()
    assert repo.cache_get("key") is None
    repo.migrate()
    with repo.connect() as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 1


def test_failed_transaction_rolls_back(tmp_path):
    repo = Repository(tmp_path / "private")
    with pytest.raises(RuntimeError), repo.connect() as con:
        con.execute("INSERT INTO cache VALUES('key','{}','9999')")
        raise RuntimeError("interrupted")
    assert repo.cache_get("key") is None
