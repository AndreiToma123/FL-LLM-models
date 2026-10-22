"""HypoDeduce phases, plugged into SoapFL's chat chain (imported inside the SoapFL process only).

Our re-implementation of the pipeline described in Le, Zheng, Kang, "Abductive Reasoning for
Neurosymbolic Fault Localization", ICSE-NIER 2026 (Sec. 3). Written from the paper; no code or prompts
from the authors' repository. The chain (fl_tools/hypodeduce/config/chain.json) is:

    TestBehaviorAnalysis        SoapFL's own phase, unchanged
    HypothesisGeneration        H root-cause hypotheses in one call                    (paper: step 1)
    HypothesisClassSearch       top-C covered classes for EACH hypothesis              (paper: step 2)
    MethodDocEnhancement        SoapFL's own phase, once per retained class
    HypothesisMethodSearch      SoapFL's related-method step, per (hypothesis, class)  (paper: step 3)
    HypothesisMethodReview      SoapFL's 1-10 method scoring, per supporting hypothesis
    HypothesisSelection         pick the most plausible hypothesis, rank methods       (paper: step 5)

Retention (paper: step 4): a class or method stays as long as at least one hypothesis keeps it.
Settings come from environment variables (recorded in run_meta.json by the runner):
    SOAPFL_HD_HYPOTHESES  H (default 5)        SOAPFL_HD_CLASSES  C (default 5)
    SOAPFL_HD_METHODS     max methods per (hypothesis, class), 0 = all the model names (default 0)
    SOAPFL_HD_SELECTION   max | mean_top3 (default max)
"""
import os
import re

from camel.local_llm import lenient, log_event, parse_score
from chatdev.chat_env import ChatEnv
from chatdev.phase import FindRelatedMethods, MethodReview, Phase
from functions.func import covered_classes_prompt, test_infos_prompt

from fl_tools.hypodeduce import logic

PHASES = ["HypothesisGeneration", "HypothesisClassSearch", "HypothesisMethodSearch",
          "HypothesisMethodReview", "HypothesisSelection"]


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def settings() -> dict:
    return {"hypotheses": max(1, _int_env("SOAPFL_HD_HYPOTHESES", 5)),
            "classes": max(1, _int_env("SOAPFL_HD_CLASSES", 5)),
            "methods": max(0, _int_env("SOAPFL_HD_METHODS", 0)),
            "selection": os.environ.get("SOAPFL_HD_SELECTION", "max") or "max"}


def state(chat_env: ChatEnv) -> dict:
    """Per-test-suite HypoDeduce state (SoapFL resets env_dict for every test suite)."""
    return chat_env.env_dict.setdefault("hd", {"hypotheses": [], "classes": {}, "methods": {},
                                               "support": {}, "scores": {}, "reasons": {}, "info": {}})


class _Asking:
    """Mixin: one model call with SoapFL's checkpointing, under a sub-name (resumable runs)."""

    def ask(self, chat_env, sub_name, chat_turn_limit, need_reflect) -> str:
        if not self.load_conclusion(chat_env, sub_name):
            self.seminar_conclusion = self.chatting(chat_env=chat_env, need_reflect=need_reflect,
                                                    assistant_role_name=self.assistant_role_name,
                                                    user_role_name=self.user_role_name,
                                                    phase_prompt=self.phase_prompt, phase_name=self.phase_name,
                                                    assistant_role_prompt=self.assistant_role_prompt,
                                                    user_role_prompt=self.user_role_prompt,
                                                    chat_turn_limit=chat_turn_limit,
                                                    placeholders=self.phase_env, model_type=self.model_type)
            self.save_conclusion(chat_env, sub_name)
        return self.seminar_conclusion or ""


class HypothesisGeneration(Phase):
    """Step 1: several competing root-cause hypotheses from the test-failure information only."""

    def update_phase_env(self, chat_env):
        test_infos = test_infos_prompt(chat_env.test_cases, self.model_type,
                                       test_output_tokens=chat_env.config.test_output_tokens)
        chat_env.env_dict["test_infos"] = test_infos
        self.phase_env.update({"test_suite": chat_env.test_suite.name,
                               "failed_tests": chat_env.env_dict["failed_tests"],
                               "test_infos": test_infos,
                               "test_behavior": chat_env.env_dict["test_behavior"],
                               "num_hypotheses": settings()["hypotheses"]})

    def update_chat_env(self, chat_env) -> ChatEnv:
        wanted = settings()["hypotheses"]
        text = self.seminar_conclusion or ""
        hyps = logic.parse_hypotheses(text, wanted)
        if not hyps:
            log_event("hd_hypotheses_unparsed", phase=self.phase_name, suite=chat_env.test_suite.name,
                      conclusion=text[:500])
            hyps = [text.strip()] if text.strip() else []
        st = state(chat_env)
        st["hypotheses"] = hyps
        chat_env.env_dict["test_failure_causes"] = "\n\n".join(f"Hypothesis {i + 1}: {h}" for i, h in enumerate(hyps))
        log_event("hd_hypotheses", suite=chat_env.test_suite.name, requested=wanted, parsed=len(hyps))
        return chat_env


class HypothesisClassSearch(_Asking, Phase):
    """Step 2: the C most suspicious covered classes for EACH hypothesis."""

    def update_phase_env(self, chat_env):   # filled per hypothesis in execute()
        pass

    def update_chat_env(self, chat_env) -> ChatEnv:
        return chat_env

    def execute(self, chat_env, chat_turn_limit, need_reflect) -> ChatEnv:
        st, cfg = state(chat_env), settings()
        env = chat_env.env_dict
        covered, classes_dict = covered_classes_prompt(env["d4j_version"], env["project_name"], env["bug_ID"],
                                                       env["directory"], env["cache_dir"], chat_env.test_suite,
                                                       self.model_type,
                                                       class_doc_tokens=chat_env.config.class_doc_tokens,
                                                       basement=chat_env.config.basement)
        env["classes_dict"] = classes_dict
        union = []
        for k, hypothesis in enumerate(st["hypotheses"]):
            self.phase_env.update({"test_suite": chat_env.test_suite.name, "failed_tests": env["failed_tests"],
                                   "test_infos": env["test_infos"], "hypothesis": hypothesis,
                                   "covered_classes": covered, "num_classes": cfg["classes"]})
            answer = self.ask(chat_env, f"H{k + 1}", chat_turn_limit, need_reflect)
            classes = logic.parse_ranked_classes(answer, classes_dict, cfg["classes"])
            if not classes:
                log_event("no_valid_class", phase=self.phase_name, suite=chat_env.test_suite.name,
                          hypothesis=k + 1, n_covered=len(classes_dict), conclusion=answer[:500])
            st["classes"][k] = classes
            union += [c for c in classes if c not in union]
        env["suspicious_classes"] = union
        chat_env.res_dict["buggy_classes"] = union
        log_event("hd_classes", suite=chat_env.test_suite.name,
                  classes={str(k + 1): v for k, v in st["classes"].items()})
        return chat_env


class HypothesisMethodSearch(_Asking, FindRelatedMethods):
    """Step 3: SoapFL's related-method selection, asked once per (hypothesis, class of that hypothesis)."""

    def execute(self, chat_env, chat_turn_limit, need_reflect) -> ChatEnv:
        st, cfg = state(chat_env), settings()
        env = chat_env.env_dict
        per_hypothesis = {}
        for k, hypothesis in enumerate(st["hypotheses"]):
            per_hypothesis[k] = {}
            for cls in st["classes"].get(k, []):
                java_class = env["classes_dict"][cls]
                if java_class.methods == {}:
                    continue
                env["test_failure_causes"] = hypothesis       # the prompt's "Possible Causes" = this hypothesis
                self.update_phase_env(chat_env, cls)
                answer = self.ask(chat_env, f"H{k + 1}_{cls}", chat_turn_limit, need_reflect)
                mentioned = [m.replace(" ", "") for m in re.findall(r"((?:\w+\.)+[\w\$]+::.+?\(.*?\))", answer)]
                src_ids = {java_class.methods[m].src_id for m in java_class.methods}
                kept = []
                for m in mentioned:
                    if m in src_ids and m not in kept:
                        kept.append(m)
                if cfg["methods"]:
                    kept = kept[:cfg["methods"]]
                if not kept:
                    log_event("no_valid_method", phase=self.phase_name, suite=chat_env.test_suite.name,
                              cls=cls, hypothesis=k + 1, n_mentioned=len(mentioned), n_in_class=len(src_ids),
                              conclusion=answer[:500])
                per_hypothesis[k][cls] = kept
        union, support = logic.retain(per_hypothesis)
        env["suspicious_methods"] = union
        st["methods"], st["support"] = per_hypothesis, support
        log_event("hd_methods", suite=chat_env.test_suite.name, n_methods=sum(len(v) for v in union.values()),
                  n_pairs=sum(len(v) for v in support.values()))
        return chat_env


class HypothesisMethodReview(_Asking, MethodReview):
    """Score each retained method (1-10, SoapFL's prompt) against every hypothesis that kept it."""

    def execute(self, chat_env, chat_turn_limit, need_reflect) -> ChatEnv:
        st = state(chat_env)
        env = chat_env.env_dict
        for cls, methods in env["suspicious_methods"].items():
            for method in methods:
                for k in st["support"].get(method, []):
                    env["test_failure_causes"] = st["hypotheses"][k]
                    self.update_phase_env(chat_env, cls, method)
                    answer = self.ask(chat_env, f"H{k + 1}_{method}", chat_turn_limit, need_reflect)
                    conclusion = answer.strip('"')
                    score = parse_score(conclusion)
                    if score is None:
                        log_event("score_unparsed", phase=self.phase_name, suite=chat_env.test_suite.name,
                                  method=method, hypothesis=k + 1, conclusion=conclusion[:500])
                        if not lenient():
                            raise ValueError(f"Invalid Method Review Conclusion (HypothesisMethodReview). {conclusion}")
                        score = 0
                    st["scores"][(method, k)] = score
                    st["reasons"][(method, k)] = conclusion
                    st["info"][method] = {k2: self.phase_env[k2] for k2 in
                                          ("method_code", "method_doc", "class_name", "class_doc", "test_suite")}
        return chat_env


class HypothesisSelection(Phase):
    """Step 5: choose the most plausible hypothesis and produce the ranked list (no model call)."""

    def update_phase_env(self, chat_env):
        pass

    def update_chat_env(self, chat_env) -> ChatEnv:
        return chat_env

    def execute(self, chat_env, chat_turn_limit, need_reflect) -> ChatEnv:
        st, cfg = state(chat_env), settings()
        hyps, scores, support = st["hypotheses"], st["scores"], st["support"]
        selected, plaus = logic.select_hypothesis(len(hyps), scores, cfg["selection"])
        reviewed = []
        for methods in chat_env.env_dict["suspicious_methods"].values():
            reviewed += [m for m in methods if m in st["info"] and m not in reviewed]
        res = chat_env.res_dict
        by_name = {m["method_name"]: m for m in res["buggy_methods"]}
        for method, key in logic.final_order(reviewed, selected, support, scores):
            own = {k: scores[(method, k)] for k in support.get(method, []) if (method, k) in scores}
            used = selected if key[0] == 1 else max(own, key=lambda k: (own[k], -k))
            info = st["info"][method]
            entry = {"method_name": method, **info,
                     "test_failure_causes": hyps[used], "score": key[1], "reason": st["reasons"][(method, used)],
                     "hypothesis": used + 1, "selected_hypothesis": key[0] == 1,
                     "support": [k + 1 for k in support.get(method, [])],
                     "scores_by_hypothesis": {str(k + 1): s for k, s in own.items()},
                     "rank_key": [key[0], key[1]]}
            old = by_name.get(method)
            if old is None:
                res["buggy_methods"].append(entry)
                by_name[method] = entry
            elif tuple(entry["rank_key"]) > tuple(old.get("rank_key", [0, old.get("score", 0)])):
                old.update(entry)      # keep the best evidence across test suites
            res["buggy_codes"].setdefault(method, {"method_name": method, "method_code": info["method_code"],
                                                   "method_doc": info["method_doc"]})
        res["buggy_methods"] = sorted(res["buggy_methods"],
                                      key=lambda m: tuple(m.get("rank_key", [0, m.get("score", 0)])), reverse=True)
        res.setdefault("hypodeduce", []).append({
            "test_suite": chat_env.test_suite.name, "settings": cfg,
            "hypotheses": hyps, "selected": None if selected is None else selected + 1,
            "plausibility": {str(k + 1): list(v) for k, v in plaus.items()},
            "classes": {str(k + 1): v for k, v in st["classes"].items()},
            "methods": {str(k + 1): v for k, v in st["methods"].items()},
        })
        log_event("hd_selection", suite=chat_env.test_suite.name,
                  selected=None if selected is None else selected + 1, n_hypotheses=len(hyps),
                  n_ranked=len(reviewed))
        return chat_env
