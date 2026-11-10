# Where the results are stored

| What | Size | Where |
|---|---|---|
| Front-end runs `reports/runall-*` (per-bug result files, summaries, job notes) | 18-63 MB per run, no file over 20 MB | git |
| Judge summaries `reports/judge-vllm/*-selection.md/.json`, `*-gate.md/.json`, `*-judge-job.json` | under 1 MB in total | git |
| Judge per-bug replays `reports/judge-vllm/*-sel-*/` (needed to recompute the "+ judge" rows) | tens of thousands of files, 168 MB packed for the -r1 runs | NOT in git: GitHub release asset `judge-r1.tgz` (release `results-r1`), plus the PC and Roihu scratch |
| Transfer archives `*.tgz` | | NOT in git (`.gitignore`) |

Why: GitHub refuses any single file over 100 MB, and a git pull on Roihu would put every replay file into
projappl, which has a 150,000-file quota. A release asset may be up to 2 GB and is not part of the repository.

To restore the replays on another computer: download `judge-r1.tgz` from the release, then
`tar -xzf judge-r1.tgz -C reports` in the repository folder.
