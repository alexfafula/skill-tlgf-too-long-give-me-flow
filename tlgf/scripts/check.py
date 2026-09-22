#!/usr/bin/env python3
"""Validate the TLGF skill package with the Python standard library."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent
SKILL = ROOT / "SKILL.md"
METADATA = ROOT / "agents" / "openai.yaml"
CASES = ROOT / "evals" / "cases.json"
REFERENCES = (
    ROOT / "references" / "addressable-flow.md",
    ROOT / "references" / "continuity.md",
    ROOT / "references" / "lineage.md",
)
CLAUDE_STYLE = REPOSITORY_ROOT / "adapters" / "claude" / "output-styles" / "tlgf.md"
AGENTS_BLOCK = REPOSITORY_ROOT / "adapters" / "agents" / "tlgf.md"
LICENSE = ROOT / "LICENSE.txt"
MAX_SKILL_LINES = 140
MIN_CASES = 12
PUBLIC_FIELDS = (
    "**You are here:**",
    "**What's happening now:**",
    "**Suggested next steps:**",
)
LEGACY_FIELDS = (
    "Situation:",
    "Now:",
    "Next best action:",
    "Worth noticing:",
    "Current goal:",
    "Progress so far:",
    "Need from you:",
)


def fail(message: str) -> None:
    raise ValueError(message)


def read(path: Path) -> str:
    if not path.is_file():
        try:
            relative = path.relative_to(ROOT)
        except ValueError:
            relative = path.relative_to(REPOSITORY_ROOT)
        fail(f"Missing required file: {relative}")
    return path.read_text(encoding="utf-8")


def validate_frontmatter(skill: str) -> None:
    match = re.match(r"\A---\n(.*?)\n---\n", skill, flags=re.DOTALL)
    if match is None:
        fail("SKILL.md must start with YAML frontmatter")
    lines = [line for line in match.group(1).splitlines() if line.strip()]
    keys = [line.split(":", 1)[0] for line in lines]
    if keys != ["name", "description"]:
        fail("Frontmatter must contain only name and description")
    if lines[0] != "name: tlgf":
        fail("Skill name must be tlgf")
    if "$tlgf" not in lines[1] or "standalone" not in lines[1]:
        fail("Description must define explicit activation and the standalone boundary")
    description = lines[1].split(":", 1)[1].strip().strip('"')
    if len(description) > 1024:
        fail("Description must contain at most 1024 characters")
    if len(skill.splitlines()) > MAX_SKILL_LINES:
        fail(f"SKILL.md must stay at or below {MAX_SKILL_LINES} lines")


def validate_runtime(skill: str) -> None:
    templates = re.findall(r"```text\n(.*?)\n```", skill, flags=re.DOTALL)
    template = next(
        (
            candidate
            for candidate in templates
            if all(field in candidate for field in PUBLIC_FIELDS)
        ),
        None,
    )
    if template is None:
        fail("SKILL.md must define the TLGF text template")
    for field in PUBLIC_FIELDS:
        if template.count(field) != 1:
            fail(f"The public template must contain exactly one {field}")
    if any(field in template for field in LEGACY_FIELDS):
        fail("The public template contains a legacy fourth field")
    if template.count("---") != 3:
        fail("The public template must place a Markdown thematic break after every field")
    if not re.search(r"(?m)^1\. <.+>$", template):
        fail("The current-state field must start with numbered point 1")
    if not re.search(r"(?m)^A\. <.+>$", template):
        fail("The suggested-next-steps field must start with lettered step A")
    required_phrases = (
        "never create a fourth field",
        "actually running",
        "observable progress or measured throughput",
        "one to four numbered points",
        "one to four suggested steps",
        "lettered `A.` through at most `D.`",
        "put the recommended option first",
        "numbers refer only to current-state points",
        "letters refer only to suggested steps or options",
        "recovered evidence",
        ".tlgf/STATE.md",
        "Render all three labels naturally in the user's language",
        "Do not show bilingual labels",
        "embed language-specific translations",
        "bold only each localized label and its colon",
        "⛔ **Needs you**",
        "must be the first visible content",
        "`2` or `expand 2`",
        "`B` or `do B`",
        "`park 4`",
        "`fork 3`",
        "`deep dive 2`",
        "`refresh`",
        "Default to one compact paragraph or at most three short bullets",
        "Do not link back to the prior frame or the file that contains it",
        "End a status-only answer after the closing thematic break",
        "Never emit `file://` URLs",
        "Formatting compliance, semantic correctness, and host reliability are separate outcomes",
        "Leave a blank line before and after every `---`",
        "If the conversation contains no TLGF frame",
        "one or two sentences",
        "without echoing the trigger word",
        "Nothing follows that break",
        "even for a one-word follow-up",
    )
    for phrase in required_phrases:
        if phrase not in skill:
            fail(f"Missing runtime rule: {phrase}")


def validate_metadata(metadata: str) -> None:
    required = (
        'display_name: "TLGF — Too long! Give me flow!"',
        'short_description: "Keep parallel AI work oriented and actionable"',
        "$tlgf",
    )
    for value in required:
        if value not in metadata:
            fail(f"Missing OpenAI metadata value: {value}")
    description = re.search(r'short_description: "([^"]+)"', metadata)
    if description is None or not 25 <= len(description.group(1)) <= 64:
        fail("short_description must contain 25–64 characters")


def validate_adapters(claude_style: str, agents_block: str) -> None:
    claude_required = (
        "name: TLGF",
        "description: State-first, addressable flow for parallel AI work",
        "keep-coding-instructions: true",
        "⛔ **Needs you**",
        "`2` or `expand 2`",
        "`B` or `do B`",
        "Never emit `file://` URLs",
        "Leave a blank line before and after every `---`",
        "If no TLGF frame exists",
        "Do not echo the trigger word",
        "Nothing follows that break",
    )
    agents_required = (
        "# TLGF agent instruction block",
        "**You are here:**",
        "1. <the most important current fact>",
        "A. <the next action and what it unlocks>",
        "`expand 2`",
        "`do B`",
        "Never emit `file://` URLs",
        "Leave a blank line before and after every `---`",
        "If no TLGF frame exists",
        "Do not echo the trigger word",
        "Nothing follows that break",
    )
    for value in claude_required:
        if value not in claude_style:
            fail(f"Claude output-style adapter is missing: {value}")
    for value in agents_required:
        if value not in agents_block:
            fail(f"AGENTS.md adapter is missing: {value}")


def validate_cases() -> int:
    try:
        payload = json.loads(read(CASES))
    except json.JSONDecodeError as error:
        fail(f"Invalid eval JSON: {error}")
    if payload.get("schema_version") != 1 or payload.get("skill") != "tlgf":
        fail("Eval metadata must identify TLGF schema 1")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) < MIN_CASES:
        fail(f"At least {MIN_CASES} eval cases are required")
    ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            fail("Every eval case must be an object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            fail(f"Invalid or duplicate eval id: {case_id}")
        ids.add(case_id)
        for key in ("purpose", "prompt"):
            if not isinstance(case.get(key), str) or not case[key].strip():
                fail(f"{case_id}: {key} must be a non-empty string")
        for key in ("must_include", "must_avoid"):
            values = case.get(key)
            if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
                fail(f"{case_id}: {key} must be a string list")
    required_ids = {
        "parallel-work-status",
        "running-work-useful-signal",
        "blocked-decision-triage",
        "retry-lineage",
        "standalone-restraint",
        "addressable-expand",
        "addressable-action",
        "polish-localized-labels",
        "missing-frame-reference",
        "deliverable-after-triptych",
        "park-point",
        "refresh-after-action",
    }
    missing = sorted(required_ids - ids)
    if missing:
        fail(f"Missing required eval cases: {missing}")
    return len(cases)


def validate_links(skill: str) -> None:
    linked: set[Path] = set()
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", skill):
        if re.match(r"(?:https?://|mailto:|#)", target):
            continue
        resolved = (ROOT / target.split("#", 1)[0]).resolve()
        if not resolved.is_file():
            fail(f"Broken link in SKILL.md: {target}")
        linked.add(resolved)
    for reference in REFERENCES:
        if reference.resolve() not in linked:
            fail(f"SKILL.md never routes to {reference.relative_to(ROOT)}")
    addressable = read(REFERENCES[0])
    if "## Missing or mismatched reference" not in addressable:
        fail("addressable-flow.md must define the missing-frame rule")


def validate_license() -> None:
    text = read(LICENSE)
    if not text.startswith("MIT License\n"):
        fail("LICENSE.txt must contain the MIT License")


def main() -> int:
    try:
        skill = read(SKILL)
        validate_frontmatter(skill)
        validate_runtime(skill)
        validate_links(skill)
        validate_license()
        validate_metadata(read(METADATA))
        if CLAUDE_STYLE.is_file() and AGENTS_BLOCK.is_file():
            validate_adapters(read(CLAUDE_STYLE), read(AGENTS_BLOCK))
        for reference in REFERENCES:
            read(reference)
        case_count = validate_cases()
    except ValueError as error:
        print(f"TLGF invalid: {error}", file=sys.stderr)
        return 1
    print(f"TLGF valid: triptych contract, {case_count} eval cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
