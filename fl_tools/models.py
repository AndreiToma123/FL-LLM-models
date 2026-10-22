"""Model presets and automatic Ollama setup.

Why this exists: Ollama's OpenAI-compatible endpoint cannot set the context size per request, and an
Ollama model without ``num_ctx`` silently cuts long prompts. So for each preset we create (once) a variant
of the installed model that has the right ``num_ctx``, using Ollama's own HTTP API, and point SoapFL at it.
"""
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .preflight import parse_ollama_num_ctx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PRESETS_PATH = os.path.join(ROOT, "configs", "models.json")


class ModelError(RuntimeError):
    pass


@dataclass
class Preset:
    key: str
    family: str
    num_ctx: int = 16384
    max_completion_tokens: int = 3072
    extra_body: dict = field(default_factory=dict)
    note: str = ""


def load_presets(path: Optional[str] = None) -> Dict[str, Preset]:
    path = path or DEFAULT_PRESETS_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelError(f"cannot read model presets {path}: {exc}")
    presets = {}
    for key, spec in raw.items():
        if key.startswith("_"):
            continue
        presets[key] = Preset(key=key, family=spec["family"], num_ctx=int(spec.get("num_ctx", 16384)),
                              max_completion_tokens=int(spec.get("max_completion_tokens", 3072)),
                              extra_body=dict(spec.get("extra_body") or {}), note=spec.get("note", ""))
    return presets


def ollama_origin(base_url: str) -> str:
    origin = base_url.rstrip("/")
    return origin[:-3] if origin.endswith("/v1") else origin


def _call(origin: str, path: str, payload: Optional[dict] = None, timeout: float = 600.0) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(origin + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise ModelError(f"{path} -> HTTP {exc.code}: {detail}")
    except (urllib.error.URLError, OSError) as exc:
        raise ModelError(f"cannot reach {origin}{path}: {exc}")
    last = raw.strip().splitlines()[-1] if raw.strip() else "{}"   # streamed replies end with a status line
    try:
        return json.loads(last)
    except json.JSONDecodeError:
        return {}


def installed_models(base_url: str) -> List[str]:
    origin = ollama_origin(base_url)
    try:
        return sorted(m["name"] for m in _call(origin, "/api/tags", timeout=20).get("models", []))
    except ModelError:
        data = _call(origin, "/v1/models", timeout=20).get("data", [])   # non-Ollama server
        return sorted(m["id"] for m in data)


def resolve_tag(preset: Preset, installed: List[str], tag: Optional[str] = None) -> str:
    """Pick the installed model that belongs to the preset's family."""
    if tag:
        if tag in installed:
            return tag
        if f"{tag}:latest" in installed:
            return f"{tag}:latest"
        raise ModelError(f"model {tag!r} is not installed. Installed: {', '.join(installed) or '(none)'}")
    candidates = [m for m in installed if m == preset.family or m.startswith(preset.family + ":")]
    candidates = [m for m in candidates if not m.startswith("soapfl-")]
    if not candidates:
        raise ModelError(f"no installed model of family {preset.family!r}. Installed: "
                         f"{', '.join(installed) or '(none)'}. Install it with: ollama pull {preset.family}")
    if len(candidates) == 1:
        return candidates[0]
    latest = f"{preset.family}:latest"
    if latest in candidates:
        return latest
    raise ModelError(f"several tags of {preset.family!r} are installed ({', '.join(candidates)}); "
                     f"choose one with --tag")


def variant_name(base_tag: str, num_ctx: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", base_tag.lower()).strip("-")
    return f"soapfl-{slug}-c{num_ctx}"


def variant_num_ctx(base_url: str, name: str) -> Optional[int]:
    try:
        return parse_ollama_num_ctx(_call(ollama_origin(base_url), "/api/show", {"model": name, "name": name}, 30))
    except ModelError:
        return None


def ensure_variant(base_url: str, base_tag: str, num_ctx: int, progress=print) -> str:
    """Make sure a variant of base_tag with the given num_ctx exists; return the name to use for requests."""
    name = variant_name(base_tag, num_ctx)
    served = name + ":latest"
    if variant_num_ctx(base_url, name) == num_ctx:
        progress(f"model variant {served} already exists (num_ctx={num_ctx})")
        return served
    origin = ollama_origin(base_url)
    progress(f"creating model variant {served} from {base_tag} with num_ctx={num_ctx} ...")
    attempts = [
        ("/api/create", {"model": name, "from": base_tag, "parameters": {"num_ctx": num_ctx}, "stream": False}),
        ("/api/create", {"name": name, "modelfile": f"FROM {base_tag}\nPARAMETER num_ctx {num_ctx}\n",
                         "stream": False}),   # older Ollama versions
    ]
    errors = []
    for path, payload in attempts:
        try:
            _call(origin, path, payload)
        except ModelError as exc:
            errors.append(str(exc))
            continue
        if variant_num_ctx(base_url, name) == num_ctx:
            return served
    raise ModelError(
        "could not create the model variant through Ollama's API (" + "; ".join(errors) + ").\n"
        f"Create it by hand (PowerShell) and run again:\n"
        f"  'FROM {base_tag}`nPARAMETER num_ctx {num_ctx}' | Set-Content Modelfile.tmp\n"
        f"  ollama create {name} -f Modelfile.tmp")


def apply_preset_env(preset: Preset, served_name: str, env=None) -> dict:
    """Set the SOAPFL_* variables for this model in `env` (default os.environ). Returns what was set."""
    env = os.environ if env is None else env
    values = {"SOAPFL_MODEL_NAME": served_name,
              "SOAPFL_CONTEXT_LIMIT": str(preset.num_ctx),
              "SOAPFL_MAX_COMPLETION_TOKENS": str(preset.max_completion_tokens)}
    env.update(values)
    if preset.extra_body:
        env["SOAPFL_EXTRA_BODY"] = json.dumps(preset.extra_body)
        values["SOAPFL_EXTRA_BODY"] = env["SOAPFL_EXTRA_BODY"]
    else:
        env.pop("SOAPFL_EXTRA_BODY", None)   # never inherit another model's setting from .env
    return values
