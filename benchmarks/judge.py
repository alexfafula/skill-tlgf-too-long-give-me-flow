#!/usr/bin/env python3
"""Blinded pairwise LLM judge for a completed benchmark run.

Usage:
    python3 benchmarks/judge.py RUN_DIRECTORY [--judges claude,codex] [--limit N]

The judge reads the saved control and treatment answers of a run, hides the
condition behind the same A/B assignment that BLIND_REVIEW.md uses, asks each
judge CLI to score both answers in both positions, and writes judge.json and
JUDGE.md next to the run's other reports. It never rewrites the run's results.

The judge sees only the task prompt, the review criteria, and the two answers.
It cannot inspect the repository or fixture, so its scores describe internal
consistency, criteria coverage, clarity, concision, tone, and traceability,
not verified factual accuracy. A visibly structured answer can still reveal the
condition, so treat the verdicts as model-judged, not as a human blind review.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

BENCHMARK_ROOT = Path(__file__).resolve().parent
JUDGES = ("claude", "codex")
JUDGE_MODEL_ENV = {"claude": "JUDGE_CLAUDE_MODEL", "codex": "JUDGE_CODEX_MODEL"}
INHERITED_ENV_KEYS = {
    "HOME",
    "LANG",
    "LOGNAME",
    "NO_COLOR",
    "PATH",
    "SHELL",
    "TERM",
    "TMPDIR",
    "USER",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
}
SHARED_DIMENSIONS = (
    ("accuracy", "No invented facts, commands, identifiers, or contradictions; claims stay inside the evidence the prompt allows."),
    ("completeness", "Covers every review criterion and every condition the reader needs; omits nothing required."),
    ("clarity", "A cold reader understands the answer on the first pass; structure matches the task."),
    ("concision", "No filler, repetition, research narration, or material outside the requested scope."),
    ("natural_tone", "Reads like a calm technical colleague: no canned praise, importance announcements, decorative metaphors, rhetorical scaffolding, or chatbot filler."),
    ("traceability", "Paths, symbols, commands, run names, and numbers are exact and attributable to a source."),
)
FLOW_DIMENSIONS = (
    ("orientation", "A cold reader can tell which project and workstream is active and what its current state is."),
    ("actionability", "The next action is concrete enough to execute without another orientation round."),
    ("restraint", "No invented state, no replayed history, no process narration, and no forced structure on a standalone question."),
)
PREFERENCES = ("A", "B", "tie", "neither")
EXECUTABLES: dict[str, str] = {}
EXECUTABLE_RETRIES = 8
EXECUTABLE_RETRY_SECONDS = 15


def resolve_executable(judge: str) -> str:
    """Find a judge CLI, waiting out a brief absence such as an auto-update."""
    for attempt in range(EXECUTABLE_RETRIES):
        found = shutil.which(judge)
        if found:
            EXECUTABLES[judge] = found
            return found
        cached = EXECUTABLES.get(judge)
        if cached and Path(cached).exists():
            return cached
        if attempt < EXECUTABLE_RETRIES - 1:
            time.sleep(EXECUTABLE_RETRY_SECONDS)
    fail(f"Judge CLI isn't available: {judge}")
    return ""


class JudgeError(RuntimeError):
    """A judge configuration or execution error."""


def fail(message: str) -> None:
    raise JudgeError(message)


def load_core() -> Any:
    for name in ("core.py", "run.py"):
        path = BENCHMARK_ROOT / name
        if path.is_file():
            spec = importlib.util.spec_from_file_location(f"benchmark_{path.stem}", path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    fail("Neither benchmarks/core.py nor benchmarks/run.py is available")
    return None


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"Cannot read {path}: {error}")
        return None


def blind_swap(run_id: str, agent: str, case_id: str, repetition: int) -> bool:
    """Match blind_label() in run.py and blind_swap() in tlgf/run.py."""
    material = f"{run_id}:{agent}:{case_id}:{repetition}:blind".encode()
    return hashlib.sha256(material).digest()[0] % 2 == 0


WORKSPACE_CONDITION_SEGMENT = re.compile(r"(workspaces/[^/\s\"'`()<>]+/)[^/\s\"'`()<>]+/")


def neutralize_workspace_paths(text: str) -> str:
    """Match neutralize_workspace_paths() in run.py: hide workspaces/<agent>/<condition>/ from the judge."""
    return WORKSPACE_CONDITION_SEGMENT.sub(r"\1CONDITION/", text)


def load_run(run_root: Path) -> dict[str, Any]:
    environment = read_json(run_root / "environment.json")
    manifest_path = run_root / "grader-manifest.json"
    if not manifest_path.is_file():
        manifest_path = run_root / "manifest.json"
    manifest = read_json(manifest_path)
    conditions = list(manifest.get("conditions", {}))
    treatment = [name for name in conditions if name != "control"]
    if "control" not in conditions or len(treatment) != 1:
        fail("The manifest must define exactly one control and one treatment condition")
    cases = {case["id"]: case for case in manifest.get("cases", [])}
    results = [read_json(path) for path in sorted((run_root / "runs").glob("*.json"))]
    grouped: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        key = (result["agent"], result["case_id"], int(result["repetition"]))
        grouped[key][result["condition"]] = result
    pairs = []
    for (agent, case_id, repetition), by_condition in sorted(grouped.items()):
        if set(by_condition) != {"control", treatment[0]}:
            continue
        if not all(str(item.get("response", "")).strip() for item in by_condition.values()):
            continue
        swap = blind_swap(environment["run_id"], agent, case_id, repetition)
        answer_a = by_condition[treatment[0]] if swap else by_condition["control"]
        answer_b = by_condition["control"] if swap else by_condition[treatment[0]]
        pairs.append(
            {
                "agent": agent,
                "case_id": case_id,
                "repetition": repetition,
                "swap": swap,
                "condition_of": {"A": answer_a["condition"], "B": answer_b["condition"]},
                "answers": {
                    "A": neutralize_workspace_paths(answer_a["response"]),
                    "B": neutralize_workspace_paths(answer_b["response"]),
                },
                "by_condition": {name: neutralize_workspace_paths(item["response"]) for name, item in by_condition.items()},
                "case": cases.get(case_id, {}),
            }
        )
    return {
        "run_id": environment["run_id"],
        "environment": environment,
        "treatment": treatment[0],
        "skill": str(manifest.get("skill", {}).get("name") or treatment[0]),
        "context": run_context(environment, manifest),
        "pairs": pairs,
    }


def run_context(environment: dict[str, Any], manifest: dict[str, Any]) -> str:
    repository = manifest.get("repository")
    if isinstance(repository, dict) and repository.get("name"):
        return (
            f"Both answers were produced from a read-only snapshot of {repository['name']} "
            f"at commit {environment.get('repository_commit') or repository.get('commit')}. "
            "You cannot open the repository; judge internal consistency, coverage of the criteria, and exact citations."
        )
    return (
        "Both answers were produced inside a small fixture workspace described by the fixture summary. "
        "You cannot open the fixture; judge whether each answer stays inside that evidence."
    )


def dimensions_for(skill: str) -> tuple[tuple[str, str], ...]:
    if skill == "tlgf":
        return SHARED_DIMENSIONS + FLOW_DIMENSIONS
    return SHARED_DIMENSIONS


def verdict_schema(dimensions: tuple[tuple[str, str], ...]) -> dict[str, Any]:
    scores = {
        "type": "object",
        "properties": {name: {"type": "integer", "minimum": 0, "maximum": 2} for name, _ in dimensions},
        "required": [name for name, _ in dimensions],
        "additionalProperties": False,
    }
    flags = {
        "type": "object",
        "properties": {"A": {"type": "boolean"}, "B": {"type": "boolean"}},
        "required": ["A", "B"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "scores": {
                "type": "object",
                "properties": {"A": scores, "B": scores},
                "required": ["A", "B"],
                "additionalProperties": False,
            },
            "critical_error": flags,
            "ai_mannerisms": {
                "type": "object",
                "properties": {
                    "A": {"type": "array", "items": {"type": "string"}},
                    "B": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["A", "B"],
                "additionalProperties": False,
            },
            "preference": {"type": "string", "enum": list(PREFERENCES)},
            "reason": {"type": "string"},
        },
        "required": ["scores", "critical_error", "ai_mannerisms", "preference", "reason"],
        "additionalProperties": False,
    }


def facts_schema(count: int) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "facts": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer", "minimum": 1, "maximum": count},
                        "conveyed": {"type": "boolean"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["index", "conveyed", "evidence"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["facts"],
        "additionalProperties": False,
    }


def build_facts_prompt(case: dict[str, Any], context: str, answer: str) -> str:
    facts = case.get("semantic_facts", [])
    lines = [
        "You are a careful cold reader checking which statements an answer conveys. You must not guess which tool or style produced the answer.",
        "",
        "## Task prompt",
        "",
        str(case.get("prompt", "")).strip(),
        "",
        "## Context",
        "",
        context,
    ]
    if case.get("fixture_summary"):
        lines.extend(["", f"Fixture summary: {case['fixture_summary']}"])
    lines.extend(["", "## Answer", "", answer.strip(), "", "## Statements", ""])
    lines.extend(f"{index}. {fact}" for index, fact in enumerate(facts, start=1))
    lines.extend(
        [
            "",
            "For every statement, decide whether the answer conveys it explicitly or by clear implication. A statement that the answer contradicts, omits, or leaves ambiguous is not conveyed. Quote the shortest supporting or contradicting words from the answer as evidence.",
            "",
            f"Return only a JSON object with a facts array of exactly {len(facts)} items, each with index, conveyed, and evidence.",
        ]
    )
    return "\n".join(lines)


def parse_facts(verdict: dict[str, Any] | None, count: int) -> list[bool] | None:
    if not isinstance(verdict, dict) or not isinstance(verdict.get("facts"), list):
        return None
    conveyed: dict[int, bool] = {}
    for item in verdict["facts"]:
        if isinstance(item, dict) and isinstance(item.get("index"), int) and isinstance(item.get("conveyed"), bool):
            conveyed[item["index"]] = item["conveyed"]
    if set(conveyed) != set(range(1, count + 1)):
        return None
    return [conveyed[index] for index in range(1, count + 1)]


def build_prompt(pair: dict[str, Any], context: str, dimensions: tuple[tuple[str, str], ...], order: tuple[str, str]) -> str:
    first, second = order
    case = pair["case"]
    criteria = case.get("review_criteria", [])
    lines = [
        "You are a blinded cold reader grading two answers to the same task. You did not see the conversation that produced them, and you must not guess which tool or style produced either answer.",
        "",
        "## Task prompt",
        "",
        str(case.get("prompt", "")).strip(),
        "",
        "## Context",
        "",
        context,
    ]
    if case.get("fixture_summary"):
        lines.extend(["", f"Fixture summary: {case['fixture_summary']}"])
    if criteria:
        lines.extend(["", "## Review criteria", ""])
        lines.extend(f"- {criterion}" for criterion in criteria)
    lines.extend(["", "## Answer A", "", pair["answers"][first].strip(), "", "## Answer B", "", pair["answers"][second].strip(), ""])
    lines.extend(["## Scoring", "", "Score each answer on every dimension from 0 to 2: 0 = absent or materially wrong, 1 = present but incomplete, ambiguous, or inefficient, 2 = correct, sufficient, and easy to use."])
    lines.extend(f"- {name}: {description}" for name, description in dimensions)
    lines.extend(
        [
            "",
            "Mark critical_error true when an answer invents a fact, command, path, or result, weakens a required condition, or omits something the criteria require.",
            "List concrete AI mannerisms you notice in each answer (quote a few words each); use an empty list when there are none.",
            "Then answer this question: which answer would let a reader continue the task correctly with less rereading and reconstruction? Choose A, B, tie, or neither (when both are unusable). Cite the specific missing or helpful information in reason.",
            "",
            "Return only a JSON object with keys scores, critical_error, ai_mannerisms, preference, and reason.",
        ]
    )
    return "\n".join(lines)


def judge_environment(judge: str, environment: dict[str, str]) -> dict[str, str]:
    safe = {key: value for key, value in environment.items() if key in INHERITED_ENV_KEYS or key.startswith("LC_")}
    safe["NO_COLOR"] = "1"
    model_key = JUDGE_MODEL_ENV.get(judge)
    if model_key and environment.get(model_key):
        safe[model_key] = environment[model_key]
    return safe


def judge_command(judge: str, prompt: str, model: str | None, schema_path: Path, workdir: Path) -> list[str]:
    executable = resolve_executable(judge)
    if judge == "claude":
        command = [
            executable,
            "-p",
            "--output-format",
            "json",
            "--no-session-persistence",
            "--permission-mode",
            "dontAsk",
            "--no-chrome",
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
            "--setting-sources",
            "project",
            "--disable-slash-commands",
            "--tools",
            "",
            "--effort",
            "medium",
            "--json-schema",
            schema_path.read_text(encoding="utf-8"),
        ]
        if model:
            command.extend(["--model", model])
        command.extend(["--", prompt])
        return command
    if judge == "codex":
        command = [
            executable,
            "-a",
            "never",
            "-s",
            "read-only",
            "-C",
            str(workdir),
            "-c",
            'model_reasoning_effort="medium"',
        ]
        if model:
            command.extend(["--model", model])
        command.extend(
            [
                "exec",
                "--json",
                "--ephemeral",
                "--skip-git-repo-check",
                "--ignore-user-config",
                "--ignore-rules",
                "--output-schema",
                str(schema_path),
                prompt,
            ]
        )
        return command
    fail(f"Unknown judge: {judge}")
    return []


def extract_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    candidates = [stripped]
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
    candidates.extend(fenced)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        candidates.append(stripped[start : end + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def parse_verdict(judge: str, stdout: str, core: Any) -> tuple[dict[str, Any] | None, str]:
    events = core.json_events(stdout)
    if judge == "claude":
        for event in reversed(events):
            if event.get("type") == "result":
                structured = event.get("structured_output")
                if isinstance(structured, dict):
                    return structured, "structured_output"
                result = event.get("result")
                if isinstance(result, str):
                    parsed = extract_json_object(result)
                    if parsed is not None:
                        return parsed, "result-text"
        parsed = extract_json_object(stdout)
        return parsed, "stdout"
    response = core.extract_response(judge, events) if events else ""
    parsed = extract_json_object(response or stdout)
    return parsed, "agent-message"


def validate_verdict(verdict: dict[str, Any], dimensions: tuple[tuple[str, str], ...]) -> str | None:
    if verdict.get("preference") not in PREFERENCES:
        return "preference must be A, B, tie, or neither"
    scores = verdict.get("scores")
    if not isinstance(scores, dict):
        return "scores missing"
    for label in ("A", "B"):
        block = scores.get(label)
        if not isinstance(block, dict):
            return f"scores.{label} missing"
        for name, _ in dimensions:
            value = block.get(name)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 2:
                return f"scores.{label}.{name} must be an integer from 0 to 2"
    return None


def run_judge(
    judge: str,
    prompt: str,
    *,
    model: str | None,
    schema: dict[str, Any],
    environment: dict[str, str],
    timeout_seconds: int,
    core: Any,
    command_override: list[str] | None = None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="benchmark-judge-") as directory:
        workdir = Path(directory)
        schema_path = workdir / "verdict.schema.json"
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        if command_override:
            command = [*command_override]
            stdin_text = prompt
        else:
            command = judge_command(judge, prompt, model, schema_path, workdir)
            stdin_text = None
        started = time.monotonic()
        for attempt in range(2):
            try:
                completed = subprocess.run(
                    command,
                    cwd=workdir,
                    env=judge_environment(judge, environment),
                    input=stdin_text,
                    stdin=None if stdin_text is not None else subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                )
                stdout, stderr, exit_code, timed_out = completed.stdout, completed.stderr, completed.returncode, False
            except FileNotFoundError:
                stdout, stderr, exit_code, timed_out = "", "executable vanished", 127, False
            except subprocess.TimeoutExpired as error:
                stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else (error.stdout or "")
                stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else (error.stderr or "")
                exit_code, timed_out = None, True
            vanished = exit_code == 127 or (exit_code not in (0, None) and not stdout.strip())
            if vanished and attempt == 0 and not command_override:
                time.sleep(EXECUTABLE_RETRY_SECONDS)
                command = judge_command(judge, prompt, model, schema_path, workdir)
                continue
            break
        duration = round(time.monotonic() - started, 3)
    if command_override:
        verdict, source = extract_json_object(stdout), "override-stdout"
        events: list[dict[str, Any]] = []
    else:
        verdict, source = parse_verdict(judge, stdout, core)
        events = core.json_events(stdout)
    host_problem = None
    for event in events:
        status = event.get("api_error_status")
        if isinstance(status, int) and status >= 400:
            host_problem = f"host error {status}: {str(event.get('result') or '')[:80]}"
        subtype = str(event.get("subtype") or "")
        if subtype.startswith("error"):
            host_problem = host_problem or f"host error: {subtype}"
    usage = core.extract_usage(judge, events) if events and not command_override else None
    runtime_model = core.extract_model(events, model) if events and not command_override else model
    return {
        "judge": judge,
        "requested_model": model,
        "runtime_model": runtime_model,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_seconds": duration,
        "usage": usage,
        "verdict": verdict,
        "verdict_source": source,
        "host_problem": host_problem,
        "raw_stdout": stdout,
        "raw_stderr": stderr[-4000:],
    }


def map_preference(preference: str, order: tuple[str, str], condition_of: dict[str, str]) -> str:
    """Translate a positional preference into a condition name or tie/neither."""
    if preference in ("tie", "neither"):
        return preference
    shown = {"A": order[0], "B": order[1]}
    return condition_of[shown[preference]]


def map_scores(scores: dict[str, Any], order: tuple[str, str], condition_of: dict[str, str]) -> dict[str, dict[str, int]]:
    shown = {"A": order[0], "B": order[1]}
    return {condition_of[shown[label]]: dict(scores[label]) for label in ("A", "B")}


def combine_orders(verdicts: list[dict[str, Any]], treatment: str) -> dict[str, Any]:
    """Reduce one judge's two positional verdicts to one pair verdict."""
    preferences = [item["preference_condition"] for item in verdicts if item.get("preference_condition")]
    if not preferences:
        return {"outcome": "unavailable", "consistent": None}
    if len(set(preferences)) == 1:
        outcome = preferences[0]
        return {"outcome": outcome, "consistent": len(preferences) > 1 or None}
    return {"outcome": "position-dependent", "consistent": False}


def summarize(run: dict[str, Any], judged: list[dict[str, Any]], judges: list[str]) -> dict[str, Any]:
    treatment = run["treatment"]
    per_judge_counts: dict[str, dict[str, int]] = {judge: defaultdict(int) for judge in judges}
    per_agent_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    agreement = {"unanimous": 0, "split": 0, "pairs_with_all_judges": 0}
    score_sums: dict[str, dict[str, dict[str, float]]] = {judge: {"control": defaultdict(float), treatment: defaultdict(float)} for judge in judges}
    score_counts: dict[str, dict[str, int]] = {judge: {"control": 0, treatment: 0} for judge in judges}
    for pair in judged:
        outcomes = []
        for judge in judges:
            block = pair["judges"].get(judge)
            if not block:
                continue
            outcome = block["combined"]["outcome"]
            per_judge_counts[judge][outcome] += 1
            outcomes.append(outcome)
            for verdict in block["verdicts"]:
                mapped = verdict.get("scores_by_condition")
                if not mapped:
                    continue
                for condition, scores in mapped.items():
                    for name, value in scores.items():
                        score_sums[judge][condition][name] += value
                    score_counts[judge][condition] += 1
        if len(outcomes) == len(judges) and judges:
            agreement["pairs_with_all_judges"] += 1
            if len(set(outcomes)) == 1:
                agreement["unanimous"] += 1
                per_agent_counts[pair["agent"]][outcomes[0]] += 1
            else:
                agreement["split"] += 1
                per_agent_counts[pair["agent"]]["split"] += 1
    mean_scores = {
        judge: {
            condition: {name: round(total / score_counts[judge][condition], 2) for name, total in sums.items()}
            for condition, sums in by_condition.items()
            if score_counts[judge][condition]
        }
        for judge, by_condition in score_sums.items()
    }
    coverage_sums: dict[str, dict[str, list[float]]] = {judge: defaultdict(list) for judge in judges}
    coverage_by_agent: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for pair in judged:
        facts = pair.get("facts")
        if not facts:
            continue
        for judge, per_condition in facts["by_judge"].items():
            for condition, result in per_condition.items():
                if result.get("coverage") is not None:
                    coverage_sums[judge][condition].append(result["coverage"])
                    coverage_by_agent[pair["agent"]][f"{judge}/{condition}"].append(result["coverage"])
    fact_coverage = {
        judge: {condition: {"mean": round(sum(values) / len(values), 2), "answers": len(values)} for condition, values in by_condition.items() if values}
        for judge, by_condition in coverage_sums.items()
    }
    fact_coverage_by_agent = {
        agent: {key: round(sum(values) / len(values), 2) for key, values in by_key.items() if values}
        for agent, by_key in coverage_by_agent.items()
    }
    return {
        "per_judge": {judge: dict(counts) for judge, counts in per_judge_counts.items()},
        "per_agent_unanimous": {agent: dict(counts) for agent, counts in per_agent_counts.items()},
        "agreement": agreement,
        "mean_scores": mean_scores,
        "fact_coverage": fact_coverage,
        "fact_coverage_by_agent": fact_coverage_by_agent,
    }


def write_markdown(run_root: Path, run: dict[str, Any], judged: list[dict[str, Any]], summary: dict[str, Any], judges: list[str]) -> None:
    treatment = run["treatment"]
    lines = [
        f"# Blinded LLM judge for `{run['run_id']}`",
        "",
        "> [!NOTE]",
        "> Model-judged verdicts. Judges saw the prompt, the review criteria, and both answers with hidden conditions, in both positions. They could not inspect the repository or fixture, and a visibly structured answer can reveal the condition. Complete the human blind review before publishing a claim.",
        "",
        f"Judges: {', '.join(judges)}. Pairs judged: {len(judged)}.",
        "",
        "## Outcome per judge",
        "",
        f"| Judge | {treatment} preferred | control preferred | tie | neither | position-dependent | unavailable |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for judge in judges:
        counts = summary["per_judge"].get(judge, {})
        lines.append(
            f"| {judge} | {counts.get(treatment, 0)} | {counts.get('control', 0)} | {counts.get('tie', 0)} | {counts.get('neither', 0)} | {counts.get('position-dependent', 0)} | {counts.get('unavailable', 0)} |"
        )
    agreement = summary["agreement"]
    lines.extend(
        [
            "",
            f"Judge agreement: {agreement['unanimous']} unanimous and {agreement['split']} split of {agreement['pairs_with_all_judges']} pairs with every judge's verdict.",
            "",
            "## Unanimous outcomes per agent",
            "",
            f"| Agent | {treatment} preferred | control preferred | tie | neither | position-dependent | split |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for agent, counts in sorted(summary["per_agent_unanimous"].items()):
        lines.append(
            f"| {agent} | {counts.get(treatment, 0)} | {counts.get('control', 0)} | {counts.get('tie', 0)} | {counts.get('neither', 0)} | {counts.get('position-dependent', 0)} | {counts.get('split', 0)} |"
        )
    lines.extend(["", "## Mean dimension scores (0–2)", ""])
    for judge in judges:
        by_condition = summary["mean_scores"].get(judge, {})
        if not by_condition:
            continue
        names = sorted({name for scores in by_condition.values() for name in scores})
        lines.extend([f"### {judge}", "", "| Condition | " + " | ".join(names) + " |", "| --- |" + " ---: |" * len(names)])
        for condition in ("control", treatment):
            scores = by_condition.get(condition)
            if scores:
                lines.append(f"| {condition} | " + " | ".join(str(scores.get(name, "—")) for name in names) + " |")
        lines.append("")
    if summary.get("fact_coverage"):
        lines.extend(["## Semantic fact coverage", "", "Share of a case's semantic_facts statements that an answer conveys, judged per answer without a pair.", "", "| Judge | Condition | Mean coverage | Answers |", "| --- | --- | ---: | ---: |"])
        for judge in judges:
            for condition in ("control", treatment):
                block = summary["fact_coverage"].get(judge, {}).get(condition)
                if block:
                    lines.append(f"| {judge} | {condition} | {block['mean']} | {block['answers']} |")
        lines.extend(["", "| Agent | " + " | ".join(f"{judge}/{condition}" for judge in judges for condition in ("control", treatment)) + " |", "| --- |" + " ---: |" * (2 * len(judges))])
        for agent, by_key in sorted(summary["fact_coverage_by_agent"].items()):
            lines.append(f"| {agent} | " + " | ".join(str(by_key.get(f"{judge}/{condition}", "—")) for judge in judges for condition in ("control", treatment)) + " |")
        lines.append("")
    lines.extend(["## Pairs", "", "| Agent | Case | Rep | Judge | Order A/B | Order B/A | Combined | Critical error | Reason |", "| --- | --- | ---: | --- | --- | --- | --- | --- | --- |"])
    for pair in judged:
        for judge in judges:
            block = pair["judges"].get(judge)
            if not block:
                continue
            verdicts = block["verdicts"]
            first = verdicts[0].get("preference_condition") or "—"
            second = verdicts[1].get("preference_condition") if len(verdicts) > 1 else "—"
            errors = sorted({condition for verdict in verdicts for condition, flag in (verdict.get("critical_error_by_condition") or {}).items() if flag})
            reason = (verdicts[0].get("verdict") or {}).get("reason", "") if verdicts else ""
            reason = re.sub(r"\s+", " ", str(reason)).strip()[:220]
            lines.append(
                f"| {pair['agent']} | {pair['case_id']} | {pair['repetition']} | {judge} | {first} | {second or '—'} | {block['combined']['outcome']} | {', '.join(errors) or 'none'} | {reason} |"
            )
    (run_root / "JUDGE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def judge_run(args: argparse.Namespace) -> int:
    core = load_core()
    run_root = args.run.resolve()
    run = load_run(run_root)
    dimensions = dimensions_for(run["skill"])
    schema = verdict_schema(dimensions)
    judges = [name.strip() for name in args.judges.split(",") if name.strip()]
    unknown = [judge for judge in judges if judge not in JUDGES]
    if unknown and not args.judge_command:
        fail(f"Unknown judges: {unknown}")
    environment = dict(os.environ)
    env_file = getattr(args, "env_file", None)
    if env_file is None:
        env_file = BENCHMARK_ROOT.parent / ".env"
    if env_file.is_file() and hasattr(core, "parse_env_file"):
        file_env = core.parse_env_file(env_file)
        for key, value in file_env.items():
            environment.setdefault(key, value)
    models = {"claude": args.claude_model or environment.get("JUDGE_CLAUDE_MODEL"), "codex": args.codex_model or environment.get("JUDGE_CODEX_MODEL")}
    recorded_models = dict(models)
    if not recorded_models.get("codex") and hasattr(core, "configured_codex_model"):
        recorded_models["codex"] = core.configured_codex_model()
    pairs = run["pairs"]
    if args.agent:
        pairs = [pair for pair in pairs if pair["agent"] == args.agent]
    if args.limit:
        pairs = pairs[: args.limit]
    if not pairs:
        fail("No complete control/treatment pairs to judge")
    orders: list[tuple[str, str]] = [("A", "B")] if args.single_order else [("A", "B"), ("B", "A")]
    override = args.judge_command.split() if args.judge_command else None
    progress_path = run_root / "judge-progress.json"
    previous: dict[str, dict[str, Any]] = {}
    if args.resume:
        source_path = progress_path if progress_path.is_file() else run_root / "judge.json"
        if source_path.is_file():
            for item in read_json(source_path).get("pairs", []):
                previous[f"{item['agent']}|{item['case_id']}|{item['repetition']}"] = item
    judged: list[dict[str, Any]] = []
    for index, pair in enumerate(pairs, start=1):
        key = f"{pair['agent']}|{pair['case_id']}|{pair['repetition']}"
        earlier = previous.get(key) or {}
        facts_needed = bool(args.facts and pair["case"].get("semantic_facts"))
        entry = {
            "agent": pair["agent"],
            "case_id": pair["case_id"],
            "repetition": pair["repetition"],
            "condition_of": pair["condition_of"],
            "judges": {},
        }
        for judge in judges:
            verdicts = []
            reusable = {
                item.get("order"): item
                for item in (earlier.get("judges", {}).get(judge, {}) or {}).get("verdicts", [])
                if item.get("preference_condition") and not item.get("verdict_problem")
            }
            for order in orders:
                if "".join(order) in reusable:
                    verdicts.append(reusable["".join(order)])
                    continue
                prompt = build_prompt(pair, run["context"], dimensions, order)
                if args.dry_run:
                    print(f"--- {judge} {pair['agent']}/{pair['case_id']}/r{pair['repetition']} order {order[0]}{order[1]} ---")
                    print(prompt)
                    continue
                print(f"[{judge}] {pair['agent']} {pair['case_id']} r{pair['repetition']} order {order[0]}{order[1]} ({index}/{len(pairs)})", flush=True)
                result = run_judge(
                    judge,
                    prompt,
                    model=models.get(judge),
                    schema=schema,
                    environment=environment,
                    timeout_seconds=args.timeout,
                    core=core,
                    command_override=override,
                )
                verdict = result["verdict"]
                problem = validate_verdict(verdict, dimensions) if isinstance(verdict, dict) else "no JSON verdict"
                if problem and result.get("host_problem"):
                    problem = result["host_problem"]
                if problem:
                    result["verdict_problem"] = problem
                    result["preference_condition"] = None
                    print(f"  unusable verdict: {problem}", flush=True)
                else:
                    result["preference_condition"] = map_preference(verdict["preference"], order, pair["condition_of"])
                    result["scores_by_condition"] = map_scores(verdict["scores"], order, pair["condition_of"])
                    flags = verdict.get("critical_error") or {}
                    shown = {"A": order[0], "B": order[1]}
                    result["critical_error_by_condition"] = {pair["condition_of"][shown[label]]: bool(flags.get(label)) for label in ("A", "B")}
                    print(f"  preference={result['preference_condition']}", flush=True)
                result["order"] = f"{order[0]}{order[1]}"
                verdicts.append(result)
            if args.dry_run:
                continue
            entry["judges"][judge] = {"verdicts": verdicts, "combined": combine_orders(verdicts, run["treatment"])}
        facts = pair["case"].get("semantic_facts", [])
        if args.facts and facts and not args.dry_run:
            entry["facts"] = {"statements": facts, "by_judge": {}}
            for judge in judges:
                per_condition: dict[str, Any] = {}
                earlier_facts = ((earlier.get("facts") or {}).get("by_judge", {}) or {}).get(judge, {}) or {}
                for condition, answer in pair["by_condition"].items():
                    if earlier_facts.get(condition, {}).get("coverage") is not None:
                        per_condition[condition] = earlier_facts[condition]
                        continue
                    print(f"[{judge}] facts {pair['agent']} {pair['case_id']} r{pair['repetition']} {condition}", flush=True)
                    result = run_judge(
                        judge,
                        build_facts_prompt(pair["case"], run["context"], answer),
                        model=models.get(judge),
                        schema=facts_schema(len(facts)),
                        environment=environment,
                        timeout_seconds=args.timeout,
                        core=core,
                        command_override=override,
                    )
                    conveyed = parse_facts(result.get("verdict"), len(facts))
                    result["conveyed"] = conveyed
                    result["coverage"] = round(sum(conveyed) / len(conveyed), 2) if conveyed else None
                    per_condition[condition] = result
                    print(f"  coverage={result['coverage']}", flush=True)
                entry["facts"]["by_judge"][judge] = per_condition
        judged.append(entry)
        if not args.dry_run:
            progress_path.write_text(json.dumps({"run_id": run["run_id"], "pairs": judged}, ensure_ascii=False), encoding="utf-8")
    if args.dry_run:
        return 0
    summary = summarize(run, judged, judges)
    payload = {
        "schema_version": 1,
        "run_id": run["run_id"],
        "treatment": run["treatment"],
        "skill": run["skill"],
        "judges": judges,
        "judge_models": {judge: recorded_models.get(judge) for judge in judges},
        "judge_reasoning_effort": {judge: "medium" for judge in judges},
        "orders": ["".join(order) for order in orders],
        "dimensions": [name for name, _ in dimensions],
        "pair_count": len(judged),
        "summary": summary,
        "pairs": judged,
    }
    (run_root / "judge.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(run_root, run, judged, summary, judges)
    progress_path.unlink(missing_ok=True)
    print(f"Judge report: {run_root / 'JUDGE.md'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Blinded pairwise LLM judge for a completed benchmark run")
    parser.add_argument("run", type=Path, help="Run directory that contains runs/, manifest.json, and environment.json")
    parser.add_argument("--judges", default="claude,codex", help="Comma-separated judge CLIs (default: claude,codex)")
    parser.add_argument("--claude-model", help="Pin the Claude judge model (or set JUDGE_CLAUDE_MODEL)")
    parser.add_argument("--codex-model", help="Pin the Codex judge model (or set JUDGE_CODEX_MODEL)")
    parser.add_argument("--agent", help="Judge only pairs produced by this agent")
    parser.add_argument("--limit", type=int, help="Judge at most this many pairs")
    parser.add_argument("--single-order", action="store_true", help="Skip the position swap (cheaper, no position-effect check)")
    parser.add_argument("--facts", action="store_true", help="Also grade each answer's coverage of the case's semantic_facts")
    parser.add_argument("--resume", action="store_true", help="Skip pairs already recorded in judge-progress.json from an interrupted run")
    parser.add_argument("--timeout", type=int, default=300, help="Seconds per judge call")
    parser.add_argument("--dry-run", action="store_true", help="Print the judge prompts without calling a model")
    parser.add_argument("--judge-command", help="Test hook: run this command with the prompt on stdin and read the JSON verdict from stdout")
    parser.add_argument("--env-file", type=Path, default=BENCHMARK_ROOT.parent / ".env", help="Path to .env file (default: .env in repository root)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return judge_run(args)
    except JudgeError as error:
        print(f"Judge failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
