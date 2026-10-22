import json
import os
import sys

import pytest

from fl_tools.mock_server import start_mock_server
from fl_tools.models import (ModelError, Preset, apply_preset_env, ensure_variant, installed_models,
                             load_presets, resolve_tag, variant_name)

INSTALLED = ["llama3.1:latest", "qwen3.5:latest", "qwen2.5-coder:latest", "llama3.2:latest"]


def test_presets_file_is_valid():
    presets = load_presets()
    assert {"qwen25coder", "qwen35", "llama31"} <= set(presets)
    assert all(p.num_ctx >= 8192 for p in presets.values())


def test_resolve_tag():
    p = Preset("x", "qwen2.5-coder")
    assert resolve_tag(p, INSTALLED) == "qwen2.5-coder:latest"
    assert resolve_tag(Preset("l", "llama3.1"), INSTALLED) == "llama3.1:latest"   # not llama3.2
    with pytest.raises(ModelError, match="ollama pull"):
        resolve_tag(Preset("m", "mistral"), INSTALLED)
    with pytest.raises(ModelError, match="--tag"):
        resolve_tag(p, ["qwen2.5-coder:7b", "qwen2.5-coder:14b"])
    assert resolve_tag(p, ["qwen2.5-coder:7b", "qwen2.5-coder:14b"], "qwen2.5-coder:14b") == "qwen2.5-coder:14b"
    assert resolve_tag(p, ["soapfl-qwen2-5-coder-latest-c16384:latest", "qwen2.5-coder:7b"]) == "qwen2.5-coder:7b"


@pytest.mark.parametrize("style", ["new", "old"])
def test_ensure_variant_creates_once(style):
    srv = start_mock_server(ollama_models={"qwen2.5-coder:latest": None}, create_style=style)
    try:
        msgs = []
        name = ensure_variant(srv.url, "qwen2.5-coder:latest", 16384, msgs.append)
        assert name == variant_name("qwen2.5-coder:latest", 16384) + ":latest"
        assert srv.state["models"][name] == 16384
        n_create = sum(1 for r in srv.state["api_requests"] if r["path"] == "/api/create")
        assert n_create == (1 if style == "new" else 2)      # old API needs the fallback request
        ensure_variant(srv.url, "qwen2.5-coder:latest", 16384, msgs.append)   # second time: nothing to do
        assert sum(1 for r in srv.state["api_requests"] if r["path"] == "/api/create") == n_create
        assert installed_models(srv.url) == sorted(srv.state["models"])
    finally:
        srv.stop()


def test_apply_preset_env_does_not_leak_extra_body():
    env = {"SOAPFL_EXTRA_BODY": '{"old": 1}'}
    apply_preset_env(Preset("a", "f"), "m:latest", env)
    assert "SOAPFL_EXTRA_BODY" not in env and env["SOAPFL_CONTEXT_LIMIT"] == "16384"
    apply_preset_env(Preset("a", "f", extra_body={"think": False}), "m:latest", env)
    assert json.loads(env["SOAPFL_EXTRA_BODY"]) == {"think": False}


STUB = r'''
import argparse, json, os
p = argparse.ArgumentParser()
for a in ("--config", "--version", "--project", "--bugID", "--output", "--model"):
    p.add_argument(a)
a = p.parse_args()
assert os.environ["SOAPFL_MODEL_NAME"].startswith("soapfl-qwen2-5-coder"), os.environ["SOAPFL_MODEL_NAME"]
d = os.path.join(a.output, f"d4j{a.version}-{a.project}-{a.bugID}")
os.makedirs(d, exist_ok=True)
json.dump({"buggy_methods": [{"class_name": "A", "method_name": "A::f()", "score": 9}], "buggy_codes": {}},
          open(os.path.join(d, "result.json"), "w"))
json.dump({"buggy_methods": ["A::f()"]}, open(os.path.join(d, "ground_truth.json"), "w"))
'''


def test_experiment_end_to_end(tmp_path, monkeypatch):
    from fl_tools.experiment import run_experiment
    soapfl = tmp_path / "SoapFL"
    soapfl.mkdir()
    (soapfl / "run.py").write_text(STUB)
    srv = start_mock_server(ollama_models={"qwen2.5-coder:latest": None})
    monkeypatch.setenv("SOAPFL_BASE_URL", srv.url)
    try:
        lines = []
        code = run_experiment("qwen25coder", select="Lang-1,Lang-3", jobs=2, soapfl_dir=str(soapfl),
                              results_dir=str(tmp_path / "results"), reports_dir=str(tmp_path / "reports"),
                              python=sys.executable, skip_preflight=True, progress=lines.append)
        text = "\n".join(lines)
        assert code == 0, text
        assert "DONE" in text
        rep = tmp_path / "reports" / "sel-qwen25coder"
        assert (rep / "summary.md").exists() and (rep / "funnel.md").exists()
        assert (rep / "bugs" / "d4j1.4.0-Lang-1" / "result.json").exists()
        # unknown model and missing base URL are reported, not crashed
        assert run_experiment("nope", soapfl_dir=str(soapfl), results_dir=str(tmp_path), reports_dir=str(tmp_path),
                              progress=lines.append) == 2
    finally:
        srv.stop()
