"""Command line: python -m fl_tools <preflight|list-bugs|run|score|funnel|mock> ..."""
import argparse
import os
import signal
import sys

from . import __version__
from .bugs import count_by_project, select_bugs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOAPFL = os.environ.get("SOAPFL_DIR") or os.path.join(ROOT, "external", "SoapFL")
DEFAULT_RESULTS = os.path.join(ROOT, "results")


def _add_selection(p: argparse.ArgumentParser) -> None:
    p.add_argument("--bugs", default="", help="e.g. Lang-1,Math-3,Chart-1:5,Time (default: all)")
    p.add_argument("--pilot", type=int, default=0, help="stratified sample of N bugs over the projects")
    p.add_argument("--sample-seed", type=int, default=0, help="seed of the pilot sample")
    p.add_argument("--exclude", default="", help="same syntax as --bugs")
    p.add_argument("--include-deprecated", action="store_true",
                   help="include the 7 IDs SoapFL's run_all.py skips (395 bugs instead of 388)")
    p.add_argument("--subset-of", type=int, default=0,
                   help="draw --pilot N from the stratified sample of this size (e.g. 100 = the baseline bugs)")
    p.add_argument("--dataset", choices=["d4j14", "d4j2new"], default="d4j14",
                   help="d4j14 = Defects4J 1.4.0 (SoapFL's 388 bugs, default); d4j2new = the 444 bugs Defects4J 2.0 added")


def _add_safety(p: argparse.ArgumentParser) -> None:
    """GPU-budget safeguards of the runner (see Runner)."""
    p.add_argument("--retry-failed", action="store_true",
                   help="also re-run bugs whose last attempt in this run failed for good (default: skip them)")
    p.add_argument("--tail-factor", type=float, default=3.0,
                   help="once every bug has started, stop a bug after this many times the 95th percentile of the "
                        "finished bugs' run time (0 = off; default 3)")
    p.add_argument("--tail-min", type=int, default=600, help="tail guard never stops a bug before this many seconds")
    p.add_argument("--breaker-rate", type=float, default=0.5,
                   help="stop the whole run when more than this share of the finished attempts failed (0 = off)")
    p.add_argument("--breaker-min", type=int, default=30, help="circuit breaker waits for this many finished attempts")


def _safety(args) -> dict:
    return {"retry_failed": args.retry_failed, "tail_factor": args.tail_factor, "tail_min": args.tail_min,
            "breaker_rate": args.breaker_rate, "breaker_min": args.breaker_min}


def _add_pipeline(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pipeline", choices=["soapfl", "hypodeduce", "classaug"], default="soapfl",
                   help="soapfl = baseline; hypodeduce = our re-implementation of HypoDeduce (ICSE-NIER 2026); "
                        "classaug = SoapFL plus the free class ranking (RQ1 / RQ2)")
    p.add_argument("--hd-hypotheses", type=int, default=None, help="HypoDeduce H (default 5, as in the paper)")
    p.add_argument("--hd-classes", type=int, default=None, help="HypoDeduce C, classes per hypothesis (default 5)")
    p.add_argument("--hd-methods", type=int, default=None,
                   help="HypoDeduce: max methods per (hypothesis, class), 0 = all (default 0)")
    p.add_argument("--hd-selection", default=None, help="HypoDeduce hypothesis selection: max | mean_top3")
    p.add_argument("--ca-k", type=int, default=None, help="classaug: heuristic top-K classes added (default 3)")
    p.add_argument("--ca-mode", choices=["always", "gated"], default=None,
                   help="classaug: always add (RQ1) or only when SoapFL's class is not the heuristic top-1 (RQ2)")
    p.add_argument("--ca-context", default=None,
                   help="classaug: failure-context folder (default reports/_failure_context in the repo)")


def _ca_args(args) -> dict:
    return {"k": args.ca_k, "mode": args.ca_mode, "context": args.ca_context}


def _hd_args(args) -> dict:
    return {"hypotheses": args.hd_hypotheses, "classes": args.hd_classes, "methods": args.hd_methods,
            "selection": args.hd_selection}


def _select(args):
    return select_bugs(args.bugs, args.pilot, args.sample_seed, args.exclude, args.include_deprecated,
                       subset_of=args.subset_of, dataset=args.dataset)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fl_tools", description="SoapFL with open models on Defects4J")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("preflight", help="check environment, Defects4J and the model endpoint")
    p.add_argument("--soapfl-dir", default=DEFAULT_SOAPFL)
    p.add_argument("--python", default=None, help="python of the SoapFL venv (default: current)")
    p.add_argument("--defects4j-home", default=None)
    p.add_argument("--skip-endpoint", action="store_true")
    p.add_argument("--skip-defects4j", action="store_true")
    p.add_argument("--dataset", choices=["d4j14", "d4j2new"], default="d4j14")

    p = sub.add_parser("list-bugs", help="print the selected bugs and per-project counts")
    _add_selection(p)

    p = sub.add_parser("run", help="run SoapFL over the selected bugs (resumable)")
    _add_selection(p)
    p.add_argument("--name", required=True, help="run name = folder under results/. One name per model/config")
    p.add_argument("--soapfl-dir", default=DEFAULT_SOAPFL)
    p.add_argument("--results-dir", default=DEFAULT_RESULTS)
    p.add_argument("--python", default=None, help="python of the SoapFL venv (default: current)")
    p.add_argument("--defects4j-home", default=None)
    p.add_argument("--config", default="Default", help="SoapFL config name (default: Default)")
    p.add_argument("--model", default="LOCAL")
    p.add_argument("--strict", action="store_true",
                   help="paper-faithful parsing: a malformed score crashes the bug like in original SoapFL")
    p.add_argument("--seed", type=int, default=0, help="SOAPFL_SEED for test sampling")
    p.add_argument("--jobs", type=int, default=1, help="bugs in parallel (each uses the same LLM server)")
    p.add_argument("--timeout", type=int, default=3600, help="seconds per bug attempt (0 = none)")
    p.add_argument("--retries", type=int, default=1, help="extra attempts for transient errors")
    p.add_argument("--allow-meta-change", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="show what would run, do nothing")
    p.add_argument("--skip-preflight", action="store_true")
    _add_pipeline(p)
    _add_safety(p)

    p = sub.add_parser("score", help="Top-1/3/5 table for a run")
    p.add_argument("run_dir")
    p.add_argument("--soapfl-dir", default=DEFAULT_SOAPFL)
    p.add_argument("--reference-csv", default=None, help="SoapFL-format CSV to compare bug by bug")
    p.add_argument("--no-write", action="store_true")

    p = sub.add_parser("funnel", help="where in the pipeline bugs are lost")
    p.add_argument("run_dir")
    p.add_argument("--soapfl-dir", default=DEFAULT_SOAPFL)
    p.add_argument("--no-write", action="store_true")

    p = sub.add_parser("ties", help="RQ3 step 0: how much does the ranking depend on score ties (offline)")
    p.add_argument("run_dir")
    p.add_argument("--draws", type=int, default=2000, help="random tie orders for the spread")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--no-write", action="store_true")

    p = sub.add_parser("models", help="list model presets and what is installed in Ollama")
    p.add_argument("--presets", default=None)

    p = sub.add_parser("experiment", help="ONE COMMAND per model: prepare Ollama, run, score, funnel, export")
    p.add_argument("model", help="preset name from configs/models.json (see `models`)")
    p.add_argument("--n", type=int, default=100, help="number of bugs (stratified sample, same bugs every time)")
    p.add_argument("--select", default="", help="explicit bugs instead of a sample, e.g. Lang-1,Math-3")
    p.add_argument("--subset-of", type=int, default=0,
                   help="take the --n bugs from the stratified sample of this size (100 = the baseline bugs)")
    p.add_argument("--dataset", choices=["d4j14", "d4j2new"], default="d4j14",
                   help="d4j14 = Defects4J 1.4.0 (default); d4j2new = the 444 bugs Defects4J 2.0 added")
    p.add_argument("--jobs", type=int, default=2)
    p.add_argument("--name", default=None, help="run name (default: run<N>-<model>)")
    p.add_argument("--tag", default=None, help="exact Ollama tag if several are installed")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--sample-seed", type=int, default=0)
    p.add_argument("--soapfl-dir", default=DEFAULT_SOAPFL)
    p.add_argument("--results-dir", default=DEFAULT_RESULTS)
    p.add_argument("--reports-dir", default=os.path.join(ROOT, "reports"))
    p.add_argument("--python", default=None)
    p.add_argument("--defects4j-home", default=None)
    p.add_argument("--timeout", type=int, default=None, help="seconds per bug attempt (default 3600)")
    p.add_argument("--skip-preflight", action="store_true")
    p.add_argument("--presets", default=None)
    _add_pipeline(p)
    _add_safety(p)

    p = sub.add_parser("select", help="RQ3: replay final-selection strategies on a finished run's candidate lists")
    p.add_argument("run_dir", nargs="?", default="")
    p.add_argument("--selector", default="S0,S0r,S1,S1-body", help="comma list; see `select --list`")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--draws", type=int, default=2000, help="random tie orders for the S0r expectation")
    p.add_argument("--split", default=None, help="dev/test split file (default configs/selection_split.json; 'none' = off)")
    p.add_argument("--out-root", default=None, help="where to write <run>-sel-<selector>/ (default: next to the run)")
    p.add_argument("--no-write", action="store_true")
    p.add_argument("--list", action="store_true", help="list the selectors and exit")
    p.add_argument("--reveal-test", action="store_true",
                   help="also report the test part of the split (only once the choices are frozen on dev)")
    p.add_argument("--judge-model", default=None,
                   help="model for S5/S2 (default: the source run's SOAPFL_MODEL_NAME from run_meta.json)")
    p.add_argument("--k", type=int, default=8, help="max candidates the judge sees per bug (default 8)")
    p.add_argument("--shortlist", choices=["top-tie", "top-k"], default="top-tie",
                   help="top-tie = the tied top group (SoapFL); top-k = K best raw scores across tiers (HypoDeduce)")
    p.add_argument("--cache", default=os.path.join(DEFAULT_RESULTS, "judge_cache.jsonl"),
                   help="judge answer cache (re-runs never repeat a call)")
    p.add_argument("--jobs", type=int, default=1, help="bugs judged in parallel (1 for Ollama; more on vLLM)")
    p.add_argument("--call-timeout", type=float, default=600.0,
                   help="seconds one judge question may take before it is given up (2 retries; default 600). "
                        "A judge answer is 1-2 tokens, so on vLLM 120 is plenty; csc/submit_select.sh passes 120")
    p.add_argument("--agent-steps", type=int, default=6, help="S8b: max tool calls per investigation (default 6)")
    p.add_argument("--agent-protocol", choices=["native", "json"], default="native",
                   help="S8b: native tool calls, or one JSON action per turn (for endpoints without tools)")
    p.add_argument("--context-dir", default=None,
                   help="failure-context folder (default: _failure_context next to the run folder)")
    p.add_argument("--check-tools", action="store_true",
                   help="only check whether the endpoint returns native tool calls (S8b) and exit")
    p.add_argument("--check-logprobs", action="store_true",
                   help="only check whether the endpoint returns log-probabilities (needed for S2) and exit; "
                        "give the run folder too so the run's model is used")

    p = sub.add_parser("context", help="export the failure context (failing tests, stack traces, coverage, "
                                       "test code) of the bugs of finished runs; CPU only, resumable")
    p.add_argument("run_dirs", nargs="+", help="run folders (reports/<run> or results/<run>): their bugs and candidate classes")
    p.add_argument("--jobs", type=int, default=2, help="bugs in parallel (each runs Defects4J tests)")
    p.add_argument("--max-tests", type=int, default=3, help="failing tests per bug (the total is recorded)")
    p.add_argument("--bugs", default="", help="only these bugs, e.g. Lang-1,Math-3")
    p.add_argument("--part", choices=["dev", "test", "all"], default="all",
                   help="only the bugs of this part of the selection split")
    p.add_argument("--soapfl-dir", default=DEFAULT_SOAPFL)
    p.add_argument("--results-dir", default=DEFAULT_RESULTS)
    p.add_argument("--reports-dir", default=os.path.join(ROOT, "reports"),
                   help="also copy the files to <reports>/_failure_context ('none' = do not copy)")

    p = sub.add_parser("gate", help="B: score confidence-gated escalation policies offline from existing "
                                    "selector replays (no model calls)")
    p.add_argument("run_dir")
    p.add_argument("--ladder", default="S6,S5,S8a,S8b",
                   help="selectors in escalation order; every ordered sub-ladder is scored (default S6,S5,S8a,S8b)")
    p.add_argument("--margin", type=float, default=0.5, help="S2/S8a-lp confidence: expected-score gap of the top two")
    p.add_argument("--split", default=None)
    p.add_argument("--reveal-test", action="store_true")
    p.add_argument("--out-root", default=None)
    p.add_argument("--no-write", action="store_true")

    p = sub.add_parser("compare", help="two runs on their common bugs: Top-N, McNemar test, cost")
    p.add_argument("run_a")
    p.add_argument("run_b")
    p.add_argument("--soapfl-dir", default=DEFAULT_SOAPFL)
    p.add_argument("--out", default=None, help="also write the table to this markdown file")

    p = sub.add_parser("export", help="copy summaries/results of a run (no checkouts) to a folder")
    p.add_argument("run_dir")
    p.add_argument("--dest", default=None, help="default: reports/<run name> in the repo")
    p.add_argument("--no-logs", action="store_true")

    p = sub.add_parser("mock", help="OpenAI-compatible mock server for offline testing")
    p.add_argument("rest", nargs=argparse.REMAINDER)
    return parser


def _raise_interrupt(signum, frame):
    raise KeyboardInterrupt(f"signal {signum}")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["mock"]:
        # argparse.REMAINDER does not accept options right after the subcommand (`mock --port 8000`),
        # so the mock server's own options are passed through untouched
        from . import mock_server
        sys.argv = ["fl_tools.mock_server"] + argv[1:]
        return mock_server.main() or 0
    args = build_parser().parse_args(argv)

    if args.cmd == "mock":
        from . import mock_server
        sys.argv = ["fl_tools.mock_server"] + args.rest
        return mock_server.main() or 0

    if args.cmd == "models":
        from .models import ModelError, installed_models, load_presets, resolve_tag, variant_name, variant_num_ctx
        presets = load_presets(args.presets)
        base_url = os.environ.get("SOAPFL_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
        installed = []
        if base_url:
            try:
                installed = installed_models(base_url)
            except ModelError as exc:
                print(f"cannot list installed models: {exc}", file=sys.stderr)
        print(f"installed in Ollama: {', '.join(installed) or '(unknown)'}\n")
        for key, p in presets.items():
            line = f"{key:12s} family {p.family}, context {p.num_ctx}"
            try:
                tag = resolve_tag(p, installed)
                ready = base_url and variant_num_ctx(base_url, variant_name(tag, p.num_ctx)) == p.num_ctx
                line += f" -> {tag}; variant " + ("ready" if ready else "will be created automatically")
            except ModelError as exc:
                line += f" -> NOT AVAILABLE ({exc})"
            print(line + (f"\n{'':12s} {p.note}" if p.note else ""))
        return 0

    if args.cmd == "experiment":
        from .experiment import run_experiment
        return run_experiment(args.model, n=args.n, select=args.select, jobs=args.jobs, name=args.name,
                              tag=args.tag, seed=args.seed, sample_seed=args.sample_seed,
                              soapfl_dir=args.soapfl_dir, results_dir=args.results_dir,
                              reports_dir=args.reports_dir, python=args.python,
                              defects4j_home=args.defects4j_home, timeout=args.timeout,
                              skip_preflight=args.skip_preflight, presets_path=args.presets,
                              pipeline=args.pipeline, hd=_hd_args(args), ca=_ca_args(args), subset_of=args.subset_of,
                              dataset=args.dataset, safety=_safety(args))

    if args.cmd == "list-bugs":
        bugs = _select(args)
        print(", ".join(b.name for b in bugs))
        print(f"\n{len(bugs)} bugs: " + ", ".join(f"{k} {v}" for k, v in count_by_project(bugs).items()))
        return 0

    if args.cmd == "preflight":
        from .preflight import format_checks, run_preflight
        checks = run_preflight(args.soapfl_dir, args.python, args.defects4j_home,
                               args.skip_endpoint, args.skip_defects4j, dataset=args.dataset)
        print(format_checks(checks))
        return 1 if any(c[0] == "fail" for c in checks) else 0

    if args.cmd == "run":
        from .runner import MetaMismatch, Runner
        # Stop cleanly on SIGTERM (Slurm time limit, `kill`) and on SIGINT even when started in the
        # background of a non-interactive shell, where SIGINT is ignored by default.
        signal.signal(signal.SIGINT, signal.default_int_handler)
        signal.signal(signal.SIGTERM, _raise_interrupt)
        bugs = _select(args)
        if not bugs:
            print("no bugs selected", file=sys.stderr)
            return 2
        print(f"{len(bugs)} bugs: " + ", ".join(f"{k} {v}" for k, v in count_by_project(bugs).items()))
        if args.dry_run:
            print(", ".join(b.name for b in bugs))
            return 0
        if not args.skip_preflight:
            from .preflight import format_checks, run_preflight
            checks = run_preflight(args.soapfl_dir, args.python, args.defects4j_home, dataset=args.dataset)
            if any(c[0] == "fail" for c in checks):
                print(format_checks(checks), file=sys.stderr)
                print("preflight failed (use --skip-preflight to override)", file=sys.stderr)
                return 1
        if args.pipeline == "hypodeduce":
            from .experiment import configure_hypodeduce
            print("HypoDeduce: " + ", ".join(f"{k}={v}" for k, v in configure_hypodeduce(_hd_args(args)).items()))
        if args.pipeline == "classaug":
            from .experiment import configure_classaug
            print("class augmentation: " + ", ".join(f"{k}={v}" for k, v in configure_classaug(_ca_args(args)).items()))
            if args.config == "Default":
                args.config = "HypoDeduce"
        runner = Runner(name=args.name, results_dir=args.results_dir, soapfl_dir=args.soapfl_dir,
                        pipeline=args.pipeline, config=args.config, model=args.model, lenient=not args.strict, seed=args.seed,
                        jobs=args.jobs, timeout=args.timeout, retries=args.retries, python=args.python,
                        defects4j_home=args.defects4j_home, allow_meta_change=args.allow_meta_change,
                        **_safety(args))
        try:
            summary = runner.run(bugs)
        except MetaMismatch as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            return 130
        print(f"done: {summary['status_counts']} (already finished: {summary['skipped_finished']}, "
              f"skipped earlier failures: {summary['skipped_failed']})")
        if summary.get("circuit_breaker"):
            print("STOPPED BY THE " + summary["circuit_breaker"], file=sys.stderr)
            return 3
        print(f"next: python -m fl_tools score {summary['out_dir']} && "
              f"python -m fl_tools funnel {summary['out_dir']}")
        return 0

    if args.cmd == "select":
        from .selection import agent, judges  # noqa: F401  (register S5, S2, S5+S2, S6, S8a, S8a-lp, S8b)
        from .selection import selectors as sel_registry
        from .selection.llm import JudgeClient, JudgeError, probe_logprobs, probe_tools
        if args.list:
            for name, sel in sel_registry.REGISTRY.items():
                print(f"{name:10s} {'[model calls] ' if sel.model_calls else ''}{sel.description}")
            return 0
        names = [n.strip() for n in args.selector.split(",") if n.strip()]
        model = args.judge_model
        if not model and args.run_dir and os.path.exists(os.path.join(args.run_dir, "run_meta.json")):
            import json
            meta = json.load(open(os.path.join(args.run_dir, "run_meta.json"), encoding="utf-8"))
            model = (meta.get("llm_env") or {}).get("SOAPFL_MODEL_NAME")
        model = model or os.environ.get("SOAPFL_MODEL_NAME")
        needs_model = args.check_logprobs or args.check_tools or any(n in sel_registry.REGISTRY and sel_registry.REGISTRY[n].model_calls
                                                 for n in names)
        client = None
        if needs_model:
            if not model:
                print("no judge model: give --judge-model or a run folder with run_meta.json", file=sys.stderr)
                return 2
            try:
                client = JudgeClient(model, cache_path=None if (args.check_logprobs or args.check_tools) else args.cache,
                                     timeout=args.call_timeout)
                if args.check_tools:
                    r = probe_tools(client)
                    print(f"endpoint {client.base_url}, model {model}: native tool calls "
                          f"{'SUPPORTED' if r['supported'] else 'NOT returned (S8b will use its JSON action protocol)'}")
                    print(f"tool calls {r['tool_calls']}; text {r['text']!r}")
                    if not args.check_logprobs:
                        return 0 if r["supported"] else 1
                if args.check_logprobs:
                    r = probe_logprobs(client)
                    print(f"endpoint {client.base_url}, model {model}: log-probabilities "
                          f"{'SUPPORTED' if r['supported'] else 'NOT returned (S2 and S5+S2 cannot run here)'}")
                    print(f"answer {r['answer']!r}; top tokens {r['top_logprobs']}")
                    return 0 if r["supported"] else 1
            except JudgeError as exc:
                print(exc, file=sys.stderr)
                return 2
        if not os.path.isdir(args.run_dir):
            print(f"no such run folder: {args.run_dir}", file=sys.stderr)
            return 2
        from .selection.replay import replay
        from .selection.split import DEFAULT_SPLIT
        split = None if (args.split or "").lower() == "none" else (args.split or DEFAULT_SPLIT)
        try:
            out = replay(args.run_dir, names, seed=args.seed, draws=args.draws, split_path=split,
                         out_root=args.out_root, write=not args.no_write, soapfl_dir=DEFAULT_SOAPFL,
                         reveal_test=args.reveal_test, client=client, k=args.k, shortlist=args.shortlist,
                         jobs=args.jobs, agent_steps=args.agent_steps, agent_protocol=args.agent_protocol,
                         context_dir=args.context_dir)
        except KeyError as exc:
            print(exc.args[0], file=sys.stderr)
            return 2
        except (JudgeError, ValueError) as exc:
            print(f"selection stopped: {exc}", file=sys.stderr)
            return 2
        print(out["markdown"])
        if client is not None:
            st = client.stats
            print(f"judge: {st['calls']} new calls, {st['cached']} from cache, "
                  f"{st['prompt_tokens'] + st['completion_tokens']} tokens, {st['seconds']:.0f} s")
        for path in out["written"]:
            print("wrote", path)
        return 0

    if args.cmd == "context":
        from .context import export_contexts
        only = {b.strip() for b in args.bugs.split(",") if b.strip()}
        if args.part != "all":
            from .selection.split import DEFAULT_SPLIT, load_split
            part = set(load_split(DEFAULT_SPLIT)[args.part])
            only = (only & part) if only else part
        for d in args.run_dirs:
            if not os.path.isdir(d):
                print(f"no such run folder: {d}", file=sys.stderr)
                return 2
        rows = export_contexts(args.run_dirs, args.soapfl_dir, args.results_dir,
                               None if args.reports_dir.lower() == "none" else args.reports_dir,
                               jobs=args.jobs, max_tests=args.max_tests, only=only or None)
        failed = [r for r in rows if not r["ok"]]
        print(f"done: {len(rows) - len(failed)} collected, {len(failed)} failed"
              + (f" ({', '.join(r['bug'] for r in failed)})" if failed else ""))
        return 1 if failed else 0

    if args.cmd == "gate":
        from .selection.gate import gate
        from .selection.split import DEFAULT_SPLIT
        if not os.path.isdir(args.run_dir):
            print(f"no such run folder: {args.run_dir}", file=sys.stderr)
            return 2
        split = None if (args.split or "").lower() == "none" else (args.split or DEFAULT_SPLIT)
        try:
            out = gate(args.run_dir, [n.strip() for n in args.ladder.split(",") if n.strip()], margin=args.margin,
                       split_path=split, reveal_test=args.reveal_test, out_root=args.out_root,
                       soapfl_dir=DEFAULT_SOAPFL, write=not args.no_write)
        except FileNotFoundError as exc:
            print(exc, file=sys.stderr)
            return 2
        print(out["markdown"])
        for path in out.get("written", []):
            print("wrote", path)
        return 0

    if args.cmd == "compare":
        from .compare import compare_runs, format_markdown
        for d in (args.run_a, args.run_b):
            if not os.path.isdir(d):
                print(f"no such run folder: {d}", file=sys.stderr)
                return 2
        md = format_markdown(compare_runs(args.run_a, args.run_b, args.soapfl_dir))
        print(md)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(md + "\n")
        return 0

    if args.cmd in ("score", "funnel", "export", "ties") and not os.path.isdir(args.run_dir):
        parent = os.path.dirname(os.path.abspath(args.run_dir)) or "."
        found = sorted(d for d in os.listdir(parent) if os.path.isdir(os.path.join(parent, d))) \
            if os.path.isdir(parent) else []
        print(f"no such run folder: {args.run_dir}\nRuns found in {parent}: {', '.join(found) or '(none)'}",
              file=sys.stderr)
        return 2

    if args.cmd == "score":
        from .score import score_run
        out = score_run(args.run_dir, args.soapfl_dir, args.reference_csv, write=not args.no_write)
        print(out["markdown"])
        if out["missing_truth"]:
            print(f"\nwarning: no ground truth for {len(out['missing_truth'])} bugs with output: "
                  f"{', '.join(out['missing_truth'][:10])}", file=sys.stderr)
        for path in out["written"]:
            print("wrote", path)
        return 0

    if args.cmd == "export":
        from .export import export_run
        run_dir = os.path.abspath(args.run_dir)
        dest = args.dest or os.path.join(ROOT, "reports", os.path.basename(run_dir.rstrip(os.sep)))
        copied = export_run(run_dir, dest, include_logs=not args.no_logs)
        print(f"copied {len(copied)} items to {dest}")
        return 0

    if args.cmd == "ties":
        from .ties import analyse_run as analyse_ties
        out = analyse_ties(args.run_dir, draws=args.draws, seed=args.seed, write=not args.no_write)
        print(out["markdown"])
        for path in out["written"]:
            print("wrote", path)
        return 0

    if args.cmd == "funnel":
        from .funnel import analyse_run
        out = analyse_run(args.run_dir, args.soapfl_dir, write=not args.no_write)
        print(out["markdown"])
        for path in out["written"]:
            print("wrote", path)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
