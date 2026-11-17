import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pandas as pd
import metrics as M
from streamlit.testing.v1 import AppTest

root = "/tmp/fakedata"
runs = M.find_runs(root)
assert len(runs) == 3, runs
# known-answer check on a tiny table: ranks 1, 3, 6, N/A -> top1=1, top3=2, top5=2, MRR=(1+1/3+1/6+0)/4
df = pd.DataFrame({"project": ["A"]*4, "bug_id": range(4), "status": ["ok"]*4, "method_rank": ["1","3","6","N/A"],
                   "llm_calls": [1,2,3,4], "prompt_tokens": [1]*4, "completion_tokens": [1]*4,
                   "total_tokens": [2]*4, "llm_seconds": [3600]*4, "wall_s": [7200]*4})
df["rank"] = pd.to_numeric(df["method_rank"], errors="coerce")
s = M.summarize(df)
assert (s["Top-1"], s["Top-3"], s["Top-5"], s["not found"]) == (1, 2, 2, 1), s
assert abs(s["MRR"] - (1 + 1/3 + 1/6)/4) < 1e-9
assert s["LLM hours"] == 4 and s["wall hours"] == 8 and s["LLM calls (total)"] == 10
print(M.describe("runall-qwen25coder-ca3g-d4j2new-csc-r1"), M.describe("runall-qwen25coder-ca3-csc-r1"), M.describe("runall-qwen25coder-csc-r1"))
print(M.summary_table(runs)[["run", "bugs", "Top-1", "Top-3", "Top-5", "MRR"]].to_string())
assert len(M.read_storage_log(root + "/storage-log.tsv")) == 2

os.environ["THESIS_DATA"] = root
at = AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "app.py"), default_timeout=30).run()
assert not at.exception, at.exception
assert len(at.tabs) == 5
at.selectbox[0].select("runall-qwen25coder-ca3g-csc-r1").run()
assert not at.exception, at.exception
os.environ["THESIS_DATA"] = "/tmp/nonexistent"
at2 = AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "app.py")).run()
assert not at2.exception and len(at2.warning) == 1
print("ALL OK")
