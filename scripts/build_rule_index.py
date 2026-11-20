"""Build Appendix B of RULEBOOK.md, the cross-reference index, from the rule bodies.

The rule book (Preamble, "Cross-references") says each rule hand-maintains its `Depends on:` line
and that the `Referenced by:` column is generated: it is the union of every other rule's
`Depends on:`. This script parses the rule book, regenerates that appendix, and checks the
citation invariant: a rule body cites a rule, an S-rule or a Part 0 item only if its `Depends on:`
lists it, and lists nothing it does not cite.

    uv run python scripts/build_rule_index.py            # print the problems, exit 1 if any
    uv run python scripts/build_rule_index.py --write    # rewrite Appendix B in RULEBOOK.md

`services/api/tests/test_rulebook.py` runs the same checks in CI.
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULEBOOK = ROOT / "RULEBOOK.md"

HEADING = re.compile(r"^### (?:Rule (\d+)|(S\d))\. (.+)$", re.M)
APPENDIX_B = "## Appendix B. Cross-reference index"
APPENDIX_C = "## Appendix C. Change log"

# Terms of Part 0, section 0.1, that a rule body can cite by name.
TERMS_0_1 = (
    "due date",
    "grace period",
    "timeliness weight",
    "score scale",
    "data table",
    "hot query",
    "source decision",
    "provisional source decision",
    "staging",
    "staged series",
    "retired series",
    "catalog version",
    "scorecard recipe",
    "native source",
    "freshness.usable",
)

HEADER = """## Appendix B. Cross-reference index

**Generated** by `scripts/build_rule_index.py` from the `Depends on:` lines of the rule bodies; do
not edit it by hand. `tests/test_rulebook.py` fails if it differs from the script's output, or if a
rule body cites a rule that is not in its `Depends on:` line. Rule bodies hold no `Referenced by:`
blocks; this appendix is their sole home.

| Rule | Depends on | Referenced by | Implementation | Tests |
|---|---|---|---|---|
"""


@dataclass
class Rule:
    key: str  # "1", "38", "S5"
    title: str
    purpose: str = ""
    force: str = ""
    text: str = ""
    depends: list[str] = field(default_factory=list)
    implementation: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)


def sort_key(key: str) -> tuple[int, float]:
    """0.1, 0.2, 0.3 first, then 1..38, then S1..S9."""
    if key.startswith("S"):
        return (2, int(key[1:]))
    return (0 if key.startswith("0.") else 1, float(key))


def _section(text: str, start: str, end: str | None) -> str:
    a = text.index(start)
    b = text.index(end, a) if end else len(text)
    return text[a:b]


def part_zero(text: str) -> tuple[set[str], set[str]]:
    """The names in section 0.2 (normative values) and the principles' count."""
    body = _section(text, "### 0.2 Normative values", "### 0.3 Principles")
    constants = set(re.findall(r"^\| `([A-Z0-9_]+)`", body, re.M))
    return constants, set()


def parse(text: str) -> dict[str, Rule]:
    rules: dict[str, Rule] = {}
    matches = list(HEADING.finditer(text))
    for i, m in enumerate(matches):
        key = m.group(1) or m.group(2)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[m.end() : end]
        for stop in ("\n---\n", "\n## "):
            if stop in chunk:
                chunk = chunk[: chunk.index(stop)]
        rule = Rule(key, m.group(3).strip())
        purpose = re.search(r"\*\*Purpose:\*\* (.+)", chunk)
        force = re.search(r"\*\*Force:\*\* (.+)", chunk)
        rule.purpose = purpose.group(1).strip() if purpose else ""
        rule.force = force.group(1).strip() if force else ""
        body = chunk.split("**Text:**", 1)[1] if "**Text:**" in chunk else ""
        rule.text = body.split("**Cross-references:**", 1)[0].strip()
        refs = (
            chunk.split("**Cross-references:**", 1)[1] if "**Cross-references:**" in chunk else ""
        )
        for line in refs.splitlines():
            line = line.strip()
            if line.startswith("- Depends on:"):
                rule.depends = [t.strip() for t in line.split(":", 1)[1].split(",") if t.strip()]
            elif line.startswith("- Implementation:"):
                rule.implementation = re.findall(r"`([^`]+)`", line)
            elif line.startswith("- Tests:"):
                rule.tests = re.findall(r"`([^`]+)`", line)
        rules[key] = rule
    return rules


def citations(rule: Rule, constants: set[str]) -> set[str]:
    """Every rule, S-rule and Part 0 item the Purpose and Text cite (the Preamble's grammar)."""
    text = rule.purpose + "\n" + rule.text
    found: set[str] = set()
    # "rule 38", "rules 12 and 26", "rules 1 to 3", "(rules 10, 12, 18, 29)"
    for m in re.finditer(r"\b[Rr]ules?\s+(\d+(?:\s*(?:,|and|to|–|-)\s*\d+)*)", text):
        parts = re.split(r"\s*(?:,|and)\s*", m.group(1))
        for part in parts:
            span = re.split(r"\s*(?:to|–|-)\s*", part)
            if len(span) == 2:
                found.update(str(n) for n in range(int(span[0]), int(span[1]) + 1))
            else:
                found.add(span[0].strip())
    # "S5", and the range "S1–S9"
    if re.search(r"\bS1\s*[–-]\s*S9\b", text):
        found.update(f"S{n}" for n in range(1, 10))
    found.update(re.findall(r"\bS[1-9]\b", text))
    # Part 0 by marker, by section-0.2 constant, or by the name of a section-0.1 term
    for n in ("1", "2", "3"):
        if re.search(rf"§0\.{n}\b", text):
            found.add(f"0.{n}")
    if any(re.search(rf"\b{re.escape(c)}\b", text) for c in constants):
        found.add("0.2")
    lowered = text.lower()
    if any(term in lowered for term in TERMS_0_1):
        found.add("0.1")
    found.discard(rule.key)
    return found


def referenced_by(rules: dict[str, Rule]) -> dict[str, list[str]]:
    reverse: dict[str, set[str]] = {k: set() for k in rules}
    for key, rule in rules.items():
        for dep in rule.depends:
            if dep in reverse:
                reverse[dep].add(key)
    return {k: sorted(v, key=sort_key) for k, v in reverse.items()}


def problems(text: str) -> list[str]:
    rules = parse(text)
    constants, _ = part_zero(text)
    found = []
    for key in sorted(rules, key=sort_key):
        rule = rules[key]
        cited = citations(rule, constants)
        listed = set(rule.depends)
        for missing in sorted(cited - listed, key=sort_key):
            found.append(f"rule {key}: cites {missing} but does not list it in Depends on")
        for extra in sorted(listed - cited, key=sort_key):
            found.append(f"rule {key}: lists {extra} in Depends on but does not cite it")
        for dep in listed:
            if dep not in rules and not dep.startswith("0."):
                found.append(f"rule {key}: Depends on {dep}, which is not a rule")
        if not rule.purpose or not rule.force or not rule.text:
            found.append(f"rule {key}: missing Purpose, Force or Text")
    return found


def _cell(items: list[str]) -> str:
    return ", ".join(f"`{i}`" for i in items) if items else "—"


def build_appendix(text: str) -> str:
    rules = parse(text)
    reverse = referenced_by(rules)
    rows = []
    for key in sorted(rules, key=sort_key):
        rule = rules[key]
        deps = ", ".join(sorted(rule.depends, key=sort_key)) or "—"
        refs = ", ".join(reverse[key]) or "—"
        rows.append(
            f"| {key} | {deps} | {refs} | {_cell(rule.implementation)} | {_cell(rule.tests)} |"
        )
    return HEADER + "\n".join(rows) + "\n\n---\n\n"


def regenerate(text: str) -> str:
    a = text.index(APPENDIX_B)
    b = text.index(APPENDIX_C)
    return text[:a] + build_appendix(text) + text[b:]


def main(argv: list[str]) -> int:
    raw = RULEBOOK.read_text(encoding="utf-8", newline="")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    if "--write" in argv:
        new = regenerate(text)
        RULEBOOK.write_text(
            new.replace("\n", "\r\n") if crlf else new, encoding="utf-8", newline=""
        )
        print("Appendix B regenerated")
        return 0
    found = problems(text)
    if regenerate(text) != text:
        found.append("Appendix B differs from the generated index: run with --write")
    for line in found:
        print(line)
    print(f"{len(found)} problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
