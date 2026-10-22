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


def _add_pipeline(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pipeline", choices=["soapfl", "hypodeduce"], default="soapfl",
                   help="soapfl = baseline; hypodeduce = our re-implementation of HypoDeduce (ICSE-NIER 2026)")
    p.add_argument("--hd-hypotheses", type=int, default=None, help="HypoDeduce H (default 5, as in the paper)")
    p.add_argument("--hd-classes", type=int, default=None, help="HypoDeduce C, classes per hypothesis (default 5)")
    p.add_argument("--hd-methods", type=int, default=None,
                   help="HypoDeduce: max methods per (hypothesis, class), 0 = all (default 0)")
    p.add_argument("--hd-selection", default=None, help="HypoDeduce hypothesis selection: max | mean_top3")


def _hd_args(args) -> dict:
    return {"hypotheses": args.hd_hypotheses, "classes": args.hd_classes, "methods": args.hd_methods,
            "selection": args.hd_selection}


def _select(args):
    return select_bugs(args.bugs, args.pilot, args.sample_seed, args.exclude, args.include_deprecated)


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
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--skip-preflight", action="store_true")
    p.add_argument("--presets", default=None)
    _add_pipeline(p)

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
                              pipeline=args.pipeline, hd=_hd_args(args))

    if args.cmd == "list-bugs":
        bugs = _select(args)
        print(", ".join(b.name for b in bugs))
        print(f"\n{len(bugs)} bugs: " + ", ".join(f"{k} {v}" for k, v in count_by_project(bugs).items()))
        return 0

    if args.cmd == "preflight":
        from .preflight import format_checks, run_preflight
        checks = run_preflight(args.soapfl_dir, args.python, args.defects4j_home,
                               args.skip_endpoint, args.skip_defects4j)
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
            checks = run_preflight(args.soapfl_dir, args.python, args.defects4j_home)
            if any(c[0] == "fail" for c in checks):
                print(format_checks(checks), file=sys.stderr)
                print("preflight failed (use --skip-preflight to override)", file=sys.stderr)
                return 1
        if args.pipeline == "hypodeduce":
            from .experiment import configure_hypodeduce
            print("HypoDeduce: " + ", ".join(f"{k}={v}" for k, v in configure_hypodeduce(_hd_args(args)).items()))
            if args.config == "Default":
                args.config = "HypoDeduce"
        runner = Runner(name=args.name, results_dir=args.results_dir, soapfl_dir=args.soapfl_dir,
                        pipeline=args.pipeline, config=args.config, model=args.model, lenient=not args.strict, seed=args.seed,
                        jobs=args.jobs, timeout=args.timeout, retries=args.retries, python=args.python,
                        defects4j_home=args.defects4j_home, allow_meta_change=args.allow_meta_change)
        try:
            summary = runner.run(bugs)
        except MetaMismatch as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            return 130
        print(f"done: {summary['status_counts']} (already finished: {summary['skipped_finished']})")
        print(f"next: python -m fl_tools score {summary['out_dir']} && "
              f"python -m fl_tools funnel {summary['out_dir']}")
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
