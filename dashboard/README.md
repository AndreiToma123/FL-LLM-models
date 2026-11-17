# Thesis hub (dashboard)

Shows the results of the runs as tables and charts on your own computer. It only READS small tables; it changes nothing.

## Start (Ubuntu)
    cd dashboard
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    streamlit run app.py

A page opens at http://localhost:8501 . Next time only `source .venv/bin/activate && streamlit run app.py`.

## Where the data comes from
Put the tables in `dashboard/data/` (or set `THESIS_DATA=/other/folder`). Any folder tree works: every
`per_bug.csv`, or any CSV with the same columns, is found automatically. Use the folders that
`finish_run.sh pack <run>` makes on Roihu (`small-tables/<run>/`), copied with the `rsync` line it prints.
The replay folders inside them show up as their own runs. `storage-log.tsv` from Roihu goes in the same folder.

## Tests
    python3 tests/make_fake.py /tmp/fakedata && python3 tests/test_all.py
