"""One command per model: prepare Ollama, check, run, score, funnel, export."""
import json
import os
import sys
from collections import Counter
from typing import Optional

from .bugs import count_by_project, select_bugs
from .export import export_run
from .funnel import analyse_run
from .ties import analyse_run as analyse_ties
from .models import (ModelError, apply_preset_env, ensure_variant, installed_models, load_presets,
                     resolve_tag)
from .preflight import format_checks, run_preflight
from .results import load_runs
from .runner import MetaMismatch, Runner
from .score import score_run


def run_experiment(model_key: str, *, n: int = 100, select: str = "", jobs: int = 2, name: Optional[str] = None,
                   tag: Optional[str] = None, seed: int = 0, sample_seed: int = 0, soapfl_dir: str,
                   results_dir: str, reports_dir: str, python: Optional[str] = None,
                   defects4j_home: Optional[str] = None, timeout: int = 3600, skip_preflight: bool = False,
                   presets_path: Optional[str] = None, pipeline: str = "soapfl", hd: Optional[dict] = None,
                   progress=print) -> int:
    try:
        presets = load_presets(presets_path)
        if model_key not in presets:
            progress(f"unknown model {model_key!r}. Available: {', '.join(presets)}")
            return 2
        preset = presets[model_key]
        base_url = os.environ.get("SOAPFL_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
        if not base_url:
            progress("SOAPFL_BASE_URL is not set (put it in .env, see configs/ollama.env)")
            return 2
        installed = installed_models(base_url)
        base_tag = resolve_tag(preset, installed, tag)
        progress(f"[1/5] model {model_key}: using installed {base_tag}")
        served = ensure_variant(base_url, base_tag, preset.num_ctx, progress)
    except ModelError as exc:
        progress(f"ERROR: {exc}")
        return 2
    env = apply_preset_env(preset, served)
    progress("      settings: " + ", ".join(f"{k}={v}" for k, v in env.items()))

    suffix = ""
    if pipeline == "hypodeduce":
        hd = configure_hypodeduce(hd or {})
        suffix = f"-hd-h{hd['hypotheses']}c{hd['classes']}"
        progress("      HypoDeduce: " + ", ".join(f"{k}={v}" for k, v in hd.items()))
    bugs = select_bugs(select, 0 if select else n, sample_seed)
    name = name or (f"run{len(bugs)}-{model_key}{suffix}" if not select else f"sel-{model_key}{suffix}")
    progress(f"[2/5] {len(bugs)} bugs ({', '.join(f'{k} {v}' for k, v in count_by_project(bugs).items())}); "
             f"run name {name}")

    if skip_preflight:
        progress("[3/5] preflight skipped")
    else:
        progress("[3/5] preflight (the first model call loads the model into memory and can take a few minutes) ...")
        checks = run_preflight(soapfl_dir, python, defects4j_home)
        progress(format_checks(checks))
        if any(c[0] == "fail" for c in checks):
            progress("preflight failed; fix the lines marked [FAIL] and run the same command again")
            return 1

    progress(f"[4/5] running (safe to interrupt; run the same command again to resume) ...")
    runner = Runner(name=name, results_dir=results_dir, soapfl_dir=soapfl_dir, model="LOCAL", lenient=True,
                    pipeline=pipeline, config="HypoDeduce" if pipeline == "hypodeduce" else "Default",
                    seed=seed, jobs=jobs, timeout=timeout, python=python, defects4j_home=defects4j_home,
                    progress=progress)
    try:
        summary = runner.run(bugs)
    except MetaMismatch as exc:
        progress(str(exc))
        return 1
    except KeyboardInterrupt:
        progress("interrupted; run the same command again to continue")
        return 130

    run_dir = summary["out_dir"]
    progress("[5/5] scoring and exporting")
    scored = score_run(run_dir, soapfl_dir)
    analyse_run(run_dir, soapfl_dir)
    analyse_ties(run_dir)
    dest = os.path.join(reports_dir, name)
    export_run(run_dir, dest)
    progress("\n" + scored["markdown"])

    latest = load_runs(run_dir)
    problems = Counter((r.get("error_class") or r.get("status")) for r in latest.values()
                       if r.get("status") != "ok")
    if problems:
        progress("\nbugs that did not finish normally: " + ", ".join(f"{k} {v}" for k, v in problems.most_common())
                 + "  (run the same command again to retry them)")
    progress(f"\nDONE. Summary files: {dest}\n(see summary.md and funnel.md there; commit and push the folder to keep them)")
    return 0


HD_DEFAULTS = {"hypotheses": 5, "classes": 5, "methods": 0, "selection": "max"}


def configure_hypodeduce(hd: dict) -> dict:
    """Fill HypoDeduce settings (paper: H = C = 5) and export them as SOAPFL_HD_* for the SoapFL processes."""
    from .hypodeduce.logic import SELECTION_RULES
    cfg = {k: (hd.get(k) if hd.get(k) is not None else v) for k, v in HD_DEFAULTS.items()}
    if cfg["selection"] not in SELECTION_RULES:
        raise ValueError(f"unknown selection rule {cfg['selection']!r}; use one of {SELECTION_RULES}")
    for key, value in cfg.items():
        os.environ[f"SOAPFL_HD_{key.upper()}"] = str(value)
    return cfg
