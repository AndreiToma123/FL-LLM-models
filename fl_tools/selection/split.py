"""Fixed dev/test split of the 100 baseline bugs (stratified by project). Choices are made on dev only."""
import json
import os
import random
from typing import Dict, List

from ..bugs import select_bugs

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_SPLIT = os.path.join(ROOT, "configs", "selection_split.json")
SPLIT_SEED = 20261024


def make_split(seed: int = SPLIT_SEED) -> Dict[str, List[str]]:
    """Half of each project's bugs (of the 100-bug baseline sample) to dev, the rest to test."""
    bugs = select_bugs("", 100, 0)
    by_project: Dict[str, List[str]] = {}
    for b in bugs:
        by_project.setdefault(b.project, []).append(b.name)
    rng = random.Random(seed)
    dev, test = [], []
    for project in sorted(by_project):
        names = sorted(by_project[project], key=lambda n: int(n.split("-")[1]))
        rng.shuffle(names)
        half = len(names) // 2
        # odd sizes: alternate which side gets the extra bug, so dev and test stay about 50/50
        if len(names) % 2 and len(dev) > len(test):
            half += 1
        test += names[:half]
        dev += names[half:]
    return {"dev": sorted(dev), "test": sorted(test)}


def load_split(path: str = DEFAULT_SPLIT) -> Dict[str, List[str]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {"dev": data["dev"], "test": data["test"]}


def write_split(path: str = DEFAULT_SPLIT, seed: int = SPLIT_SEED) -> Dict[str, List[str]]:
    split = make_split(seed)
    data = {"_comment": "Dev/test split of the 100 baseline bugs (stratified sample of 100, sample seed 0), "
                        "stratified by project, seed below. Selection choices (prompts, K, weights, which "
                        "selector) are made on dev only; test is reported once. Bugs outside the 100 "
                        "(e.g. other HypoDeduce samples) count as test.",
            "seed": seed, **split}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return split


def part_of(bug: str, split: Dict[str, List[str]]) -> str:
    return "dev" if bug in split["dev"] else "test"
