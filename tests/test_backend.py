"""Tests of the patched SoapFL backend against the mock server.

Need a patched SoapFL checkout: set SOAPFL_DIR (default external/SoapFL). Skipped otherwise.
Each scenario runs in a fresh interpreter because the OpenAI client is cached per process.
"""
import json
import os
import subprocess
import sys
import tempfile

import pytest

from fl_tools.mock_server import start_mock_server

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOAPFL = os.environ.get("SOAPFL_DIR", os.path.join(ROOT, "external", "SoapFL"))
pytestmark = pytest.mark.skipif(not os.path.exists(os.path.join(SOAPFL, "camel", "local_llm.py")),
                                reason="patched SoapFL checkout not found (set SOAPFL_DIR)")

CALL = r'''
import json, os, sys
sys.path.insert(0, sys.argv[1])
from camel.typing import ModelType
from camel.configs import ChatGPTConfig
from camel.model_backend import ModelFactory
b = ModelFactory.create(ModelType.LOCAL, ChatGPTConfig().__dict__)
msgs = [{"role": "user", "content": sys.argv[2]}]
r = b.run(messages=msgs)
print(json.dumps({"content": r.choices[0].message.content, "usage": getattr(r, "usage", None) is not None}))
'''


def call(srv, prompt="hi", **env):
    run_dir = tempfile.mkdtemp()
    e = os.environ.copy()
    e.update(SOAPFL_BASE_URL=srv.url, SOAPFL_API_KEY="x", SOAPFL_MODEL_NAME="mock-model",
             SOAPFL_CONTEXT_LIMIT="8192", SOAPFL_RUN_DIR=run_dir, PYTHONWARNINGS="ignore")
    e.update(env)
    proc = subprocess.run([sys.executable, "-c", CALL, SOAPFL, prompt], capture_output=True, text=True, env=e)
    events = []
    p = os.path.join(run_dir, "events.jsonl")
    if os.path.exists(p):
        events = [json.loads(l) for l in open(p) if l.strip()]
    return proc, events


def test_think_stripped_and_event_logged():
    srv = start_mock_server(reply="Looks buggy. #8#", think=True, max_model_len=8192)
    try:
        proc, events = call(srv)
        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout.splitlines()[-1])["content"] == "Looks buggy. #8#"
        assert srv.requests[-1]["model"] == "mock-model"
        call_ev = [e for e in events if e["type"] == "llm_call"][0]
        assert call_ev["think_chars_removed"] > 0 and call_ev["finish_reason"] == "stop"
    finally:
        srv.stop()


def test_max_tokens_shrinks_for_big_prompt():
    srv = start_mock_server(max_model_len=8192, enforce_context=True)
    try:
        proc, _ = call(srv, "word " * 5200)
        assert proc.returncode == 0, proc.stderr
        assert srv.requests[-1]["max_tokens"] < 4096
    finally:
        srv.stop()


def test_null_content_and_missing_usage():
    srv = start_mock_server(null_content=True, omit_usage=True)
    try:
        proc, _ = call(srv)
        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout.splitlines()[-1])["content"] == ""
    finally:
        srv.stop()


def test_missing_model_name_is_a_clear_error():
    srv = start_mock_server()
    try:
        proc, _ = call(srv, SOAPFL_MODEL_NAME="")
        assert proc.returncode != 0 and "SOAPFL_MODEL_NAME" in proc.stderr
    finally:
        srv.stop()


PARSE = r'''
import json, os, sys
sys.path.insert(0, sys.argv[1])
from camel.local_llm import parse_score, strip_think
os.environ["SOAPFL_LENIENT_PARSING"] = sys.argv[2]
cases = ["#7#", "blah #3# blah #9#", "# 5 #", "Score: 6", "8/10", "#42#", "no score", "<think>#1#</think>#4#"]
out = []
for c in cases:
    t, _ = strip_think(c)
    try:
        out.append(parse_score(t))
    except Exception as exc:
        out.append("ERR:" + type(exc).__name__)
print(json.dumps(out))
'''


@pytest.mark.parametrize("lenient,expected", [
    ("0", [7, 3, None, None, None, 42, None, 4]),
    ("1", [7, 3, 5, 6, 8, None, None, 4]),
])
def test_parse_score(lenient, expected):
    proc = subprocess.run([sys.executable, "-c", PARSE, SOAPFL, lenient], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    got = json.loads(proc.stdout.splitlines()[-1])
    norm = [("ERR" if isinstance(g, str) and g.startswith("ERR") else g) for g in got]
    assert norm == expected, got


def test_unix_socket_endpoint(tmp_path):
    """vLLM on Roihu listens on a Unix socket (--uds); SOAPFL_UDS must route the client through it."""
    sock = str(tmp_path / "vllm.sock")
    srv = start_mock_server(reply="Via socket. #7#", max_model_len=8192, uds=sock)
    try:
        proc, events = call(srv, SOAPFL_UDS=sock, SOAPFL_BASE_URL="")
        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout.splitlines()[-1])["content"] == "Via socket. #7#"
        assert [e for e in events if e["type"] == "llm_call"]
    finally:
        srv.stop()
