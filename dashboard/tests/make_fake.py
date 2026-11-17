"""Writes fake tables with the real column names (for testing only)."""
import random, sys
from pathlib import Path
root = Path(sys.argv[1]); random.seed(1)
cols = "project,bug_id,status,has_result,has_truth,method_rank,true_class,recall_ratio,false_positive,llm_calls,prompt_tokens,completion_tokens,total_tokens,llm_seconds,wall_s"
for run, n in [("runall-qwen25coder-csc-r1", 40), ("runall-qwen25coder-ca3g-csc-r1", 40), ("runall-qwen25coder-d4j2new-csc-r1", 30)]:
    d = root / run; d.mkdir(parents=True, exist_ok=True)
    rows = [cols]
    for i in range(n):
        rk = random.choice(["N/A", "1", "1", "2", "3", "5", "9"])
        pt, ct = random.randint(5000, 20000), random.randint(800, 2500)
        rows.append(f"Chart,{i+1},ok,True,True,{rk},1,1|1,1,{random.randint(5,9)},{pt},{ct},{pt+ct},{random.uniform(8,25):.2f},{random.uniform(20,50):.1f}")
    (d / "per_bug.csv").write_text("\n".join(rows) + "\n")
(root / "storage-log.tsv").write_text("2026-11-17\tcleanup\t20G/250G\t174K/500K\n2026-11-18\tafter 14B\t24G/250G\t212K/500K\n")
