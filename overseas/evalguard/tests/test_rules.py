"""evalguard self-test.

Canon #424: an identification claim needs BOTH a positive control that can
reach 1.0 AND a negative control sitting at chance level. These tests are
the positive control (planted fixture must be caught) and the negative
control (clean fixture must stay silent).
"""
import pathlib, sys, pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from evalguard import cli

HERE = pathlib.Path(__file__).parent


def scan(name):
    return {r["eg_id"]: r["severity"] for r in cli.scan(str(HERE / name))}


def test_positive_control_planted_defects_are_caught():
    hits = scan("planted_eval.py")
    for eg in ("EG001", "EG002", "EG003", "EG004", "EG005", "EG006",
               "EG007", "EG008", "EG009", "EG011", "EG012", "EG013",
               "EG014", "EG015", "EG016"):
        assert eg in hits, f"{eg} missed a planted defect"


def test_negative_control_clean_fixture_is_silent():
    hits = scan("clean_eval.py")
    noisy = {k: v for k, v in hits.items() if v in ("blocker", "warn")}
    assert noisy == {}, f"false positives on clean code: {noisy}"


def test_dotted_names_survive_comment_stripping():
    """Regression: `_code_only` used to turn `requests.get` into
    `requests . get`, which silently disabled every dotted keyword."""
    from evalguard import rules
    stripped = rules._code_only("r = requests.get(u)  # baseline\n")
    assert "requests.get" in stripped, "dotted name destroyed by token join"
    assert "baseline" not in stripped, "comment leaked into code view"


def test_strings_are_stripped_from_code_view():
    from evalguard import rules
    stripped = rules._code_only('print("saved and archived")\n')
    assert "archived" not in stripped


def test_syntax_error_is_reported_not_crashed():
    res = cli.scan(str(HERE / "broken_syntax.py"))
    assert any(r["eg_id"] == "EG000" for r in res)


def test_exit_code_is_one_only_when_blocker_fires():
    assert cli.main(["--format", "json", str(HERE / "planted_eval.py")]) == 0
    assert cli.main([str(HERE / "planted_eval.py")]) == 1
    assert cli.main([str(HERE / "clean_eval.py")]) == 0
