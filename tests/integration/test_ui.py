from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_home_demo_fee_timeline_and_delete(tmp_path, monkeypatch):
    from veritern.ui.app import services

    services.clear()
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


def test_reference_url_flow_provenance_compare_and_unknown_domain(tmp_path, monkeypatch):
    from veritern.ui.app import services

    services.clear()
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "reference-private"))
    monkeypatch.setenv("APP_MODE", "live")
    monkeypatch.setenv("REFERENCE_CASES_ENABLED", "true")
    app = AppTest.from_file(
        Path(__file__).resolve().parents[2] / "app.py", default_timeout=20
    ).run()
    assert not app.exception
    next(field for field in app.text_input if field.label == "Website URL").set_value(
        "https://internpe.in/"
    )
    next(box for box in app.checkbox if box.label.startswith("For a URL")).check()
    next(b for b in app.button if b.label == "Review →").click().run()
    assert not app.exception
    assert any(t.value == "InternPE" for t in app.title)
    assert any("ORIGINAL DOCUMENT NOT SUPPLIED" in c.value for c in app.caption)
    assert any("not run; no recorded AI output" in m.value for m in app.markdown)
    next(r for r in app.radio if r.label == "Workspace").set_value("Compare references").run()
    assert not app.exception
    assert any(t.value == "Wipro" for t in app.title)
    next(r for r in app.radio if r.label == "Workspace").set_value("Method & model").run()
    assert not app.exception
    next(b for b in app.button if b.label == "New investigation").click().run()
    next(field for field in app.text_input if field.label == "Website URL").set_value(
        "https://tcs.com.evil.org"
    )
    next(box for box in app.checkbox if box.label.startswith("For a URL")).check()
    next(b for b in app.button if b.label == "Review →").click().run()
    assert not app.exception
    assert any("No supplied reference exists" in warning.value for warning in app.warning)
