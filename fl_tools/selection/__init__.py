"""Final-selection framework (RQ3): re-rank the candidate lists that a finished run already stored.

Design: claude/SELECTION_FRAMEWORK_SPEC.md (project docs) and docs/SELECTION.md (repo).
Replay = no front-end re-run: a selector reads each bug's `result.json` (the scored candidate methods),
returns a new order, and the result is written as a normal run folder so `score`, `funnel`, `ties`
and `compare` work on it unchanged.

    python -m fl_tools select reports/run100-qwen25coder --selector S0,S0r,S1
"""
