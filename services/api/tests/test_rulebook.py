"""The rule book keeps its own promises (Preamble, Appendices A and B, Part 0).

These checks are what the Preamble says `tests/test_rulebook.py` does: the cross-reference
invariant, the generated Appendix B, the paths a rule cites, the Part 0 values against the code,
the retired numbers, and rule 25 against the rule book itself.
"""

import importlib
import importlib.util
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RULEBOOK = ROOT / "RULEBOOK.md"
WAIVERS = ROOT / "docs" / "rulebook-paths-waivers.md"
API = ROOT / "services" / "api"

spec = importlib.util.spec_from_file_location(
    "build_rule_index", ROOT / "scripts" / "build_rule_index.py"
)
index = importlib.util.module_from_spec(spec)
sys.modules["build_rule_index"] = index
spec.loader.exec_module(index)

TEXT = RULEBOOK.read_text(encoding="utf-8").replace("\r\n", "\n")
RULES = index.parse(TEXT)
BODY = "## Part 1." + TEXT.split("## Part 1.", 1)[1].split("## Appendix A.")[0]  # the rule bodies
FORCE = re.compile(r"^(Mandatory|Conditional \(.+\)|Informational)( \(.+\))?$")


def test_rules_are_numbered_one_to_thirty_eight_with_the_five_retired_gaps():
    numbers = {int(k) for k in RULES if not k.startswith("S")}
    assert numbers == set(range(1, 39)) - {5, 13, 14, 17, 19}
    assert {k for k in RULES if k.startswith("S")} == {f"S{n}" for n in range(1, 10)}


def test_every_rule_has_a_purpose_a_force_a_text_and_cross_references():
    for key, rule in RULES.items():
        assert rule.purpose and rule.text, key
        assert FORCE.match(rule.force.rstrip(".")), (key, rule.force)
        assert rule.depends, key


def test_every_rule_depends_on_exactly_what_it_cites():
    """The Preamble's grammar: Depends on lists every rule, S-rule and Part 0 item the Purpose or
    Text cites, and nothing else."""
    assert index.problems(TEXT) == []


def test_appendix_b_is_the_index_the_script_generates():
    assert index.regenerate(TEXT) == TEXT, "run `python scripts/build_rule_index.py --write`"


def test_no_rule_body_uses_a_retired_letter():
    assert not re.findall(r"\b[Rr]ules? [A-P]\b", BODY)


def test_every_retired_or_renumbered_entry_resolves_to_a_real_rule():
    table = TEXT.split("## Appendix A.")[1].split("## Appendix B.")[0]
    rows = [r for r in table.splitlines() if r.startswith("| ") and "---" not in r]
    assert len(rows) > 10
    for row in rows[1:]:
        _old, kind, now, _ = (c.strip() for c in row.strip("|").split("|", 3))
        assert kind in ("Retired", "Renumbered"), row
        for target in re.findall(r"S\d|\d+", now):
            assert target in RULES, row


def waived(table_heading: str) -> set[str]:
    text = WAIVERS.read_text(encoding="utf-8")
    section = text.split(table_heading)[1].split("\n## ")[0]
    return set(re.findall(r"^\| `([^`]+)`", section, re.M))


def resolve(path: str) -> Path:
    if path.startswith(("app/", "tests/", "migrations/")):
        return API / path
    return ROOT / path


def test_every_cited_path_exists_or_is_waived():
    waived_paths = waived("## 1. Paths cited")
    missing = []
    for key, rule in RULES.items():
        for path in rule.implementation + rule.tests:
            if path.startswith("private/") or path in waived_paths:
                continue
            if not resolve(path).exists():
                missing.append(f"rule {key}: {path}")
    assert not missing, missing


def section_02() -> list[tuple[str, str, str | None, str]]:
    body = TEXT.split("### 0.2 Normative values")[1].split("### 0.3")[0]
    rows = []
    for line in body.splitlines():
        m = re.match(r"\| `([A-Z0-9_]+)`(?: \(([^)]+)\))? \| (.+?) \| (.+) \|$", line)
        if m:
            rows.append((m.group(1), m.group(3), m.group(2), m.group(4)))
    return rows


FREQ_KEY = {"daily": "D", "weekly": "W", "biweekly": "B", "monthly": "M", "quarterly": "Q",
            "semi-annual": "S", "annual": "A"}  # fmt: skip


def number(cell: str) -> float:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cell):
        return float(date.fromisoformat(cell).toordinal())
    if cell.startswith("trailing 3 years"):
        return 3 * 365
    return float(re.search(r"\d+(?:\.\d+)?(?:e-?\d+)?", cell).group(0))


def held(name: str, qualifier: str | None, home: str):
    """The value the code holds for a Part 0 name, or raises LookupError."""
    if "refresh_run_timeout_seconds" in home:
        from app.core.config import Settings

        return Settings.model_fields["refresh_run_timeout_seconds"].default
    module = importlib.import_module(
        home.strip("`").split("`")[0].removesuffix(".py").replace("/", ".")
    )
    value = getattr(module, name)
    if name == "GRACE_DAYS":
        return [value[FREQ_KEY[q.strip()]] for q in qualifier.split(",")]
    if isinstance(value, date):
        return value.toordinal()
    if isinstance(value, timedelta):
        return value.days
    return value


def test_part_zero_values_are_held_by_the_code_or_waived():
    sys.path.insert(0, str(API))
    os.chdir(API)
    waived_names = waived("## 2. Part 0")
    assert len(section_02()) >= 25  # the table was read
    problems = []
    for name, cell, qualifier, home in section_02():
        if name in waived_names:
            continue
        try:
            value = held(name, qualifier, home)
        except (AttributeError, ImportError, LookupError, ValueError) as exc:
            problems.append(f"{name}: not in {home} ({type(exc).__name__})")
            continue
        expected = number(cell)
        for v in value if isinstance(value, list) else [value]:
            if name == "LAG_WINDOW":
                ok = abs(v - expected) <= 1
            else:
                ok = float(v) == pytest.approx(expected, rel=1e-9)
            if not ok:
                problems.append(f"{name}: the book says {cell}, the code holds {v}")
    assert not problems, problems


def test_the_waivers_name_only_values_and_paths_the_book_still_has():
    names = {n for n, *_ in section_02()}
    assert waived("## 2. Part 0") <= names


def test_rule_25_applies_to_the_rule_book_itself():
    """No AI assistant or code-generation tool is named in the rule book, its log or appendices."""
    named = re.findall(r"\b(Claude|Anthropic|Gemini|ChatGPT|OpenAI|Copilot|Codex)\b", TEXT, re.I)
    assert not named, named
