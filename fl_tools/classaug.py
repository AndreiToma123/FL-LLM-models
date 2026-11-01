"""RQ1 / RQ2: widen SoapFL's class step with a free class ranking from the failing tests (no model call).

SoapFL's model picks ONE suspicious class from the classes the failing tests executed; on our full CSC runs that
class is right in 68% (dataset 1) and 54% (dataset 2) of the bugs. The failure context (fl_tools context) ranks
the same classes without a model: on a failing test's stack first (shallower first), then name overlap with the
failing test class, then how many failing tests executed it, then how many of its methods they executed.
Adding the top-K of that ranking to SoapFL's choice raises class recall (K = 3: 68% -> 88%, 54% -> 74%).

  mode "always"  RQ1: review SoapFL's class plus the heuristic top-K classes in every bug.
  mode "gated"   RQ2: only when SoapFL's class is NOT the heuristic top-1 (SoapFL is right in 82% / 75% of the
                 agreeing bugs, but only in 42% / 32% of the disagreeing ones), add the top-K; else plain SoapFL.

SoapFL itself is not changed: `SearchSuspiciousClass.update_chat_env` is wrapped at start-up (like the HypoDeduce
plug-in). The later phases (method docs, method search, method review) already loop over all suspicious
classes, so the extra classes are reviewed with SoapFL's own prompts and ranked with SoapFL's own scores.
Everything about the bug comes from the failure context (buggy version and failing tests only).
"""
import json
import os
import re
import sys
from typing import Dict, List, Optional

MODES = ("always", "gated")
ENV_RANKING = "SOAPFL_CA_RANKING"     # JSON list: heuristic class ranking of this bug (written by the runner)
ENV_MODE = "SOAPFL_CA_MODE"
ENV_K = "SOAPFL_CA_K"


def outer_class(c: str) -> str:
    return c.split("$")[0]


def class_of_method(m: str) -> str:
    return outer_class(m.split("::")[0])


def _tokens(name: str) -> set:
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name.split(".")[-1])
    return {t.lower() for t in re.split(r"[^A-Za-z0-9]+", s) if len(t) > 2}


def rank_classes(ctx: Optional[dict]) -> List[str]:
    """Classes executed by the failing tests, most suspicious first (fixed key, no tuning)."""
    if not ctx:
        return []
    test_toks = set()
    for t in ctx.get("tests") or []:
        test_toks |= _tokens(t["name"].split("::")[0].replace("Test", ""))
    feats: Dict[str, dict] = {}
    for m, e in (ctx.get("methods") or {}).items():
        c = class_of_method(m)
        if c.endswith("Test") or ".test." in c:
            continue
        f = feats.setdefault(c, {"depth": None, "cov": 0, "nm": 0})
        d = e.get("stack_depth")
        if d is not None and (f["depth"] is None or d < f["depth"]):
            f["depth"] = d
        f["cov"] = max(f["cov"], e.get("failing_tests_covering") or 0)
        f["nm"] += 1

    def key(c):
        f = feats[c]
        return (f["depth"] is not None, -(f["depth"] or 0), len(_tokens(c) & test_toks), f["cov"], f["nm"], c)
    return sorted(feats, key=key, reverse=True)


def decide(chosen: List[str], ranking: List[str], available, mode: str, k: int) -> dict:
    """Which classes to add. `available` = the classes SoapFL offered to its model (classes_dict)."""
    chosen_set = {outer_class(c) for c in chosen}
    top1 = ranking[0] if ranking else None
    agree = top1 is not None and top1 in chosen_set
    out = {"mode": mode, "k": k, "chosen": list(chosen), "heuristic_top": ranking[:k], "agree": agree, "added": []}
    if not ranking or (mode == "gated" and agree):
        return out
    for c in ranking[:k]:
        if c not in chosen_set and c in available:
            out["added"].append(c)
    return out


def install(phase_module) -> None:
    """Wrap SearchSuspiciousClass so that its conclusion is widened as configured in the environment."""
    ranking = json.loads(os.environ.get(ENV_RANKING) or "[]")
    mode = os.environ.get(ENV_MODE, "always")
    k = int(os.environ.get(ENV_K, "3"))
    original = phase_module.SearchSuspiciousClass.update_chat_env

    def update_chat_env(self, chat_env):
        chat_env = original(self, chat_env)
        chosen = list(chat_env.env_dict.get("suspicious_classes") or [])
        info = decide(chosen, ranking, chat_env.env_dict.get("classes_dict") or {}, mode, k)
        if info["added"]:
            chat_env.env_dict["suspicious_classes"] = chosen + info["added"]
            chat_env.res_dict["buggy_classes"] = chosen + info["added"]
        chat_env.res_dict.setdefault("class_augment", []).append(dict(info, test_suite=getattr(chat_env, "test_suite", None) and chat_env.test_suite.name))
        print(f"[class augment] mode {mode}, k {k}: SoapFL chose {chosen}; heuristic top {ranking[:k]}; "
              f"added {info['added']}")
        return chat_env
    phase_module.SearchSuspiciousClass.update_chat_env = update_chat_env


def main(argv=None) -> None:
    """Entry point started by the runner (cwd = SoapFL folder): wrap the phase, then run SoapFL's run.py."""
    argv = list(sys.argv[1:] if argv is None else argv)
    soapfl_dir = os.environ.get("SOAPFL_DIR") or os.getcwd()
    if not os.path.exists(os.path.join(soapfl_dir, "run.py")):
        sys.exit(f"SoapFL not found in {soapfl_dir}")
    os.chdir(soapfl_dir)
    sys.path.insert(0, soapfl_dir)
    import chatdev.phase as phase_module
    install(phase_module)
    import run as soapfl_run
    sys.argv = [os.path.join(soapfl_dir, "run.py")] + argv
    soapfl_run.main()


if __name__ == "__main__":
    main()
