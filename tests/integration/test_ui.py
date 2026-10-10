from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_home_demo_fee_timeline_and_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "ui-private"))
    monkeypatch.setenv("APP_MODE", "demo")
    app = AppTest.from_file(
        Path(__file__).resolve().parents[2] / "app.py", default_timeout=20
    ).run()
    assert not app.exception
    assert any("Look beyond" in t.value for t in app.title)
    button = next(b for b in app.button if b.label == "Try a fictional example")
    button.click().run()
    assert not app.exception
    assert any("Insufficient" in t.value for t in app.subheader)
    next(b for b in app.button if b.label == "Add fictional task sheet").click().run()
    assert not app.exception
    next(b for b in app.button if b.label == "Add later ₹50 request").click().run()
    assert not app.exception
    assert any("Material concerns" in t.value for t in app.subheader)
    next(b for b in app.button if b.label == "Delete this case").click().run()
    assert not app.exception
    assert any("Look beyond" in t.value for t in app.title)
