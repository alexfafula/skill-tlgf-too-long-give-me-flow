#!/usr/bin/env python3
"""Run the fixture-backed TLGF cognitive-continuity benchmark."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import re
import shutil
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


BENCHMARK_ROOT = Path(__file__).resolve().parent
SHARED_ROOT = BENCHMARK_ROOT.parent
ROOT = SHARED_ROOT.parent
MANIFEST_PATH = BENCHMARK_ROOT / "manifest.json"
SKILL_ROOT = ROOT / "tlgf"
DEFAULT_RESULTS_ROOT = SHARED_ROOT / "results" / "tlgf"
DEFAULT_ENV_FILE = ROOT / ".env"
CORE_PATH = SHARED_ROOT / "core.py" if (SHARED_ROOT / "core.py").is_file() else SHARED_ROOT / "run.py"
RENDERER_PATH = SHARED_ROOT / "render_html.py"
AGENTS = ("claude", "codex", "agy")
MODEL_ENV_KEYS = {
    "claude": "TLGF_BENCH_CLAUDE_MODEL",
    "codex": "TLGF_BENCH_CODEX_MODEL",
    "agy": "TLGF_BENCH_AGY_MODEL",
}
CONTROL = "control"
TREATMENT = "tlgf"
STATE_FILE = ".tlgf/STATE.md"
RESULT_SCHEMA_VERSION = 1
PARSER_SCHEMA_VERSION = 5
PERCENT = re.compile(r"(?<![\d/])\b\d+(?:\.\d+)?%")
TRIPTYCH_SEPARATOR = "---"
TRIPTYCH_BREAK = re.compile(r"(?m)^[ \t]*---[ \t]*$")
NUMBERED_ITEM = re.compile(r"(?m)^[ \t]*(\d+)\.[ \t]+\S.*$")
LETTERED_ITEM = re.compile(r"(?m)^[ \t]*([A-Za-z])\.[ \t]+\S.*$")
DEFAULT_LABELS: dict[str, list[str]] = {"you_are_here": ["You are here"], "needs_you": ["Needs you"]}
LABEL_KEYS = ("you_are_here", "needs_you")


def label_alternation(labels: list[str]) -> str:
    return "(?:" + "|".join(re.escape(label) for label in labels) + ")"


def you_are_here_pattern(labels: list[str] | None = None) -> re.Pattern[str]:
    return re.compile(r"\A\*\*" + label_alternation(labels or DEFAULT_LABELS["you_are_here"]) + r":\*\*")


def needs_you_pattern(labels: list[str] | None = None) -> re.Pattern[str]:
    return re.compile(r"(?mi)^[ \t]*⛔[ \t]*\*\*" + label_alternation(labels or DEFAULT_LABELS["needs_you"]) + r"\*\*")


def case_labels(case: dict[str, Any]) -> dict[str, list[str]]:
    """Localized label alternatives for a case; English by default."""
    labels = {key: list(value) for key, value in DEFAULT_LABELS.items()}
    override = case.get("labels")
    if isinstance(override, dict):
        for key in LABEL_KEYS:
            value = override.get(key)
            if isinstance(value, str) and value.strip():
                labels[key] = [value.strip()]
            elif isinstance(value, list) and value and all(isinstance(item, str) and item.strip() for item in value):
                labels[key] = [item.strip() for item in value]
    return labels


YOU_ARE_HERE_START = you_are_here_pattern()
NEEDS_YOU_SIGNAL = needs_you_pattern()


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Can't load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load_module("shared_benchmark_core", CORE_PATH)
renderer = load_module("shared_benchmark_renderer", RENDERER_PATH)


class BenchmarkError(RuntimeError):
    """A TLGF benchmark configuration or execution error."""


def fail(message: str) -> None:
    raise BenchmarkError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        fail(f"Can't read JSON from {path}: {error}")
    if not isinstance(value, dict):
        fail(f"Expected a JSON object in {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        fail(f"{label} must be a list of strings")
    return value


def term_groups(value: Any, label: str) -> list[list[str]]:
    if not isinstance(value, list):
        fail(f"{label} must be a list")
    groups: list[list[str]] = []
    for group in value:
        if (
            not isinstance(group, list)
            or not group
            or any(not isinstance(term, str) or not term for term in group)
        ):
            fail(f"{label} must contain nonempty string lists")
        groups.append(group)
    return groups


def fixture_path(
    case: dict[str, Any], *, require_exists: bool = True
) -> Path:
    fixture = case.get("fixture")
    if not isinstance(fixture, str) or not fixture:
        fail(f"Case {case.get('id')} has no fixture")
    path = (BENCHMARK_ROOT / fixture).resolve()
    fixtures_root = (BENCHMARK_ROOT / "fixtures").resolve()
    if path != fixtures_root and fixtures_root not in path.parents:
        fail(f"Case {case.get('id')} fixture escapes fixtures/: {fixture}")
    if require_exists and not path.is_dir():
        fail(f"Case {case.get('id')} fixture doesn't exist: {fixture}")
    return path


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    manifest = read_json(path)
    if manifest.get("schema_version") != 1:
        fail("Unsupported TLGF benchmark manifest schema")
    skill = manifest.get("skill")
    if not isinstance(skill, dict) or skill.get("name") != "tlgf":
        fail("The manifest must identify the tlgf skill")
    conditions = manifest.get("conditions")
    if not isinstance(conditions, dict) or set(conditions) != {CONTROL, TREATMENT}:
        fail("The manifest must define control and tlgf conditions")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        fail("The manifest must define benchmark cases")
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            fail("Every benchmark case must be an object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or re.fullmatch(r"[a-z0-9-]+", case_id) is None:
            fail(f"Invalid benchmark case ID: {case_id!r}")
        if case_id in seen:
            fail(f"Duplicate benchmark case ID: {case_id}")
        seen.add(case_id)
        if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
            fail(f"Case {case_id} has no prompt")
        for key in ("enabled_by_default", "requires_preparation"):
            if key in case and not isinstance(case[key], bool):
                fail(f"Case {case_id} has invalid {key}")
        for key in ("requires_needs_user_signal", "forbids_needs_user_signal"):
            if key in case and not isinstance(case[key], bool):
                fail(f"Case {case_id} has invalid {key}")
        if case.get("requires_needs_user_signal") and case.get(
            "forbids_needs_user_signal"
        ):
            fail(f"Case {case_id} can't require and forbid the needs-user signal")
        branch = case.get("workspace_branch")
        if not isinstance(branch, str) or not branch.strip():
            fail(f"Case {case_id} has no workspace_branch")
        requires_preparation = bool(case.get("requires_preparation"))
        fixture = fixture_path(case, require_exists=not requires_preparation)
        source_repository = case.get("source_repository")
        if requires_preparation:
            if not isinstance(source_repository, dict):
                fail(f"Case {case_id} has no source_repository metadata")
            for key in ("url", "commit", "license"):
                if not isinstance(source_repository.get(key), str) or not source_repository[
                    key
                ].strip():
                    fail(f"Case {case_id} has invalid source_repository.{key}")
        for relative in string_list(case.get("required_paths", []), f"{case_id}.required_paths"):
            target = (fixture / relative).resolve()
            if target != fixture and fixture not in target.parents:
                fail(f"Case {case_id} required path escapes its fixture: {relative}")
            if fixture.is_dir() and not target.is_file():
                fail(f"Case {case_id} required path doesn't exist: {relative}")
        term_groups(case.get("required_term_groups", []), f"{case_id}.required_term_groups")
        term_groups(
            case.get("treatment_required_term_groups", []),
            f"{case_id}.treatment_required_term_groups",
        )
        string_list(case.get("forbidden_terms", []), f"{case_id}.forbidden_terms")
        string_list(
            case.get("treatment_forbidden_terms", []),
            f"{case_id}.treatment_forbidden_terms",
        )
        string_list(case.get("review_criteria", []), f"{case_id}.review_criteria")
        string_list(case.get("semantic_facts", []), f"{case_id}.semantic_facts")
        labels = case.get("labels", {})
        if not isinstance(labels, dict) or any(
            key not in LABEL_KEYS
            or not (
                (isinstance(value, str) and value.strip())
                or (isinstance(value, list) and value and all(isinstance(item, str) and item.strip() for item in value))
            )
            for key, value in labels.items()
        ):
            fail(f"Case {case_id} labels must map you_are_here or needs_you to text or a list of texts")
        if "deliverable_after_frame" in case and not isinstance(case["deliverable_after_frame"], bool):
            fail(f"Case {case_id} has invalid deliverable_after_frame")
        orientation = case.get("orientation_facts", {})
        if not isinstance(orientation, dict):
            fail(f"Case {case_id} orientation_facts must be an object")
        for name, accepted in orientation.items():
            if not isinstance(name, str):
                fail(f"Case {case_id} has an invalid orientation fact name")
            term_groups([accepted], f"{case_id}.orientation_facts.{name}")
        for key in ("max_response_words", "max_user_questions"):
            value = case.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                fail(f"Case {case_id} has invalid {key}")
    return manifest


def manifest_digest() -> str:
    return hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()


def fixture_set_digest(
    manifest: dict[str, Any], cases: list[dict[str, Any]] | None = None
) -> str:
    digest = hashlib.sha256()
    selected = cases if cases is not None else select_cases(manifest, None)
    for case in selected:
        digest.update(str(case["id"]).encode())
        digest.update(b"\0")
        digest.update(core.repository_digest(fixture_path(case)).encode())
        digest.update(b"\0")
    return digest.hexdigest()


def install_skill(agent: str, workspace: Path) -> Path:
    if not SKILL_ROOT.is_dir():
        fail(f"TLGF skill root doesn't exist: {SKILL_ROOT}")
    if agent == "claude":
        destination = workspace / ".claude" / "skills" / "tlgf"
    else:
        destination = workspace / ".agents" / "skills" / "tlgf"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SKILL_ROOT, destination)
    return destination


def workspace_path(
    run_root: Path,
    agent: str,
    condition: str,
    case_id: str,
    repetition: int,
) -> Path:
    return (
        run_root
        / "workspaces"
        / agent
        / condition
        / case_id
        / f"r{repetition}"
        / "workspace"
    )


def create_workspace(
    run_root: Path,
    agent: str,
    condition: str,
    case: dict[str, Any],
    environment: dict[str, str],
    repetition: int = 1,
    replace_incomplete: bool = False,
) -> Path:
    if repetition < 1:
        fail("Workspace repetition must be at least 1")
    workspace = workspace_path(
        run_root,
        agent,
        condition,
        str(case["id"]),
        repetition,
    )
    if workspace.exists():
        if not replace_incomplete:
            fail(f"Workspace already exists: {workspace}")
        shutil.rmtree(workspace)
    workspace.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(fixture_path(case), workspace)
    if condition == TREATMENT:
        install_skill(agent, workspace)
    core.run_checked(
        ["git", "-C", str(workspace), "init", "-q", "-b", str(case["workspace_branch"])]
    )
    return workspace


def stable_condition_order(
    seed: int, agent: str, case_id: str, repetition: int
) -> list[str]:
    material = f"{seed}:{agent}:{case_id}:{repetition}:tlgf".encode()
    derived = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    order = [CONTROL, TREATMENT]
    random.Random(derived).shuffle(order)
    return order


def state_file_digest(workspace: Path) -> str | None:
    """Digest of .tlgf/STATE.md, which the skill may legitimately update."""
    path = workspace / STATE_FILE
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_text(value: str) -> str:
    return re.sub(r"[`*_]", "", value).casefold()


def match_groups(response: str, groups: list[list[str]]) -> list[dict[str, Any]]:
    normalized = normalize_text(response)
    matches: list[dict[str, Any]] = []
    for group in groups:
        matched = [term for term in group if normalize_text(term) in normalized]
        matches.append({"terms": group, "matched": matched, "passed": bool(matched)})
    return matches


def count_questions(response: str) -> int:
    without_code = re.sub(r"```.*?```", "", response, flags=re.DOTALL)
    without_quoted_questions = re.sub(
        r'(["“])[^"”\n]*\?[^"”\n]*(["”])', "", without_code
    )
    without_table_rows = "\n".join(
        line
        for line in without_quoted_questions.splitlines()
        if not (line.count("|") >= 2 and "?" in line)
    )
    without_question_headings = re.sub(
        r"(?m)^\s*#{1,6}\s+[^\n?]*\?[^\n]*$", "", without_table_rows
    )
    return without_question_headings.count("?")


def triptych_list_structure(response: str) -> dict[str, Any]:
    """Measure stable numeric-state and lettered-action addresses."""
    sections = TRIPTYCH_BREAK.split(response)
    if len(sections) != 4:
        return {
            "current_point_ids": [],
            "suggested_step_ids": [],
            "current_points_valid": False,
            "suggested_steps_valid": False,
        }
    current_point_ids = NUMBERED_ITEM.findall(sections[1])
    misplaced_current_letters = LETTERED_ITEM.findall(sections[1])
    suggested_step_ids = [item.upper() for item in LETTERED_ITEM.findall(sections[2])]
    misplaced_step_numbers = NUMBERED_ITEM.findall(sections[2])
    expected_current_ids = [str(index) for index in range(1, len(current_point_ids) + 1)]
    expected_step_ids = [chr(ord("A") + index) for index in range(len(suggested_step_ids))]
    return {
        "current_point_ids": current_point_ids,
        "suggested_step_ids": suggested_step_ids,
        "current_points_valid": (
            1 <= len(current_point_ids) <= 4
            and current_point_ids == expected_current_ids
            and not misplaced_current_letters
        ),
        "suggested_steps_valid": (
            1 <= len(suggested_step_ids) <= 4
            and suggested_step_ids == expected_step_ids
            and not misplaced_step_numbers
        ),
    }


def first_visible_content(
    response: str, labels: dict[str, list[str]] | None = None
) -> dict[str, Any]:
    """Check the hard first-content gate using the case's localized labels."""
    labels = labels or DEFAULT_LABELS
    you_are_here = you_are_here_pattern(labels["you_are_here"])
    needs_you = needs_you_pattern(labels["needs_you"])
    stripped = response.lstrip()
    signal_at_start = needs_you.match(stripped)
    you_are_here_at_start = you_are_here.match(stripped) is not None
    after_signal_starts_triptych = False
    if signal_at_start is not None:
        first_line_end = stripped.find("\n", signal_at_start.end())
        remainder = "" if first_line_end < 0 else stripped[first_line_end + 1 :].lstrip()
        after_signal_starts_triptych = you_are_here.match(remainder) is not None
    return {
        "labels": labels,
        "starts_with_you_are_here": you_are_here_at_start,
        "needs_you_present": needs_you.search(response) is not None,
        "needs_you_at_start": signal_at_start is not None,
        "needs_you_followed_by_triptych": after_signal_starts_triptych,
        "valid_triptych_start": you_are_here_at_start
        or (signal_at_start is not None and after_signal_starts_triptych),
    }


def evaluate_response(
    case: dict[str, Any],
    condition: str,
    response: str,
    workspace: Path,
    activation_evidence: list[str],
    *,
    execution_succeeded: bool,
    workspace_unchanged: bool,
    visible_text: str,
    evidence_text: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_text(response)
    normalized_evidence = normalize_text(
        response if evidence_text is None else f"{response}\n{evidence_text}"
    )
    required_groups = match_groups(response, case.get("required_term_groups", []))
    treatment_groups = match_groups(
        response,
        case.get("treatment_required_term_groups", []) if condition == TREATMENT else [],
    )
    required_paths = {
        relative: normalize_text(relative) in normalized_evidence
        and (workspace / relative).is_file()
        for relative in case.get("required_paths", [])
    }
    forbidden = list(case.get("forbidden_terms", []))
    if condition == TREATMENT:
        forbidden.extend(case.get("treatment_forbidden_terms", []))
    forbidden_terms = {term: normalize_text(term) in normalized for term in forbidden}
    orientation_checks: dict[str, bool] = {}
    orientation_matches: dict[str, list[str]] = {}
    for name, accepted in case.get("orientation_facts", {}).items():
        matched = [term for term in accepted if normalize_text(term) in normalized]
        orientation_checks[name] = bool(matched)
        orientation_matches[name] = matched
    word_count = core.reader_response_word_count(response)
    max_words = int(case["max_response_words"])
    question_count = count_questions(response)
    max_questions = int(case["max_user_questions"])
    percentages = PERCENT.findall(response)
    forbid_percent = bool(case.get("forbid_unmeasured_percent"))
    narration = [
        match.group(0).strip() for match in core.PROCESS_NARRATION.finditer(visible_text)
    ]
    expected_activation = condition == TREATMENT
    observed_activation = bool(activation_evidence)
    triptych_expected = condition == TREATMENT and case.get("mode") in {
        "orient",
        "resume",
    }
    separator_count = len(TRIPTYCH_BREAK.findall(response))
    triptych_lists = triptych_list_structure(response)
    first_content = first_visible_content(response, case_labels(case))
    requires_needs_user = condition == TREATMENT and bool(
        case.get("requires_needs_user_signal")
    )
    forbids_needs_user = condition == TREATMENT and bool(
        case.get("forbids_needs_user_signal")
    )
    needs_user_signal_valid = (
        (not requires_needs_user or first_content["needs_you_at_start"])
        and (not forbids_needs_user or not first_content["needs_you_present"])
    )
    checks = {
        "execution_succeeded": execution_succeeded,
        "workspace_unchanged": workspace_unchanged,
        "nonempty": bool(response.strip()),
        "required_paths": all(required_paths.values()),
        "required_term_groups": all(group["passed"] for group in required_groups),
        "treatment_protocol": all(group["passed"] for group in treatment_groups),
        "forbidden_terms": not any(forbidden_terms.values()),
        "orientation_facts": all(orientation_checks.values()),
        "response_word_limit": word_count <= max_words,
        "user_question_limit": question_count <= max_questions,
        "no_unmeasured_percent": not forbid_percent or not percentages,
        "no_process_narration": not narration,
        "skill_activation": observed_activation == expected_activation,
        "triptych_separator_count": not triptych_expected or separator_count == 3,
        "triptych_first_content": not triptych_expected
        or first_content["valid_triptych_start"],
        "triptych_closed": not triptych_expected
        or bool(case.get("deliverable_after_frame"))
        or response.rstrip().endswith(TRIPTYCH_SEPARATOR),
        "current_state_numbering": not triptych_expected
        or triptych_lists["current_points_valid"],
        "suggested_steps_lettering": not triptych_expected
        or triptych_lists["suggested_steps_valid"],
        "needs_user_signal": needs_user_signal_valid,
        "portable_links": condition != TREATMENT or "file://" not in response.casefold(),
    }
    budget_check_names = {"response_word_limit"}
    quality_checks = {
        name: passed for name, passed in checks.items() if name not in budget_check_names
    }
    budget_checks = {
        name: passed for name, passed in checks.items() if name in budget_check_names
    }
    return {
        "passed": all(quality_checks.values()),
        "quality_passed": all(quality_checks.values()),
        "budget_passed": all(budget_checks.values()),
        "all_checks_passed": all(checks.values()),
        "checks": checks,
        "quality_checks": quality_checks,
        "budget_checks": budget_checks,
        "required_paths": required_paths,
        "required_path_evidence_scope": "response_or_tool_trace",
        "required_term_groups": required_groups,
        "treatment_required_term_groups": treatment_groups,
        "forbidden_terms": forbidden_terms,
        "orientation_checks": orientation_checks,
        "orientation_matches": orientation_matches,
        "missing_orientation_fact_count": sum(
            1 for passed in orientation_checks.values() if not passed
        ),
        "response_words": word_count,
        "max_response_words": max_words,
        "user_question_count": question_count,
        "max_user_questions": max_questions,
        "percentages": percentages,
        "process_narration": narration,
        "style": core.style_metrics(response),
        "activation_expected": expected_activation,
        "activation_observed": observed_activation,
        "activation_evidence": activation_evidence,
        "triptych_separator_count": separator_count,
        "triptych_expected": triptych_expected,
        "triptych_lists": triptych_lists,
        "first_visible_content": first_content,
        "requires_needs_user_signal": requires_needs_user,
        "forbids_needs_user_signal": forbids_needs_user,
    }


def derive_attempt(
    agent: str,
    execution: dict[str, Any],
    attempt_number: int,
    requested_model: str | None,
    file_values: dict[str, str],
) -> dict[str, Any]:
    return core.derive_attempt(
        agent,
        {
            "attempt_number": attempt_number,
            "exit_code": execution["exit_code"],
            "timed_out": execution["timed_out"],
            "duration_seconds": execution["duration_seconds"],
            "raw_stdout": core.redact(execution["stdout"], file_values),
            "raw_stderr": core.redact(execution["stderr"], file_values),
        },
        requested_model,
        "tlgf",
    )


def regrade_result(
    result: dict[str, Any], case: dict[str, Any], workspace: Path
) -> dict[str, Any]:
    agent = str(result.get("agent") or "")
    requested_model = (
        result.get("requested_model")
        if isinstance(result.get("requested_model"), str)
        else None
    )
    stored_attempts = result.get("attempts")
    if not isinstance(stored_attempts, list) or not stored_attempts:
        fail("A result must contain saved attempts")
    attempts = [
        core.derive_attempt(agent, attempt, requested_model, "tlgf")
        for attempt in stored_attempts
        if isinstance(attempt, dict)
    ]
    if not attempts:
        fail("A result must contain at least one valid attempt")
    selected = attempts[-1]
    workspace_unchanged = not bool(result.get("workspace_mutated"))
    duration = round(
        sum(
            float(attempt["duration_seconds"])
            for attempt in attempts
            if isinstance(attempt.get("duration_seconds"), (int, float))
        ),
        3,
    )
    result.update(
        {
            "parser_schema_version": PARSER_SCHEMA_VERSION,
            "agent_status": selected["agent_status"],
            "runtime_model": selected["runtime_model"],
            "exit_code": selected["exit_code"],
            "timed_out": selected["timed_out"],
            "duration_seconds": duration,
            "selected_attempt_duration_seconds": selected["duration_seconds"],
            "response": selected["response"],
            "response_words": selected["response_words"],
            "markdown_source_words": selected["markdown_source_words"],
            "response_characters": selected["response_characters"],
            "visible_text": selected["visible_text"],
            "visible_text_words": selected["visible_text_words"],
            "visible_text_source_words": selected["visible_text_source_words"],
            "usage": core.aggregate_attempt_usage(attempts),
            "selected_attempt_usage": selected["usage"],
            "final_step_usage": selected["final_step_usage"],
            "finish_reason": selected["finish_reason"],
            "tool_call_count": sum(int(attempt["tool_call_count"]) for attempt in attempts),
            "selected_attempt_tool_call_count": selected["tool_call_count"],
            "attempt_count": len(attempts),
            "retry_count": len(attempts) - 1,
            "attempt_statuses": [attempt["agent_status"] for attempt in attempts],
            "first_attempt_status": attempts[0]["agent_status"],
            "recovered_after_retry": (
                len(attempts) > 1
                and attempts[0]["agent_status"] != "SUCCESS"
                and selected["agent_status"] == "SUCCESS"
            ),
            "attempts": attempts,
            "raw_stdout": selected["raw_stdout"],
            "raw_stderr": selected["raw_stderr"],
            "evaluation": evaluate_response(
                case,
                str(result.get("condition") or ""),
                selected["response"],
                workspace,
                selected["activation_evidence"],
                execution_succeeded=selected["agent_status"] == "SUCCESS",
                workspace_unchanged=workspace_unchanged,
                visible_text=selected["visible_text"],
                evidence_text=selected["raw_stdout"],
            ),
        }
    )
    return result


def result_filename(agent: str, case_id: str, condition: str, repetition: int) -> str:
    return f"{agent}__{case_id}__{condition}__r{repetition}.json"


def select_cases(
    manifest: dict[str, Any], requested: list[str] | None
) -> list[dict[str, Any]]:
    cases = manifest["cases"]
    if not requested:
        return [case for case in cases if case.get("enabled_by_default", True)]
    by_id = {case["id"]: case for case in cases}
    unknown = [case_id for case_id in requested if case_id not in by_id]
    if unknown:
        fail(f"Unknown benchmark cases: {', '.join(unknown)}")
    return [by_id[case_id] for case_id in requested]


def expected_results(
    manifest: dict[str, Any],
    cases: list[dict[str, Any]],
    agents: list[str],
    repetitions: int,
    seed: int,
) -> dict[str, dict[str, Any]]:
    expected: dict[str, dict[str, Any]] = {}
    for agent in agents:
        for case in cases:
            case_id = str(case["id"])
            fixture_sha256 = core.repository_digest(fixture_path(case))
            for repetition in range(1, repetitions + 1):
                order = stable_condition_order(seed, agent, case_id, repetition)
                for order_index, condition in enumerate(order, 1):
                    prompt = case["prompt"] + manifest["conditions"][condition][
                        "prompt_suffix"
                    ]
                    filename = result_filename(
                        agent, case_id, condition, repetition
                    )
                    expected[filename] = {
                        "agent": agent,
                        "case_id": case_id,
                        "condition": condition,
                        "repetition": repetition,
                        "condition_order": order_index,
                        "fixture_sha256": fixture_sha256,
                        "prompt": prompt,
                        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                    }
    return expected


def validate_resume_run(
    run_root: Path,
    manifest: dict[str, Any],
    cases: list[dict[str, Any]],
    agents: list[str],
    repetitions: int,
    seed: int,
    timeout_seconds: int,
    max_attempts: int,
    versions: dict[str, Any],
    manage_agy_settings: bool,
) -> tuple[dict[str, Any], set[str], int]:
    if not run_root.is_dir():
        fail(f"Resume directory doesn't exist: {run_root}")
    for required in ("manifest.json", "environment.json", "runs"):
        if not (run_root / required).exists():
            fail(f"Resume directory is missing {required}: {run_root}")

    stored_manifest = read_json(run_root / "manifest.json")
    if stored_manifest != manifest:
        fail("Can't resume: the benchmark manifest changed")
    environment_record = read_json(run_root / "environment.json")
    if environment_record.get("run_id") != run_root.name:
        fail("Can't resume: environment run_id doesn't match the directory name")

    digest_checks = {
        "manifest_sha256": manifest_digest(),
        "fixture_set_sha256": fixture_set_digest(manifest, cases),
        "skill_sha256": core.repository_digest(SKILL_ROOT),
    }
    for name, current_value in digest_checks.items():
        if environment_record.get(name) != current_value:
            fail(f"Can't resume: {name} changed")

    scalar_checks = {
        "seed": seed,
        "timeout_seconds": timeout_seconds,
        "max_attempts": max_attempts,
    }
    for name, current_value in scalar_checks.items():
        if environment_record.get(name) != current_value:
            fail(f"Can't resume: {name} changed")

    stored_agents = environment_record.get("agents")
    if not isinstance(stored_agents, dict) or set(stored_agents) != set(agents):
        fail("Can't resume: the selected agents changed")
    for agent in agents:
        stored = stored_agents.get(agent)
        current = versions.get(agent)
        if not isinstance(stored, dict) or not isinstance(current, dict):
            fail(f"Can't resume: agent metadata is missing for {agent}")
        for name in ("executable", "version", "requested_model", "display_model"):
            if stored.get(name) != current.get(name):
                fail(f"Can't resume: {agent} {name} changed")

    case_ids = [str(case["id"]) for case in cases]
    recorded_case_ids = environment_record.get("case_ids")
    if recorded_case_ids is not None and recorded_case_ids != case_ids:
        fail("Can't resume: the selected benchmark cases changed")
    recorded_repetitions = environment_record.get("repetitions")
    if recorded_repetitions is not None and recorded_repetitions != repetitions:
        fail("Can't resume: the repetition count changed")
    recorded_agy_management = environment_record.get("manage_agy_settings")
    if (
        recorded_agy_management is not None
        and recorded_agy_management != manage_agy_settings
    ):
        fail("Can't resume: Agy settings management changed")

    expected = expected_results(manifest, cases, agents, repetitions, seed)
    recorded_expected_count = environment_record.get("expected_result_count")
    if (
        recorded_expected_count is not None
        and recorded_expected_count != len(expected)
    ):
        fail("Can't resume: the expected result count changed")

    existing: set[str] = set()
    for result_path in sorted((run_root / "runs").glob("*.json")):
        specification = expected.get(result_path.name)
        if specification is None:
            fail(f"Can't resume: unexpected result file {result_path.name}")
        result = read_json(result_path)
        checks = {
            "schema_version": RESULT_SCHEMA_VERSION,
            "run_id": run_root.name,
            "agent": specification["agent"],
            "agent_version": versions[specification["agent"]]["version"],
            "case_id": specification["case_id"],
            "condition": specification["condition"],
            "repetition": specification["repetition"],
            "condition_order": specification["condition_order"],
            "fixture_sha256": specification["fixture_sha256"],
            "prompt": specification["prompt"],
            "prompt_sha256": specification["prompt_sha256"],
            "requested_model": versions[specification["agent"]][
                "requested_model"
            ],
            "max_attempts": max_attempts,
        }
        for name, expected_value in checks.items():
            if result.get(name) != expected_value:
                fail(f"Can't resume: {name} mismatch in {result_path.name}")
        existing.add(result_path.name)

    if environment_record.get("status") == "completed" and len(existing) != len(
        expected
    ):
        fail("Can't resume: a completed run is missing results")
    return environment_record, existing, len(expected)


def percentage_reduction(
    control: int | float | None, treatment: int | float | None
) -> float | None:
    if (
        not isinstance(control, (int, float))
        or not isinstance(treatment, (int, float))
        or isinstance(control, bool)
        or isinstance(treatment, bool)
        or control == 0
    ):
        return None
    return round((1 - treatment / control) * 100, 2)


def metric_delta(
    control: int | float | None, treatment: int | float | None
) -> int | float | None:
    if (
        not isinstance(control, (int, float))
        or not isinstance(treatment, (int, float))
        or isinstance(control, bool)
        or isinstance(treatment, bool)
    ):
        return None
    return treatment - control


def paired_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        grouped[(result["agent"], result["case_id"], result["repetition"])][
            result["condition"]
        ] = result
    pairs: list[dict[str, Any]] = []
    for (agent, case_id, repetition), conditions in sorted(grouped.items()):
        if set(conditions) != {CONTROL, TREATMENT}:
            continue
        control = conditions[CONTROL]
        treatment = conditions[TREATMENT]
        control_usage = control.get("usage", {})
        treatment_usage = treatment.get("usage", {})
        pairs.append(
            {
                "agent": agent,
                "case_id": case_id,
                "repetition": repetition,
                "control_pass": bool(control["evaluation"]["passed"]),
                "tlgf_pass": bool(treatment["evaluation"]["passed"]),
                "control_budget_pass": bool(
                    control["evaluation"].get("budget_passed", True)
                ),
                "tlgf_budget_pass": bool(
                    treatment["evaluation"].get("budget_passed", True)
                ),
                "comparable": bool(
                    control["evaluation"]["passed"]
                    and treatment["evaluation"]["passed"]
                ),
                "word_reduction_percent": percentage_reduction(
                    control.get("response_words"), treatment.get("response_words")
                ),
                "output_token_reduction_percent": percentage_reduction(
                    control_usage.get("output_tokens"),
                    treatment_usage.get("output_tokens"),
                ),
                "retry_inclusive_total_token_delta": metric_delta(
                    control_usage.get("total_tokens"),
                    treatment_usage.get("total_tokens"),
                ),
                "missing_orientation_fact_delta": metric_delta(
                    control["evaluation"].get("missing_orientation_fact_count"),
                    treatment["evaluation"].get("missing_orientation_fact_count"),
                ),
                "control_retries": int(control.get("retry_count") or 0),
                "tlgf_retries": int(treatment.get("retry_count") or 0),
            }
        )
    return pairs


def markdown_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value).replace("|", "\\|")


def blind_swap(run_id: str, agent: str, case_id: str, repetition: int) -> bool:
    material = f"{run_id}:{agent}:{case_id}:{repetition}:tlgf-blind".encode()
    return hashlib.sha256(material).digest()[0] % 2 == 0


def write_reports(run_root: Path) -> None:
    grader_manifest = run_root / "grader-manifest.json"
    manifest = read_json(
        grader_manifest if grader_manifest.is_file() else run_root / "manifest.json"
    )
    environment = read_json(run_root / "environment.json")
    results = [read_json(path) for path in sorted((run_root / "runs").glob("*.json"))]
    pairs = paired_results(results)
    summary = {
        "schema_version": 1,
        "run_id": environment["run_id"],
        "manifest_sha256": environment["manifest_sha256"],
        "grader_manifest_sha256": environment.get(
            "grader_manifest_sha256", environment["manifest_sha256"]
        ),
        "fixture_set_sha256": environment["fixture_set_sha256"],
        "run_count": len(results),
        "automated_pass_count": sum(bool(result["evaluation"]["passed"]) for result in results),
        "quality_pass_count": sum(
            bool(result["evaluation"]["quality_passed"]) for result in results
        ),
        "word_budget_pass_count": sum(
            bool(result["evaluation"]["budget_passed"]) for result in results
        ),
        "first_attempt_success_count": sum(
            result.get("first_attempt_status") == "SUCCESS" for result in results
        ),
        "recovered_after_retry_count": sum(
            bool(result.get("recovered_after_retry")) for result in results
        ),
        "pairs": pairs,
    }
    write_json(run_root / "summary.json", summary)

    report = [
        f"# TLGF benchmark run `{environment['run_id']}`",
        "",
        "> [!IMPORTANT]",
        "> These are automated diagnostic results. Complete the blind cold-reader review before publishing a claim.",
        "",
        f"Manifest: `{environment['manifest_sha256']}`",
        "",
        f"Fixtures: `{environment['fixture_set_sha256']}`",
        "",
        "## Runs",
        "",
        "| Agent | Case | Condition | Attempts | First status | Final status | Quality | Word budget | Reader words | Markdown source words | Mannerisms | Mean sentence words | Loop output | Total tokens | Missing orientation facts | Seconds |",
        "| --- | --- | --- | ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in sorted(
        results,
        key=lambda item: (
            item["agent"],
            item["case_id"],
            item["repetition"],
            item["condition"],
        ),
    ):
        report.append(
            "| "
            + " | ".join(
                markdown_value(value)
                for value in (
                    result["agent"],
                    result["case_id"],
                    result["condition"],
                    result["attempt_count"],
                    result["first_attempt_status"],
                    result["agent_status"],
                    result["evaluation"]["passed"],
                    result["evaluation"]["budget_passed"],
                    result["response_words"],
                    result.get("markdown_source_words", result["response_words"]),
                    result["evaluation"].get("style", {}).get("mannerism_count"),
                    result["evaluation"].get("style", {}).get("mean_sentence_words"),
                    result["usage"].get("output_tokens"),
                    result["usage"].get("total_tokens"),
                    result["evaluation"]["missing_orientation_fact_count"],
                    result["duration_seconds"],
                )
            )
            + " |"
        )
    report.extend(
        [
            "",
            "## Paired changes",
            "",
            "| Agent | Case | Control quality | TLGF quality | Control budget | TLGF budget | Comparable | Word reduction | Output-token reduction | Retry-inclusive total-token delta | Missing-orientation-fact delta |",
            "| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for pair in pairs:
        report.append(
            "| "
            + " | ".join(
                markdown_value(value)
                for value in (
                    pair["agent"],
                    pair["case_id"],
                    pair["control_pass"],
                    pair["tlgf_pass"],
                    pair["control_budget_pass"],
                    pair["tlgf_budget_pass"],
                    pair["comparable"],
                    pair["word_reduction_percent"],
                    pair["output_token_reduction_percent"],
                    pair["retry_inclusive_total_token_delta"],
                    pair["missing_orientation_fact_delta"],
                )
            )
            + " |"
        )
    report.extend(
        [
            "",
            "A negative missing-orientation-fact delta means that TLGF omitted fewer required facts.",
            "Token comparisons include retries and are valid only within the same agent and model.",
            "",
        ]
    )
    (run_root / "REPORT.md").write_text("\n".join(report), encoding="utf-8")

    cases = {case["id"]: case for case in manifest["cases"]}
    review = [
        f"# Blind cold-reader review for `{environment['run_id']}`",
        "",
        "Review each pair without identifying the treatment. Decide which answer lets a cold reader continue correctly with less reconstruction. Workspace paths show `CONDITION` in place of the condition directory, so both answers of a pair cite the same neutral path.",
        "",
    ]
    grouped: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        grouped[(result["agent"], result["case_id"], result["repetition"])][
            result["condition"]
        ] = result
    for (agent, case_id, repetition), conditions in sorted(grouped.items()):
        if set(conditions) != {CONTROL, TREATMENT}:
            continue
        swap = blind_swap(environment["run_id"], agent, case_id, repetition)
        answer_a = conditions[TREATMENT] if swap else conditions[CONTROL]
        answer_b = conditions[CONTROL] if swap else conditions[TREATMENT]
        case = cases[case_id]
        review.extend(
            [
                f"## Pair {agent} / {case_id} / repetition {repetition}",
                "",
                "### Full prompt",
                "",
                case["prompt"],
                "",
                "### Fixture summary",
                "",
                str(case.get("fixture_summary") or case.get("fixture") or ""),
                "",
                "### Answer A",
                "",
                core.neutralize_workspace_paths(answer_a["response"]) if answer_a["response"] else "[No final answer]",
                "",
                "### Answer B",
                "",
                core.neutralize_workspace_paths(answer_b["response"]) if answer_b["response"] else "[No final answer]",
                "",
                "### Cold-reader questions",
                "",
                "1. Which project and workstream are active?",
                "2. Which run, branch, or artifact is current?",
                "3. What is verified, and what remains unresolved?",
                "4. What exact action happens next?",
                "5. Does the user need to decide anything?",
                "",
                "| Review | Answer A | Answer B |",
                "| --- | --- | --- |",
                "| Orientation facts correct |  |  |",
                "| What we know is separated from inference |  |  |",
                "| Next best action is executable |  |  |",
                "| Reconstruction required |  |  |",
                "| Critical error |  |  |",
                "| Preference: A / B / tie / neither |  |  |",
                "",
                "### Case-specific criteria",
                "",
                *[f"- {criterion}" for criterion in case["review_criteria"]],
                "",
            ]
        )
    (run_root / "BLIND_REVIEW.md").write_text("\n".join(review), encoding="utf-8")
    renderer.render_report(run_root)


def safe_command_for_record(command: list[str], prompt: str) -> list[str]:
    return ["<PROMPT>" if argument == prompt else argument for argument in command]


def run_benchmark(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    cases = select_cases(manifest, args.cases)
    if not args.agents:
        fail("Select at least one agent with --agents")
    environment, file_values = core.effective_environment(args.env_file)
    overrides = {
        "claude": args.claude_model,
        "codex": args.codex_model,
        "agy": args.agy_model,
    }
    for agent, model in overrides.items():
        if model:
            environment[MODEL_ENV_KEYS[agent]] = model
    if "agy" in args.agents and not environment.get(MODEL_ENV_KEYS["agy"]):
        configured = core.configured_agy_model()
        if configured:
            environment[MODEL_ENV_KEYS["agy"]] = configured
    versions: dict[str, Any] = {}
    for agent in args.agents:
        executable = core.find_executable(agent)
        if executable is None:
            fail(f"Agent CLI isn't available: {agent}")
        requested = environment.get(MODEL_ENV_KEYS.get(agent, "")) or None
        source = "flag or environment" if requested else None
        if agent == "codex" and not requested:
            requested = core.configured_codex_model()
            source = "codex config.toml" if requested else None
        versions[agent] = {
            "executable": executable,
            "version": core.command_version(agent, executable),
            "requested_model": requested,
            "requested_model_source": source,
            "reasoning_effort": core.reasoning_effort(agent, requested),
            "display_model": None,
        }

    existing_results: set[str] = set()
    if args.resume_run is not None:
        run_root = args.resume_run.resolve()
        environment_record, existing_results, expected_result_count = (
            validate_resume_run(
                run_root,
                manifest,
                cases,
                args.agents,
                args.repetitions,
                args.seed,
                args.timeout,
                args.max_attempts,
                versions,
                args.manage_agy_settings,
            )
        )
        run_id = str(environment_record["run_id"])
        resume_events = environment_record.setdefault("resume_events", [])
        if not isinstance(resume_events, list):
            fail("Can't resume: environment resume_events isn't a list")
        resume_events.append(
            {
                "resumed_at": datetime.now(timezone.utc).isoformat(),
                "existing_result_count": len(existing_results),
                "missing_result_count": expected_result_count - len(existing_results),
            }
        )
        environment_record.update(
            {
                "status": "running",
                "case_ids": [str(case["id"]) for case in cases],
                "repetitions": args.repetitions,
                "expected_result_count": expected_result_count,
                "manage_agy_settings": args.manage_agy_settings,
            }
        )
        write_json(run_root / "environment.json", environment_record)
        print(
            f"Resuming: {run_id} "
            f"({len(existing_results)}/{expected_result_count} results saved)"
        )
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"{manifest['id']}__{timestamp}"
        run_root = args.results_root / run_id
        run_root.mkdir(parents=True, exist_ok=False)
        write_json(run_root / "manifest.json", manifest)
        write_json(run_root / "grader-manifest.json", manifest)
        expected_result_count = len(
            expected_results(
                manifest, cases, args.agents, args.repetitions, args.seed
            )
        )
        environment_record = {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "running",
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "agents": versions,
            "case_ids": [str(case["id"]) for case in cases],
            "repetitions": args.repetitions,
            "expected_result_count": expected_result_count,
            "seed": args.seed,
            "timeout_seconds": args.timeout,
            "max_attempts": args.max_attempts,
            "manage_agy_settings": args.manage_agy_settings,
            "retry_policy": "any empty answer or any TRUNCATED result",
            "manifest_sha256": manifest_digest(),
            "grader_manifest_sha256": manifest_digest(),
            "fixture_set_sha256": fixture_set_digest(manifest, cases),
            "skill_sha256": core.repository_digest(SKILL_ROOT),
            "codex_global_skills_disabled": True,
            "secrets_recorded": False,
        }
        write_json(run_root / "environment.json", environment_record)
        print(f"Run: {run_id}")
    print(f"Results: {run_root}")

    saved_results = set(existing_results)
    for agent in args.agents:
        manage_agy = agent == "agy" and args.manage_agy_settings
        with core.temporary_agy_sandbox_settings(manage_agy):
            isolated_environment = core.agent_environment(
                agent, environment, MODEL_ENV_KEYS
            )
            for case in cases:
                for repetition in range(1, args.repetitions + 1):
                    order = stable_condition_order(
                        args.seed, agent, str(case["id"]), repetition
                    )
                    for order_index, condition in enumerate(order, 1):
                        filename = result_filename(
                            agent, str(case["id"]), condition, repetition
                        )
                        result_path = run_root / "runs" / filename
                        if filename in saved_results:
                            print(
                                f"[{agent}] {case['id']} {condition} "
                                f"r{repetition} ({order_index}/2) saved",
                                flush=True,
                            )
                            continue
                        workspace = create_workspace(
                            run_root,
                            agent,
                            condition,
                            case,
                            environment,
                            repetition,
                            replace_incomplete=args.resume_run is not None,
                        )
                        prompt = case["prompt"] + manifest["conditions"][condition][
                            "prompt_suffix"
                        ]
                        command, requested_model = core.build_command(
                            agent,
                            condition,
                            workspace,
                            prompt,
                            environment,
                            skill_name="tlgf",
                            model_env_keys=MODEL_ENV_KEYS,
                            disable_other_codex_skills=True,
                        )
                        print(
                            f"[{agent}] {case['id']} {condition} "
                            f"r{repetition} ({order_index}/2)",
                            flush=True,
                        )
                        workspace_before = core.repository_digest(workspace, ignore=(STATE_FILE,))
                        state_before = state_file_digest(workspace)
                        attempts: list[dict[str, Any]] = []
                        for attempt_number in range(1, args.max_attempts + 1):
                            execution = core.execute(
                                command, workspace, isolated_environment, args.timeout
                            )
                            attempt = derive_attempt(
                                agent,
                                execution,
                                attempt_number,
                                requested_model,
                                file_values,
                            )
                            attempts.append(attempt)
                            print(
                                f"  attempt={attempt_number}/{args.max_attempts} "
                                f"status={attempt['agent_status']} "
                                f"words={attempt['response_words']}",
                                flush=True,
                            )
                            if not core.should_retry_incomplete_answer(
                                attempt["agent_status"],
                                attempt["response"],
                                attempt_number,
                                args.max_attempts,
                            ):
                                break
                            print(
                                "  retrying: final answer was missing or truncated",
                                flush=True,
                            )
                        workspace_after = core.repository_digest(workspace, ignore=(STATE_FILE,))
                        state_after = state_file_digest(workspace)
                        selected = attempts[-1]
                        result = {
                            "schema_version": RESULT_SCHEMA_VERSION,
                            "run_id": run_id,
                            "agent": agent,
                            "agent_version": versions[agent]["version"],
                            "case_id": case["id"],
                            "condition": condition,
                            "repetition": repetition,
                            "condition_order": order_index,
                            "fixture": case["fixture"],
                            "fixture_sha256": core.repository_digest(fixture_path(case)),
                            "prompt": prompt,
                            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                            "command": safe_command_for_record(command, prompt),
                            "requested_model": requested_model,
                            "display_model": None,
                            "max_attempts": args.max_attempts,
                            "attempts": attempts,
                            "raw_stdout": selected["raw_stdout"],
                            "raw_stderr": selected["raw_stderr"],
                            "workspace_before_sha256": workspace_before,
                            "workspace_after_sha256": workspace_after,
                            "workspace_mutated": workspace_before != workspace_after,
                            "state_file_updated": state_before != state_after,
                            "workspace_integrity_method": "digest",
                        }
                        regrade_result(result, case, workspace)
                        write_json(result_path, result)
                        saved_results.add(filename)
                        print(
                            f"  attempts={result['attempt_count']} "
                            f"pass={result['evaluation']['passed']} "
                            f"missing_orientation={result['evaluation']['missing_orientation_fact_count']} "
                            f"total_tokens={result['usage']['total_tokens']}",
                            flush=True,
                        )
    if len(saved_results) != expected_result_count:
        fail(
            "Run ended with "
            f"{len(saved_results)}/{expected_result_count} expected results"
        )
    environment_record.update(
        {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "result_count": len(saved_results),
        }
    )
    write_json(run_root / "environment.json", environment_record)
    write_reports(run_root)
    if not args.keep_workspaces:
        shutil.rmtree(run_root / "workspaces", ignore_errors=True)
    print(f"Markdown report: {run_root / 'REPORT.md'}")
    print(f"HTML report: {run_root / 'REPORT.html'}")
    return 0


def regrade_workspace_path(root: Path, result: dict[str, Any]) -> Path:
    agent = result.get("agent")
    case_id = result.get("case_id")
    condition = result.get("condition")
    repetition = result.get("repetition")
    if not isinstance(agent, str) or not agent:
        fail("A saved result has no agent")
    if not isinstance(case_id, str) or not case_id:
        fail("A saved result has no case_id")
    if condition not in {CONTROL, TREATMENT}:
        fail("A saved result has an invalid condition")
    if not isinstance(repetition, int) or isinstance(repetition, bool) or repetition < 1:
        fail("A saved result has an invalid repetition")
    return root / agent / case_id / str(condition) / f"r{repetition}"


def regrade_run(args: argparse.Namespace) -> int:
    run_root = args.run_root.resolve()
    if not (run_root / "runs").is_dir():
        fail(f"Run directory has no runs/ folder: {run_root}")
    manifest = load_manifest()
    stored_manifest = read_json(run_root / "manifest.json")
    if stored_manifest.get("id") != manifest.get("id"):
        fail("The saved run uses a different benchmark manifest")
    cases = {case["id"]: case for case in manifest["cases"]}
    result_paths = sorted((run_root / "runs").glob("*.json"))
    if not result_paths:
        fail(f"Run directory has no result files: {run_root}")
    pass_count = 0
    updated_results: list[tuple[Path, dict[str, Any]]] = []
    with tempfile.TemporaryDirectory(prefix="tlgf-regrade-") as directory:
        for result_path in result_paths:
            result = read_json(result_path)
            case_id = result.get("case_id")
            condition = result.get("condition")
            if case_id not in cases or condition not in {CONTROL, TREATMENT}:
                fail(f"Unknown case or condition in {result_path}")
            case = cases[str(case_id)]
            workspace = regrade_workspace_path(Path(directory), result)
            workspace.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(fixture_path(case), workspace)
            expected_prompt = case["prompt"] + manifest["conditions"][str(condition)][
                "prompt_suffix"
            ]
            if result.get("prompt") != expected_prompt:
                fail(f"Prompt mismatch in {result_path}")
            regrade_result(result, case, workspace)
            pass_count += int(bool(result["evaluation"]["passed"]))
            updated_results.append((result_path, result))
    for result_path, result in updated_results:
        write_json(result_path, result)
    environment_path = run_root / "environment.json"
    environment = read_json(environment_path)
    environment.update(
        {
            "regraded_at": datetime.now(timezone.utc).isoformat(),
            "grader_manifest_sha256": manifest_digest(),
            "result_parser_schema_version": PARSER_SCHEMA_VERSION,
        }
    )
    write_json(environment_path, environment)
    write_json(run_root / "grader-manifest.json", manifest)
    write_reports(run_root)
    print(f"Regraded {len(result_paths)} results without calling an agent")
    print(f"Automated gates: {pass_count}/{len(result_paths)}")
    print(f"HTML report: {run_root / 'REPORT.html'}")
    return 0


def doctor(env_file: Path) -> int:
    manifest = load_manifest()
    default_cases = select_cases(manifest, None)
    prepared_cases = [
        {
            "id": case["id"],
            "prepared": fixture_path(case, require_exists=False).is_dir(),
            "source_repository": case.get("source_repository"),
        }
        for case in manifest["cases"]
        if case.get("requires_preparation")
    ]
    environment, file_values = core.effective_environment(env_file)
    agents: dict[str, Any] = {}
    for agent in AGENTS:
        executable = core.find_executable(agent)
        agents[agent] = {
            "available": executable is not None,
            "executable": executable,
            "version": core.command_version(agent, executable) if executable else None,
        }
    result = {
        "benchmark": manifest["id"],
        "manifest_valid": True,
        "case_count": len(default_cases),
        "default_cases": [case["id"] for case in default_cases],
        "prepared_cases": prepared_cases,
        "fixtures_sha256": fixture_set_digest(manifest, default_cases),
        "skill_root": str(SKILL_ROOT),
        "skill_present": SKILL_ROOT.is_dir(),
        "agents": agents,
        "codex_global_tlgf_paths": [
            str(path) for path in core.codex_global_skill_paths("tlgf")
        ],
        "codex_global_skill_count": len(core.codex_all_global_skill_paths()),
        "env_file": str(env_file),
        "env_file_present": env_file.is_file(),
        "env_keys_loaded": sorted(file_values),
        "secret_values_logged": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser(
        "doctor", help="Validate fixtures and check local agents without calling a model"
    )
    doctor_parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)

    regrade_parser = subparsers.add_parser(
        "regrade", help="Reparse and regrade a saved run without calling a model"
    )
    regrade_parser.add_argument("run_root", type=Path)

    run_parser = subparsers.add_parser(
        "run", help="Run paired control and TLGF evaluations"
    )
    run_parser.add_argument("--agents", type=parse_csv, required=True)
    run_parser.add_argument("--cases", type=parse_csv)
    run_parser.add_argument("--repetitions", type=int, default=1)
    run_parser.add_argument("--max-attempts", type=int, default=2)
    run_parser.add_argument("--timeout", type=int, default=300)
    run_parser.add_argument("--seed", type=int, default=20260820)
    run_parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    run_parser.add_argument(
        "--resume-run",
        type=Path,
        help=(
            "Resume an interrupted run after verifying its frozen manifest, "
            "fixtures, skill, agents, models, and run settings"
        ),
    )
    run_parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    run_parser.add_argument("--claude-model", help="Pin the Claude model")
    run_parser.add_argument("--codex-model", help="Pin the Codex model")
    run_parser.add_argument("--agy-model", help="Pin the Agy model")
    run_parser.add_argument("--keep-workspaces", action="store_true")
    run_parser.add_argument("--manage-agy-settings", action="store_true")
    return parser


def validate_arguments(args: argparse.Namespace) -> None:
    if args.command != "run":
        return
    unknown = [agent for agent in args.agents if agent not in AGENTS]
    if unknown:
        fail(f"Unknown agents: {', '.join(unknown)}")
    if len(set(args.agents)) != len(args.agents):
        fail("Don't repeat an agent in --agents")
    if args.repetitions < 1:
        fail("--repetitions must be at least 1")
    if not 1 <= args.max_attempts <= 5:
        fail("--max-attempts must be between 1 and 5")
    if args.timeout < 30:
        fail("--timeout must be at least 30 seconds")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        validate_arguments(args)
        if args.command == "doctor":
            return doctor(args.env_file)
        if args.command == "regrade":
            return regrade_run(args)
        if args.command == "run":
            return run_benchmark(args)
        fail(f"Unknown command: {args.command}")
    except (BenchmarkError, core.BenchmarkError, renderer.ReportError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
