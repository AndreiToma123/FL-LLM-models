"""HypoDeduce, re-implemented from the paper (not from the authors' code).

Le, Zheng, Kang. "Abductive Reasoning for Neurosymbolic Fault Localization." ICSE-NIER 2026.
Runs as a plug-in chain inside the (unchanged) patched SoapFL, so fact extraction, the method-selection
and method-scoring prompts, checkpoints and result.json are shared with the SoapFL baseline.
Select it with `python -m fl_tools run --pipeline hypodeduce` (or `experiment --pipeline hypodeduce`).
Design decisions that the paper leaves open are listed in docs/HYPODEDUCE.md.
"""
