import pytest

from fl_tools.bugs import (all_bugs, bug_from_dirname, count_by_project, parse_bugs, select_bugs,
                           stratified_sample)


def test_full_counts():
    assert len(all_bugs()) == 388          # SoapFL's run_all.py list
    assert len(all_bugs(True)) == 395      # paper's Table I
    assert count_by_project(all_bugs())["Closure"] == 131


def test_parse():
    assert [b.name for b in parse_bugs("Lang-1,Chart-1:3")] == ["Lang-1", "Chart-1", "Chart-2", "Chart-3"]
    assert len(parse_bugs("Time")) == 26
    assert len(parse_bugs("Time-1,Time-1")) == 1


def test_parse_errors():
    with pytest.raises(ValueError):
        parse_bugs("Foo-1")
    with pytest.raises(ValueError):
        parse_bugs("Lang-66")
    assert parse_bugs("Lang-2")[0].id == 2   # deprecated ids may be requested explicitly


def test_dirname_roundtrip():
    b = parse_bugs("Math-7")[0]
    assert b.dirname == "d4j1.4.0-Math-7"
    assert bug_from_dirname(b.dirname) == b
    with pytest.raises(ValueError):
        bug_from_dirname("something")


@pytest.mark.parametrize("n", [6, 10, 30, 100])
def test_stratified(n):
    bugs = all_bugs()
    s1, s2 = stratified_sample(bugs, n, 1), stratified_sample(bugs, n, 1)
    assert s1 == s2 and len(s1) == n and len(set(s1)) == n
    assert len(count_by_project(s1)) == 6          # every project represented


def test_select():
    assert len(select_bugs(pilot=20)) == 20
    assert "Lang-1" not in [b.name for b in select_bugs("Lang", exclude="Lang-1")]


def test_dataset2_table_and_names():
    from fl_tools.bugs import DATASETS, defects4j_home
    bugs = all_bugs(dataset="d4j2new")
    assert len(bugs) == 444 and count_by_project(bugs)["JacksonDatabind"] == 112
    assert "Cli-6" not in {b.name for b in bugs}                     # deprecated in Defects4J 2.0
    b = parse_bugs("Closure-150", dataset="d4j2new")[0]
    assert b.dirname == "d4j2.0.0-Closure-150" and bug_from_dirname(b.dirname) == b
    with pytest.raises(ValueError):
        parse_bugs("Closure-10", dataset="d4j2new")                   # a 1.4.0 bug, not new in 2.0
    with pytest.raises(ValueError):
        parse_bugs("Jsoup-1")                                        # not in dataset 1
    assert DATASETS["d4j2new"]["version"] == "2.0.0"
    pilot = select_bugs(pilot=12, dataset="d4j2new")
    assert len(count_by_project(pilot)) == 12                        # one bug per project
    assert [b.name for b in select_bugs(pilot=100)][:3] == [b.name for b in select_bugs(pilot=100)][:3]
    assert count_by_project(select_bugs(pilot=100))["Mockito"] == 13  # dataset-1 sample unchanged (legacy rule)


def test_runner_uses_bug_version_and_dataset_home(tmp_path, monkeypatch):
    from fl_tools.runner import Runner
    home2 = tmp_path / "d4j2"
    (home2 / "framework" / "bin").mkdir(parents=True)
    monkeypatch.setenv("DEFECTS4J2_HOME", str(home2))
    monkeypatch.setenv("DEFECTS4J_HOME", str(tmp_path / "d4j1"))
    r = Runner(name="x", results_dir=str(tmp_path), soapfl_dir=str(tmp_path))
    b2 = parse_bugs("Jsoup-1", dataset="d4j2new")[0]
    cmd = r._command(b2)
    assert cmd[cmd.index("--version") + 1] == "2.0.0"
    env = r._env(b2)
    assert env["PATH"].startswith(str(home2)) and env["DEFECTS4J_HOME"] == str(home2)
    assert r._env(parse_bugs("Lang-1")[0])["DEFECTS4J_HOME"] == str(tmp_path / "d4j1")
    with pytest.raises(ValueError):
        r.run([b2, parse_bugs("Lang-1")[0]])
