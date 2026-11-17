"""Thesis dashboard (local). Start:  streamlit run app.py
Reads small tables only (per_bug.csv per run, storage-log.tsv). Never changes anything."""
import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import metrics as M

st.set_page_config(page_title="Thesis hub", layout="wide")
st.title("Thesis hub")

default_dir = os.environ.get("THESIS_DATA", str(Path(__file__).parent / "data"))
data_dir = st.sidebar.text_input("Data folder (tables from Roihu / git)", default_dir)
runs = M.find_runs(data_dir)
st.sidebar.write(f"{len(runs)} runs found")
if st.sidebar.button("Reload"):
    st.cache_data.clear()

if not runs:
    st.warning(f"No per_bug.csv tables found under `{data_dir}`. Copy the `small-tables/<run>/` folders "
               "from Roihu there (finish_run.sh pack prints the command), or set THESIS_DATA.")
    st.stop()


@st.cache_data
def summary(paths):
    return M.summary_table(dict(paths))


@st.cache_data
def load(path):
    return M.load_run(path)


table = summary(tuple(sorted((k, str(v)) for k, v in runs.items())))

tab_over, tab_cmp, tab_bug, tab_cost, tab_store = st.tabs(
    ["Overview", "Compare runs", "Per bug", "Cost", "Storage"])

with tab_over:
    st.subheader("All runs")
    show = table[["run", "dataset", "pipeline", "bugs", "Top-1", "Top-3", "Top-5", "MRR",
                  "not found", "failed bugs"]]
    st.dataframe(show, hide_index=True, width="stretch",
                 column_config={"MRR": st.column_config.NumberColumn(format="%.3f")})
    st.caption("Top-k counts bugs whose faulty method is at rank k or better. Bugs where it was not found "
               "(rank N/A) count as misses in every column and as 0 in MRR. The denominator is every row "
               "of the run's per_bug.csv.")

with tab_cmp:
    st.subheader("Top-1 / Top-3 / Top-5 in percent")
    pick = st.multiselect("Runs", list(table["run"]), default=list(table["run"])[:6])
    sub = table[table["run"].isin(pick)]
    if len(sub):
        long = sub.melt(id_vars=["run"], value_vars=["Top-1 %", "Top-3 %", "Top-5 %"],
                        var_name="metric", value_name="percent")
        chart = alt.Chart(long).mark_bar().encode(
            x=alt.X("run:N", sort=None, title=None, axis=alt.Axis(labelAngle=-30)),
            xOffset="metric:N", y=alt.Y("percent:Q", title="% of bugs"),
            color="metric:N", tooltip=["run", "metric", alt.Tooltip("percent:Q", format=".1f")])
        st.altair_chart(chart, width="stretch")
        st.dataframe(sub[["run", "Top-1 %", "Top-3 %", "Top-5 %", "MRR"]], hide_index=True,
                     width="stretch")

with tab_bug:
    run = st.selectbox("Run", list(table["run"]))
    df = load(str(runs[run]))
    projects = sorted(df["project"].unique())
    chosen = st.multiselect("Project", projects, default=projects)
    only_miss = st.checkbox("Only bugs where the faulty method was not found")
    view = df[df["project"].isin(chosen)]
    if only_miss:
        view = view[view["rank"].isna()]
    st.write(f"{len(view)} bugs shown")
    st.dataframe(view.drop(columns=["rank"]), hide_index=True, width="stretch")
    st.download_button("Download this table (CSV)", view.drop(columns=["rank"]).to_csv(index=False),
                       file_name=f"{run}-filtered.csv")
    st.subheader("Results per project")
    per = view.groupby("project").agg(bugs=("bug_id", "count"),
                                      top1=("rank", lambda r: int((r <= 1).sum())),
                                      top5=("rank", lambda r: int((r <= 5).sum()))).reset_index()
    st.dataframe(per, hide_index=True, width="stretch")

with tab_cost:
    st.subheader("What each run used")
    st.dataframe(table[["run", "pipeline", "bugs", "LLM calls (total)", "calls per bug", "tokens (total)",
                        "tokens per bug", "LLM hours", "wall hours"]], hide_index=True,
                 width="stretch",
                 column_config={"calls per bug": st.column_config.NumberColumn(format="%.1f"),
                                "tokens per bug": st.column_config.NumberColumn(format="%.0f"),
                                "LLM hours": st.column_config.NumberColumn(format="%.2f"),
                                "wall hours": st.column_config.NumberColumn(format="%.2f")})
    st.caption("Calls and tokens come from per_bug.csv. GPU billing units (BU) are not in these tables: "
               "they come from the job logs (job_meta.json) and are not shown yet.")
    c = alt.Chart(table).mark_bar().encode(
        x=alt.X("run:N", sort=None, title=None, axis=alt.Axis(labelAngle=-30)),
        y=alt.Y("tokens per bug:Q"), tooltip=["run", alt.Tooltip("tokens per bug:Q", format=".0f")])
    st.altair_chart(c, width="stretch")

with tab_store:
    st.subheader("Roihu storage log")
    log_path = st.text_input("storage-log.tsv", str(Path(data_dir).expanduser() / "storage-log.tsv"))
    log = M.read_storage_log(log_path)
    if log.empty:
        st.info("No log yet. finish_run.sh check <label> writes it on Roihu; copy it here.")
    else:
        st.dataframe(log[["date", "label", "space", "files"]], hide_index=True, width="stretch")
        line = alt.Chart(log.reset_index()).mark_line(point=True).encode(
            x=alt.X("index:O", title="check number"), y=alt.Y("entries:Q", title="files + folders"),
            tooltip=["date", "label", "files"])
        limit = alt.Chart(pd.DataFrame({"y": [500000]})).mark_rule(color="red").encode(y="y:Q")
        warn = alt.Chart(pd.DataFrame({"y": [300000]})).mark_rule(color="orange", strokeDash=[4, 4]).encode(y="y:Q")
        st.altair_chart(line + limit + warn, width="stretch")
        st.caption("Red line: the 500,000 limit. Dashed line: 300,000, where packing runs should start.")
