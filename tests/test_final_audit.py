"""Audit tests of 2026-11-09 (execution plan, section 15): the judge asks every pair in both orders."""
import re
from itertools import combinations

from fl_tools.mock_server import start_mock_server
from fl_tools.selection import judges
from fl_tools.selection.candidates import BugCase
from fl_tools.selection.llm import JudgeClient


def _m(name, score):
    return {"method_name": name, "class_name": name.split("::")[0], "score": score,
            "test_failure_causes": "A test fails.", "method_code": "void f() {}", "method_doc": ""}


def _pairs_asked(requests):
    out = []
    for body in requests:
        user = body["messages"][-1]["content"]
        a = re.search(r"Method A: (\S+)", user).group(1)
        b = re.search(r"Method B: (\S+)", user).group(1)
        out.append((a, b))
    return out


def test_every_pair_is_sent_in_both_orders():
    names = ["a.B::one()", "a.B::two()", "a.B::three()", "a.B::four()"]
    srv = start_mock_server(reply="A")
    try:
        client = JudgeClient("mock-model", base_url=srv.url)            # no cache: every question reaches the server
        case = BugCase("Lang-1", "Lang", "x", set(), [_m(n, 8) for n in names] + [_m("a.B::low()", 2)])
        _, info = judges.S5().configure(client).order(case)
        asked = _pairs_asked(srv.requests)
    finally:
        srv.stop()
    short = [n.split("::")[1] for n in names]                            # the prompt shows Class::method short names
    assert len(asked) == 2 * 6 == info["calls"] and info["pairs"] == 6  # 4 shortlisted -> 6 pairs -> 12 questions
    for x, y in combinations(short, 2):
        fx = [p for p in asked if x in p[0] and y in p[1]]
        fy = [p for p in asked if y in p[0] and x in p[1]]
        assert len(fx) == 1 and len(fy) == 1, (x, y, asked)              # once as A-B and once as B-A
    assert not any("low" in a or "low" in b for a, b in asked)          # not in the tied top group: not judged
    # the mock always answers "A": position bias in every pair -> every pair is a draw, no method wins
    assert info["draws"] == 6


# ---------------------------------------------------------------- safeguards really reach the jobs
import os
import shutil
import subprocess

import pytest

from fl_tools.__main__ import build_parser

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_runner_safeguard_defaults():
    """The values csc/run_job.sbatch relies on (it passes --timeout 3600 and nothing else by default)."""
    a = build_parser().parse_args(["run", "--name", "x", "--timeout", "3600"])
    assert (a.timeout, a.tail_factor, a.tail_min, a.breaker_rate, a.breaker_min) == (3600, 3.0, 600, 0.5, 30)
    assert a.retry_failed is False            # failed bugs are skipped on resume unless asked
    assert a.retries == 1                     # transient errors only; the run protocol (--rep) sets 0


def test_select_call_timeout_option():
    a = build_parser().parse_args(["select", "r", "--call-timeout", "120"])
    assert a.call_timeout == 120


def _csc_env(tmp_path):
    root = tmp_path / "fl"
    (root / "images").mkdir(parents=True)
    (root / "images" / "soapfl-aarch64.sif").write_text("")
    m = root / "models" / "Qwen_Qwen2.5-Coder-7B-Instruct"
    m.mkdir(parents=True)
    (m / "w.safetensors").write_text("")
    return dict(os.environ, FL_ROOT=str(root), USER="t")


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_submit_rep_protocol(tmp_path):
    env = _csc_env(tmp_path)
    sh = os.path.join(REPO, "csc", "submit.sh")
    out = subprocess.run(["bash", sh, "qwen25coder", "--n", "all", "--rep", "3", "--dry-run"], env=env,
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    job_env = open(next((tmp_path / "fl" / "logs").glob("*.env"))).read()
    assert "FL_RUN=runall-qwen25coder-csc-r3" in job_env and "FL_SEED=2" in job_env
    assert "--retries\\ 0" in job_env and "retry-failed" not in job_env
    bad = subprocess.run(["bash", sh, "qwen25coder", "--rep", "1", "--retry-failed", "--dry-run"], env=env,
                         capture_output=True, text=True)
    assert bad.returncode != 0 and "no reruns" in bad.stderr
    plain = subprocess.run(["bash", sh, "qwen25coder", "--n", "all", "--dry-run"], env=env, capture_output=True, text=True)
    assert "retry-failed" not in plain.stdout                     # skipping known failures stays on by default
