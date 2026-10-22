"""Checks to run BEFORE spending GPU hours: every item below has caused a failed run in practice.

Each check returns (level, name, message) with level in {"ok", "warn", "fail"}.
"""
import filecmp
import importlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from typing import List, Optional, Tuple

Check = Tuple[str, str, str]

REQUIRED_MODULES = ["openai", "tenacity", "tiktoken", "tree_sitter", "numpy", "requests"]


def check_python_modules(python: Optional[str] = None) -> List[Check]:
    python = python or sys.executable
    out: List[Check] = []
    for mod in REQUIRED_MODULES:
        proc = subprocess.run([python, "-c", f"import {mod}"], capture_output=True, text=True)
        if proc.returncode == 0:
            out.append(("ok", f"python:{mod}", "importable"))
        else:
            out.append(("fail", f"python:{mod}", f"cannot import in {python}: "
                        f"{proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else 'unknown error'}"))
    return out


def check_patch_applied(soapfl_dir: str) -> List[Check]:
    marker = os.path.join(soapfl_dir, "camel", "local_llm.py")
    if os.path.exists(marker):
        return [("ok", "patch", "open-model patch is applied (camel/local_llm.py present)")]
    return [("fail", "patch", f"{marker} is missing: run scripts/setup_soapfl.sh or "
                              f"`git -C {soapfl_dir} apply patches/0001-open-model-support.patch`")]


def check_defects4j(defects4j_home: Optional[str]) -> List[Check]:
    out: List[Check] = []
    exe = shutil.which("defects4j")
    if defects4j_home:
        cand = os.path.join(defects4j_home, "framework", "bin", "defects4j")
        if os.path.exists(cand):
            exe = cand
    if not exe:
        return [("fail", "defects4j", "defects4j not found on PATH and DEFECTS4J_HOME unset/invalid")]
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(exe) + os.pathsep + env.get("PATH", "")
    try:
        proc = subprocess.run([exe, "info", "-p", "Lang"], capture_output=True, text=True, timeout=120, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [("fail", "defects4j", f"could not run {exe}: {exc}")]
    if proc.returncode != 0:
        out.append(("fail", "defects4j", f"`defects4j info -p Lang` failed: {proc.stderr.strip()[:200]}"))
    else:
        out.append(("ok", "defects4j", f"works ({exe})"))
    return out


def check_java() -> List[Check]:
    java = shutil.which("java")
    if not java:
        return [("fail", "java", "java not found on PATH (Defects4J 1.x needs Java 8)")]
    proc = subprocess.run([java, "-version"], capture_output=True, text=True)
    text = (proc.stderr or proc.stdout).strip().splitlines()
    first = text[0] if text else "unknown"
    if '"1.8' in first or "openjdk version \"8" in first:
        return [("ok", "java", first)]
    return [("warn", "java", f"{first} -- Defects4J 1.x is normally run with Java 8; other versions "
                             f"may fail at compile/test time")]


def check_overlay(soapfl_dir: str, defects4j_home: Optional[str]) -> List[Check]:
    """SoapFL ships Defects4J_mod, which must be copied over the Defects4J install."""
    from .bugs import VERSION
    overlay = os.path.join(soapfl_dir, "Defects4J_mod", f"defects4j-{VERSION}-jvm-mod")
    if not os.path.isdir(overlay):
        return [("fail", "overlay", f"no {overlay}: SoapFL ships overlays only for Defects4J 1.4.0 and 2.0.0")]
    if not defects4j_home or not os.path.isdir(defects4j_home):
        return [("warn", "overlay", "DEFECTS4J_HOME not set, cannot verify the Defects4J_mod overlay")]
    differing, missing = [], []
    for root, _, files in os.walk(overlay):
        for name in files:
            src = os.path.join(root, name)
            rel = os.path.relpath(src, overlay)
            dst = os.path.join(defects4j_home, rel)
            if not os.path.exists(dst):
                missing.append(rel)
            elif not filecmp.cmp(src, dst, shallow=False):
                differing.append(rel)
    if missing or differing:
        bad = (missing + differing)[:5]
        return [("fail", "overlay", f"{len(missing)} missing / {len(differing)} different files vs "
                                    f"Defects4J_mod (e.g. {', '.join(bad)}). Copy the overlay: "
                                    f"cp -r {overlay}/* {defects4j_home}/")]
    return [("ok", "overlay", "Defects4J_mod overlay is installed")]


def check_tiktoken_cache() -> List[Check]:
    cache = os.environ.get("TIKTOKEN_CACHE_DIR") or os.environ.get("DATA_GYM_CACHE_DIR")
    if cache and os.path.isdir(cache) and os.listdir(cache):
        return [("ok", "tiktoken-cache", f"{cache} is populated")]
    return [("warn", "tiktoken-cache",
             "TIKTOKEN_CACHE_DIR is not set/populated. On nodes without internet SoapFL falls back to a "
             "rough 3-chars-per-token estimate (works, but less exact). scripts/setup_soapfl.sh warms the cache.")]


def _http_json(url: str, payload: Optional[dict], api_key: str, timeout: float = 60):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def parse_ollama_num_ctx(show: dict) -> Optional[int]:
    """num_ctx from an Ollama /api/show reply (Modelfile PARAMETER), or None if not set."""
    for line in (show.get("parameters") or "").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == "num_ctx" and parts[1].isdigit():
            return int(parts[1])
    return None


def check_ollama(base_url: str, model: Optional[str], context_limit: Optional[int]) -> List[Check]:
    """Ollama's /v1 API ignores the context size and SILENTLY TRUNCATES prompts longer than num_ctx
    (default 2048-4096 tokens, far below what SoapFL needs). Check the model's configured num_ctx."""
    origin = base_url.rstrip("/")
    if origin.endswith("/v1"):
        origin = origin[:-3]
    try:
        show = _http_json(origin + "/api/show", {"model": model, "name": model}, "EMPTY", timeout=20)
    except (urllib.error.URLError, OSError, ValueError):
        return []  # not an Ollama server
    num_ctx = parse_ollama_num_ctx(show)
    if num_ctx is None:
        return [("fail", "ollama-num_ctx", f"{model!r} has no num_ctx set, so Ollama uses its small default "
                 f"and silently cuts SoapFL's long prompts. Create a variant: see configs/ollama/")]
    if context_limit and context_limit > num_ctx:
        return [("fail", "ollama-num_ctx", f"SOAPFL_CONTEXT_LIMIT={context_limit} > model num_ctx={num_ctx}: "
                 f"prompts would be silently truncated. Lower SOAPFL_CONTEXT_LIMIT or raise num_ctx")]
    return [("ok", "ollama-num_ctx", f"num_ctx={num_ctx}" +
             ("" if context_limit else "; set SOAPFL_CONTEXT_LIMIT to this value"))]


def entry_has_len(served: list, model: str) -> bool:
    return any(m.get("id") == model and m.get("max_model_len") for m in served)


def check_endpoint(base_url: Optional[str], model: Optional[str], api_key: str = "EMPTY",
                   context_limit: Optional[int] = None, chat: bool = True) -> List[Check]:
    out: List[Check] = []
    if not base_url:
        return [("fail", "endpoint", "no base URL: set SOAPFL_BASE_URL (e.g. http://localhost:8000/v1)")]
    if not model:
        out.append(("fail", "model-name", "SOAPFL_MODEL_NAME is not set (must equal the name the server serves)"))
    base_url = base_url.rstrip("/")
    try:
        listing = _http_json(base_url + "/models", None, api_key, timeout=20)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        out.append(("fail", "endpoint", f"cannot reach {base_url}/models: {exc}"))
        return out
    served = listing.get("data", [])
    names = [m.get("id") for m in served]
    if model and model not in names and f"{model}:latest" in names:
        model = f"{model}:latest"   # Ollama lists untagged models with an implicit ':latest'
        out.append(("warn", "model-name", f"served as {model!r}; set SOAPFL_MODEL_NAME={model} in .env"))
    out.append(("ok", "endpoint", f"{base_url} reachable, serves {', '.join(map(str, names)) or '(nothing)'}"))
    if model and model not in names:
        out.append(("fail", "model-name", f"SOAPFL_MODEL_NAME={model!r} not among served models {names}. "
                    f"Tip: `python -m fl_tools experiment <preset>` picks and prepares the model automatically"))
    elif model:
        out.append(("ok", "model-name", f"{model!r} is served"))
        entry = next((m for m in served if m.get("id") == model), {})
        max_len = entry.get("max_model_len")
        if max_len and context_limit:
            if context_limit > max_len:
                out.append(("fail", "context", f"SOAPFL_CONTEXT_LIMIT={context_limit} exceeds the server's "
                                               f"max_model_len={max_len}; requests will be rejected"))
            else:
                out.append(("ok", "context", f"SOAPFL_CONTEXT_LIMIT={context_limit} <= max_model_len={max_len}"))
        elif max_len:
            out.append(("warn", "context", f"server max_model_len={max_len}; set SOAPFL_CONTEXT_LIMIT to it "
                                           f"(default assumed by the patch is 32768)"))
    if model and model in names and not (entry_has_len(served, model)):
        out += check_ollama(base_url, model, context_limit)
    if chat and model and model in names:
        try:
            reply = _http_json(base_url + "/chat/completions", {
                "model": model, "max_tokens": 64, "temperature": 0,
                "messages": [{"role": "user", "content": "Reply with the single word: ready"}]}, api_key,
                timeout=600)   # the first call loads the model into memory, which can take minutes
            text = (reply["choices"][0]["message"].get("content") or "").strip()
            if text:
                out.append(("ok", "chat", f"test completion works (reply: {text[:40]!r})"))
            else:
                out.append(("warn", "chat", "test completion returned an EMPTY reply. If this model 'thinks' before "
                            "answering, it may use up the token budget; try the extra_body setting in "
                            "configs/models.json (reasoning_effort / think) or a non-thinking model"))
        except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
            out.append(("fail", "chat", f"test completion failed: {exc}. If the model was still loading, run the same "
                                        f"command again (it is usually fast the second time)"))
    return out


def run_preflight(soapfl_dir: str, python: Optional[str] = None, defects4j_home: Optional[str] = None,
                  skip_endpoint: bool = False, skip_defects4j: bool = False) -> List[Check]:
    defects4j_home = defects4j_home or os.environ.get("DEFECTS4J_HOME")
    checks: List[Check] = []
    if not os.path.isdir(soapfl_dir):
        return [("fail", "soapfl", f"{soapfl_dir} does not exist: run scripts/setup_soapfl.sh")]
    checks.append(("ok", "soapfl", soapfl_dir))
    checks += check_patch_applied(soapfl_dir)
    checks += check_python_modules(python)
    if not skip_defects4j:
        checks += check_java()
        checks += check_defects4j(defects4j_home)
        checks += check_overlay(soapfl_dir, defects4j_home)
    checks += check_tiktoken_cache()
    if not skip_endpoint:
        base = os.environ.get("SOAPFL_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
        key = os.environ.get("SOAPFL_API_KEY") or os.environ.get("OPENAI_API_KEY") or "EMPTY"
        limit = os.environ.get("SOAPFL_CONTEXT_LIMIT")
        checks += check_endpoint(base, os.environ.get("SOAPFL_MODEL_NAME"), key,
                                 int(limit) if limit and limit.isdigit() else None)
    return checks


def format_checks(checks: List[Check]) -> str:
    icon = {"ok": "[ ok ]", "warn": "[warn]", "fail": "[FAIL]"}
    lines = [f"{icon[level]} {name}: {msg}" for level, name, msg in checks]
    fails = sum(1 for c in checks if c[0] == "fail")
    warns = sum(1 for c in checks if c[0] == "warn")
    lines.append("")
    lines.append(f"{fails} failure(s), {warns} warning(s)." + (" Fix the failures before running." if fails else ""))
    return "\n".join(lines)
