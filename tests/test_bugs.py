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
