"""Reading the per-bug tables and computing the thesis numbers (no web code here, so it can be tested)."""
from pathlib import Path
import re
import pandas as pd

REQUIRED = {"project", "bug_id", "method_rank", "llm_calls", "prompt_tokens",
            "completion_tokens", "total_tokens", "llm_seconds", "wall_s"}


def find_runs(root):
    """Every CSV under `root` that has the per_bug columns. Name = run folder (per_bug.csv) or file name."""
    runs = {}
    root = Path(root).expanduser()
    if not root.exists():
        return runs
    for p in sorted(root.rglob("*.csv")):
        name = p.parent.name if p.name == "per_bug.csv" else p.stem
        try:
            head = pd.read_csv(p, nrows=0)
        except Exception:
            continue
        if REQUIRED <= set(head.columns):
            runs.setdefault(name, p)
    return runs


def load_run(path):
    df = pd.read_csv(path)
    df["rank"] = pd.to_numeric(df["method_rank"], errors="coerce")   # "N/A" -> NaN = not found
    return df


def describe(name):
    """Guess dataset and pipeline from the run name (naming used in the thesis runs)."""
    dataset = "Defects4J 2.0 new (d2)" if "d4j2new" in name else "Defects4J 1.4.0 (d1)"
    if "-ca3g-" in name or name.startswith("ca3g"):
        pipeline = "class widening, gated"
    elif "-ca3-" in name or name.startswith("ca3"):
        pipeline = "class widening, always"
    else:
        pipeline = "SoapFL"
    return dataset, pipeline


def summarize(df):
    n = len(df)
    r = df["rank"]
    out = {
        "bugs": n,
        "Top-1": int((r <= 1).sum()),
        "Top-3": int((r <= 3).sum()),
        "Top-5": int((r <= 5).sum()),
        "MRR": float((1.0 / r).fillna(0).mean()) if n else 0.0,
        "not found": int(r.isna().sum()),
        "LLM calls (total)": int(df["llm_calls"].sum()),
        "calls per bug": float(df["llm_calls"].mean()) if n else 0.0,
        "tokens (total)": int(df["total_tokens"].sum()),
        "tokens per bug": float(df["total_tokens"].mean()) if n else 0.0,
        "LLM hours": float(df["llm_seconds"].sum() / 3600),
        "wall hours": float(df["wall_s"].sum() / 3600),
        "failed bugs": int((df["status"] != "ok").sum()) if "status" in df else 0,
    }
    for k in (1, 3, 5):
        out[f"Top-{k} %"] = 100.0 * out[f"Top-{k}"] / n if n else 0.0
    return out


def summary_table(runs):
    rows = []
    for name, path in runs.items():
        s = summarize(load_run(path))
        dataset, pipeline = describe(name)
        rows.append({"run": name, "dataset": dataset, "pipeline": pipeline, **s})
    return pd.DataFrame(rows)


def read_storage_log(path):
    """storage-log.tsv: date, label, space (20G/250G), files (174K/500K)."""
    p = Path(path).expanduser()
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p, sep="\t", header=None, names=["date", "label", "space", "files"])
    df["entries"] = df["files"].map(_count)
    df["entries_max"] = df["files"].map(lambda s: _count(str(s).split("/")[-1]))
    return df


def _count(text):
    m = re.match(r"\s*([\d.]+)\s*([KM]?)", str(text).split("/")[0])
    if not m:
        return None
    return float(m.group(1)) * {"": 1, "K": 1e3, "M": 1e6}[m.group(2)]
