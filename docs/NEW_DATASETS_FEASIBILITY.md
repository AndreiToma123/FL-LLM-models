# GHRB and GitBug-Java: can our pipeline run on them? (feasibility, 2026-11-09)

Step 1 of the execution plan (section 15, update 2): read both benchmarks, list what is Defects4J-specific in our
pipeline, and say what has to change. Nothing was built yet; nothing in the frozen SoapFL path was changed.
Sources: the two repositories (cloned read-only on 2026-11-09: github.com/coinse/GHRB, github.com/gitbugactions/
gitbug-java), their papers (arXiv 2310.13229, 2402.02961), and SoapFL's code.

## 1. Why this is real work: where SoapFL depends on Defects4J

SoapFL never reads a project by itself; it calls the `defects4j` command-line tool:

| SoapFL needs | Defects4J command it runs | file |
|---|---|---|
| buggy and fixed source | `defects4j checkout -p P -v Nb/Nf -w dir` | `functions/d4j.py` |
| build | `defects4j compile` | `functions/d4j.py`, `extract_classes.py` |
| list of failing tests (Class::method) | `defects4j export -p tests.trigger` | `functions/d4j.py` |
| source / test / binary folders | `export -p dir.src.classes, dir.src.tests, dir.bin.classes, dir.bin.tests` | several |
| changed classes (for the answer key) | `export -p classes.modified` | `functions/d4j.py` |
| failing test output + stack trace | `defects4j test -n -t Class::method`, then reads the `failing_tests` file in Defects4J's format | `functions/d4j.py` |
| which classes and methods the test runs | `defects4j test ... -a -Djvmargs=-javaagent:classtracer.jar=...` | `functions/instrument.py` |

Our own failure-context export (`fl_tools/context.py`, needed by class widening and the judge's evidence) calls
the same SoapFL helpers, so it has the same dependency. Two helpful facts: (a) SoapFL skips the test run and the
instrumentation when their output files are already in its cache, and (b) the instrumentation agent works on any
JVM test run, not only Defects4J's.

## 2. The two benchmarks

| | GHRB | GitBug-Java |
|---|---|---|
| Size today | 134 bugs, 16 projects (1 deprecated); the 2023 paper had 76; FlexFL could reproduce 28 | 199 bugs, 55 projects |
| Dates | pull requests created 2021-07-10 to 2025-09-19 (from the bug files); 24 of 134 after Sep 2024 | fix commits 2023-01-03 to 2023-10-30 |
| Interface | `cli.py` with Defects4J-like commands: `checkout -p P -v 1b/1f -w dir`, `compile`, `test -t/-c/-s`, `export -p ...` (cp.test, dir.bin.classes, dir.bin.tests, ...) | `gitbug-java checkout BID DIR [--fixed]`, `gitbug-java run DIR` (replays the project's GitHub Actions workflow) |
| Runs in | its own Docker image, x86 only (`--platform linux/amd64`; Ubuntu 20.04, JDK 8/11/17, Maven; Gradle via wrappers) | Docker, about 130 GB (50 GB image + 80 GB offline dependencies); x86 not stated, built on x86 |
| Failing tests given as | test CLASSES only (`execution_result.valid_tests`), not test methods | per-test results of the workflow runs (`actions_runs`: class, name, result, message) |
| Answer key | `git diff` buggy vs fixed (commits in the bug file) | `bug_patch` diff in the bug file |
| Licence | **no licence file in the repository** | MIT |

Neither has a `defects4j` command, neither records which test METHODS fail in Defects4J's form, and both need
Docker on an x86 machine with internet access (Maven/Gradle download their dependencies).

## 3. The blocking fact: Roihu's GPU nodes

Our LLM runs happen on Roihu GPU nodes: ARM processors, Apptainer instead of Docker, and (not checked) probably no
internet. Neither benchmark's environment runs there. So the work must be split in two phases:

1. **Preparation on an x86 machine with Docker (for example the user's Windows PC), CPU only:** for each bug,
   check out buggy and fixed versions with the benchmark's own tool, build, find the failing test METHODS (run the
   failing test classes on the buggy version, keep the methods that fail there and pass on the fixed version), run
   each failing test once with SoapFL's classtracer agent, and write a per-bug "bundle": the two source trees, the
   SoapFL cache files (failing test output, stack trace, instrumentation logs, `test_failure.pkl`), our
   failure-context file, the answer key (methods changed by the fix, found by comparing method bodies), and a
   small JSON with the folder names SoapFL asks for.
2. **LLM run on Roihu, unchanged SoapFL:** a small stand-in `defects4j` script for these datasets only (put first on
   PATH by the runner, the same way the runner already switches between Defects4J 1.4 and 2.0) answers `export`
   from the JSON and `checkout` by copying the bundle's source tree, and stops with a clear error if SoapFL ever
   tries to compile or run a test (it should not, because the cache is complete).

This keeps the frozen SoapFL path untouched: only a new bug source (`--dataset ghrb` / `--dataset gitbug`) and the
stand-in tool are added.

## 4. Work and risks

| Piece | Effort (coder's working time) | Risk |
|---|---|---|
| stand-in `defects4j` + bundle reader + `--dataset` values + tests | about half a day | low |
| preparation harness for GHRB (its CLI already has checkout/compile/test) | 1-2 days | JUnit 5 projects (FlexFL reproduced only 28 of 76), Maven vs Gradle test filters, agent arguments through surefire / Gradle |
| preparation harness for GitBug-Java (its tool replays whole workflows; single-test runs with the agent must be added inside its containers) | 2-3 days | 130 GB of disk; single-test runs inside the replayed workflow; flaky tests |
| answer key from the fix diff | half a day | fixes that touch only non-method code (fields, imports) have no method answer and must be listed and left out |
| 10-bug pilot per set + hand check of 3 answer keys | half a day each | |

**Recommendation:** start with **GHRB** (Defects4J-like interface, smaller, fixes newer than GitBug-Java's) as soon as
the user decides the open points below; GitBug-Java second, only if GHRB works. Report bugs that cannot be prepared,
with the reason.

## 5. Decisions needed from the user before building

1. **GHRB has no licence.** The thesis dropped HypoDeduce partly because its code has no licence. Running GHRB's
   tool and data is using them, not copying them into our repository, but the two cases should be treated the same
   way in the thesis text. Options: use GHRB and say so; ask the GHRB authors; or use only GitBug-Java (MIT).
2. **Where phase 1 runs:** the PC with Docker (needs about 20-130 GB of disk and some hours of CPU time), or another
   x86 machine. Roihu's x86 CPU nodes have no Docker; whether Apptainer can run these images there was not checked.
3. **Dates:** all GitBug-Java fixes (2023) and 110 of the 134 GHRB fixes are before Qwen2.5-Coder's release (Sep
   2024), so neither set is "unseen by the model". Write "more recent than Defects4J", record each bug's date, and
   report GHRB's 24 post-Sep-2024 bugs separately if they can be prepared (too few for a test, but worth a line).
4. The time box for the coder's adaptation work per set.
