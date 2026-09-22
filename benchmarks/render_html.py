#!/usr/bin/env python3
"""Render a self-contained side-by-side HTML report for a benchmark run."""

from __future__ import annotations

import argparse
import difflib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


BENCHMARK_ROOT = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = BENCHMARK_ROOT / "report_template.html"


class ReportError(RuntimeError):
    """A report input or rendering error."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ReportError(f"Can't read JSON from {path}: {error}") from error
    if not isinstance(value, dict):
        raise ReportError(f"Expected a JSON object in {path}")
    return value


def finite_number(value: Any) -> float | int | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def result_metric(result: dict[str, Any], name: str) -> float | int | None:
    if name == "words":
        return finite_number(result.get("response_words", result.get("words")))
    view_names = {
        "output_tokens": "outputTokens",
        "final_step_output_tokens": "finalStepOutputTokens",
        "input_tokens": "inputTokens",
        "total_tokens": "totalTokens",
        "visible_words": "visibleWords",
    }
    if name in view_names and view_names[name] in result:
        return finite_number(result.get(view_names[name]))
    usage = result.get("usage")
    if isinstance(usage, dict):
        return finite_number(usage.get(name))
    return None


def reduction(control: float | int | None, tlgd: float | int | None) -> float | None:
    if control is None or tlgd is None or control == 0:
        return None
    return round((control - tlgd) / control * 100, 2)


def sum_metric(results: Iterable[dict[str, Any]], name: str) -> float | int | None:
    values = [result_metric(result, name) for result in results]
    if not values or any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def condition_passed(result: dict[str, Any]) -> bool:
    evaluation = result.get("evaluation")
    return bool(isinstance(evaluation, dict) and evaluation.get("passed"))


def benchmark_conditions(manifest: dict[str, Any]) -> tuple[str, str, str, str]:
    condition_config = manifest.get("conditions")
    if not isinstance(condition_config, dict) or len(condition_config) != 2:
        raise ReportError("The manifest must define exactly two benchmark conditions")
    report = manifest.get("report")
    if not isinstance(report, dict):
        report = {}
    control = str(report.get("control_condition") or "control")
    if control not in condition_config:
        raise ReportError(f"Unknown control condition: {control}")
    treatment = report.get("treatment_condition")
    if not isinstance(treatment, str) or treatment not in condition_config:
        candidates = [name for name in condition_config if name != control]
        treatment = candidates[0]
    control_config = condition_config.get(control)
    treatment_config = condition_config.get(treatment)
    control_label = (
        str(control_config.get("display_name") or "Control")
        if isinstance(control_config, dict)
        else "Control"
    )
    treatment_label = (
        str(treatment_config.get("display_name") or treatment.upper())
        if isinstance(treatment_config, dict)
        else treatment.upper()
    )
    return control, treatment, control_label, treatment_label


def attempt_view(attempt: dict[str, Any]) -> dict[str, Any]:
    usage = attempt.get("usage") if isinstance(attempt.get("usage"), dict) else {}
    return {
        "number": finite_number(attempt.get("attempt_number")) or 1,
        "status": str(attempt.get("agent_status") or "UNKNOWN"),
        "response": str(attempt.get("response") or ""),
        "visibleText": str(attempt.get("visible_text") or attempt.get("response") or ""),
        "outputTokens": finite_number(usage.get("output_tokens")),
        "inputTokens": finite_number(usage.get("input_tokens")),
        "totalTokens": finite_number(usage.get("total_tokens")),
        "durationSeconds": finite_number(attempt.get("duration_seconds")),
        "finishReason": attempt.get("finish_reason"),
    }


def result_view(result: dict[str, Any], result_path: Path, run_root: Path) -> dict[str, Any]:
    usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
    final_step_usage = (
        result.get("final_step_usage")
        if isinstance(result.get("final_step_usage"), dict)
        else {}
    )
    evaluation = (
        result.get("evaluation") if isinstance(result.get("evaluation"), dict) else {}
    )
    checks = evaluation.get("checks") if isinstance(evaluation.get("checks"), dict) else {}
    budget_tracked = isinstance(evaluation.get("budget_passed"), bool)
    attempts = result.get("attempts") if isinstance(result.get("attempts"), list) else []
    return {
        "condition": str(result.get("condition") or ""),
        "prompt": str(result.get("prompt") or ""),
        "response": str(result.get("response") or ""),
        "visibleText": str(result.get("visible_text") or result.get("response") or ""),
        "words": result_metric(result, "words"),
        "markdownSourceWords": finite_number(
            result.get("markdown_source_words", result.get("response_words"))
        ),
        "visibleWords": finite_number(result.get("visible_text_words", result.get("response_words"))),
        "characters": finite_number(result.get("response_characters")),
        "outputTokens": finite_number(usage.get("output_tokens")),
        "finalStepOutputTokens": finite_number(final_step_usage.get("output_tokens")),
        "inputTokens": finite_number(usage.get("input_tokens")),
        "cachedInputTokens": finite_number(usage.get("cached_input_tokens")),
        "reasoningTokens": finite_number(usage.get("reasoning_tokens")),
        "totalTokens": finite_number(usage.get("total_tokens")),
        "durationSeconds": finite_number(result.get("duration_seconds")),
        "toolCalls": finite_number(result.get("tool_call_count")),
        "attemptCount": finite_number(result.get("attempt_count")) or 1,
        "retryCount": finite_number(result.get("retry_count")) or 0,
        "attemptStatuses": result.get("attempt_statuses", []),
        "attempts": [attempt_view(attempt) for attempt in attempts if isinstance(attempt, dict)],
        "selectedAttemptOutputTokens": finite_number(
            result.get("selected_attempt_usage", {}).get("output_tokens")
            if isinstance(result.get("selected_attempt_usage"), dict)
            else None
        ),
        "gatePassed": condition_passed(result),
        "budgetTracked": budget_tracked,
        "budgetPassed": bool(evaluation.get("budget_passed")) if budget_tracked else True,
        "checks": checks,
        "status": str(result.get("agent_status") or "UNKNOWN"),
        "exitCode": finite_number(result.get("exit_code")),
        "timedOut": bool(result.get("timed_out")),
        "finishReason": result.get("finish_reason"),
        "workspaceMutated": bool(result.get("workspace_mutated")),
        "requestedModel": result.get("requested_model"),
        "runtimeModel": result.get("runtime_model"),
        "agentVersion": result.get("agent_version"),
        "rawJsonUrl": result_path.relative_to(run_root).as_posix(),
    }


def unified_diff(control: str, treatment: str, tofile: str = "tlgf") -> str:
    lines = difflib.unified_diff(
        control.splitlines(),
        treatment.splitlines(),
        fromfile="control",
        tofile=tofile,
        lineterm="",
        n=3,
    )
    return "\n".join(lines)


def load_results(run_root: Path) -> list[tuple[Path, dict[str, Any]]]:
    runs_root = run_root / "runs"
    if not runs_root.is_dir():
        raise ReportError(f"Run directory has no runs/ folder: {run_root}")
    results = [(path, read_json(path)) for path in sorted(runs_root.glob("*.json"))]
    if not results:
        raise ReportError(f"Run directory has no result JSON files: {run_root}")
    return results


def build_report_data(run_root: Path) -> dict[str, Any]:
    run_root = run_root.resolve()
    grader_manifest = run_root / "grader-manifest.json"
    manifest = read_json(
        grader_manifest if grader_manifest.is_file() else run_root / "manifest.json"
    )
    environment = read_json(run_root / "environment.json")
    cases = {
        str(case.get("id")): case
        for case in manifest.get("cases", [])
        if isinstance(case, dict) and case.get("id")
    }
    case_order = {case_id: index for index, case_id in enumerate(cases)}
    condition_config = manifest.get("conditions")
    if not isinstance(condition_config, dict):
        condition_config = {}
    control_condition, treatment_condition, control_label, treatment_label = (
        benchmark_conditions(manifest)
    )
    conditions_order = (control_condition, treatment_condition)

    indexed: dict[tuple[str, str, int], dict[str, tuple[Path, dict[str, Any]]]] = (
        defaultdict(dict)
    )
    all_results = load_results(run_root)
    for path, result in all_results:
        agent = str(result.get("agent") or "unknown")
        case_id = str(result.get("case_id") or "unknown")
        repetition = int(result.get("repetition") or 0)
        condition = str(result.get("condition") or "")
        if condition not in conditions_order:
            raise ReportError(f"Unknown condition {condition!r} in {path}")
        indexed[(agent, case_id, repetition)][condition] = (path, result)

    pairs: list[dict[str, Any]] = []
    ordered_results = sorted(
        indexed.items(),
        key=lambda item: (
            case_order.get(item[0][1], len(case_order)),
            item[0][0],
            item[0][2],
        ),
    )
    for (agent, case_id, repetition), conditions in ordered_results:
        if any(condition not in conditions for condition in conditions_order):
            continue
        control_path, control_result = conditions[control_condition]
        tlgd_path, tlgd_result = conditions[treatment_condition]
        case = cases.get(case_id, {})
        control = result_view(control_result, control_path, run_root)
        tlgd = result_view(tlgd_result, tlgd_path, run_root)
        pair_id = f"{agent}-{case_id}-r{repetition}"
        pairs.append(
            {
                "id": pair_id,
                "agent": agent,
                "caseId": case_id,
                "caseMode": case.get("mode"),
                "difficulty": case.get("difficulty", "standard"),
                "repetition": repetition,
                "basePrompt": str(case.get("prompt") or ""),
                "controlSuffix": str(
                    condition_config.get(control_condition, {}).get("prompt_suffix", "")
                    if isinstance(condition_config.get(control_condition), dict)
                    else ""
                ),
                "treatmentSuffix": str(
                    condition_config.get(treatment_condition, {}).get("prompt_suffix", "")
                    if isinstance(condition_config.get(treatment_condition), dict)
                    else ""
                ),
                "tlgfSuffix": str(
                    condition_config.get(treatment_condition, {}).get("prompt_suffix", "")
                    if isinstance(condition_config.get(treatment_condition), dict)
                    else ""
                ),
                "tlgdSuffix": str(
                    condition_config.get(treatment_condition, {}).get("prompt_suffix", "")
                    if isinstance(condition_config.get(treatment_condition), dict)
                    else ""
                ),
                "fixture": case.get("fixture"),
                "fixtureSummary": case.get("fixture_summary"),
                "reviewCriteria": case.get("review_criteria", []),
                "control": control,
                "treatment": tlgd,
                "tlgf": tlgd,
                "tlgd": tlgd,
                "comparable": bool(control["gatePassed"] and tlgd["gatePassed"]),
                "diff": unified_diff(
                    control["response"], tlgd["response"], tofile=treatment_condition
                ),
                "wordReduction": reduction(control["words"], tlgd["words"]),
                "outputTokenReduction": reduction(
                    control["outputTokens"], tlgd["outputTokens"]
                ),
                "finalStepOutputTokenReduction": reduction(
                    control["finalStepOutputTokens"], tlgd["finalStepOutputTokens"]
                ),
                "durationReduction": reduction(
                    control["durationSeconds"], tlgd["durationSeconds"]
                ),
            }
        )

    if not pairs:
        raise ReportError(
            f"Run directory has no complete {control_label}/{treatment_label} pairs: {run_root}"
        )

    summaries: list[dict[str, Any]] = []
    agents = sorted({pair["agent"] for pair in pairs})
    for agent in agents:
        agent_pairs = [pair for pair in pairs if pair["agent"] == agent]
        comparable_pairs = [pair for pair in agent_pairs if pair["comparable"]]
        all_control_results = [pair["control"] for pair in agent_pairs]
        all_tlgd_results = [pair["tlgd"] for pair in agent_pairs]
        control_results = [pair["control"] for pair in comparable_pairs]
        tlgd_results = [pair["tlgd"] for pair in comparable_pairs]
        all_control_words = sum_metric(all_control_results, "words")
        all_tlgd_words = sum_metric(all_tlgd_results, "words")
        all_control_output = sum_metric(all_control_results, "output_tokens")
        all_tlgd_output = sum_metric(all_tlgd_results, "output_tokens")
        all_control_total = sum_metric(all_control_results, "total_tokens")
        all_tlgd_total = sum_metric(all_tlgd_results, "total_tokens")
        all_control_final_output = sum_metric(
            all_control_results, "final_step_output_tokens"
        )
        all_tlgd_final_output = sum_metric(
            all_tlgd_results, "final_step_output_tokens"
        )
        control_words = sum_metric(control_results, "words")
        tlgd_words = sum_metric(tlgd_results, "words")
        control_output = sum_metric(control_results, "output_tokens")
        tlgd_output = sum_metric(tlgd_results, "output_tokens")
        control_final_output = sum_metric(control_results, "final_step_output_tokens")
        tlgd_final_output = sum_metric(tlgd_results, "final_step_output_tokens")
        models = sorted(
            {
                str(result.get("runtimeModel"))
                for result in all_control_results + all_tlgd_results
                if result.get("runtimeModel")
            }
        )
        summaries.append(
            {
                "agent": agent,
                "models": models,
                "pairCount": len(agent_pairs),
                "comparablePairCount": len(comparable_pairs),
                "allControlWords": all_control_words,
                "allTreatmentWords": all_tlgd_words,
                "allTlgfWords": all_tlgd_words,
                "allTlgdWords": all_tlgd_words,
                "allWordReduction": reduction(all_control_words, all_tlgd_words),
                "allControlOutputTokens": all_control_output,
                "allTreatmentOutputTokens": all_tlgd_output,
                "allTlgfOutputTokens": all_tlgd_output,
                "allTlgdOutputTokens": all_tlgd_output,
                "allOutputTokenReduction": reduction(
                    all_control_output, all_tlgd_output
                ),
                "allControlTotalTokens": all_control_total,
                "allTreatmentTotalTokens": all_tlgd_total,
                "allTlgfTotalTokens": all_tlgd_total,
                "allTlgdTotalTokens": all_tlgd_total,
                "allTotalTokenReduction": reduction(
                    all_control_total, all_tlgd_total
                ),
                "allControlFinalStepOutputTokens": all_control_final_output,
                "allTreatmentFinalStepOutputTokens": all_tlgd_final_output,
                "allTlgfFinalStepOutputTokens": all_tlgd_final_output,
                "allTlgdFinalStepOutputTokens": all_tlgd_final_output,
                "allFinalStepOutputTokenReduction": reduction(
                    all_control_final_output, all_tlgd_final_output
                ),
                "controlWords": control_words,
                "treatmentWords": tlgd_words,
                "tlgfWords": tlgd_words,
                "tlgdWords": tlgd_words,
                "wordReduction": reduction(control_words, tlgd_words),
                "controlOutputTokens": control_output,
                "treatmentOutputTokens": tlgd_output,
                "tlgfOutputTokens": tlgd_output,
                "tlgdOutputTokens": tlgd_output,
                "outputTokenReduction": reduction(control_output, tlgd_output),
                "controlFinalStepOutputTokens": control_final_output,
                "treatmentFinalStepOutputTokens": tlgd_final_output,
                "tlgfFinalStepOutputTokens": tlgd_final_output,
                "tlgdFinalStepOutputTokens": tlgd_final_output,
                "finalStepOutputTokenReduction": reduction(
                    control_final_output, tlgd_final_output
                ),
                "controlPassed": sum(
                    1 for result in all_control_results if result.get("gatePassed")
                ),
                "treatmentPassed": sum(
                    1 for result in all_tlgd_results if result.get("gatePassed")
                ),
                "tlgfPassed": sum(
                    1 for result in all_tlgd_results if result.get("gatePassed")
                ),
                "tlgdPassed": sum(
                    1 for result in all_tlgd_results if result.get("gatePassed")
                ),
                "budgetTracked": any(
                    result.get("budgetTracked")
                    for result in all_control_results + all_tlgd_results
                ),
                "controlBudgetPassed": sum(
                    1
                    for result in all_control_results
                    if result.get("budgetTracked") and result.get("budgetPassed")
                ),
                "treatmentBudgetPassed": sum(
                    1
                    for result in all_tlgd_results
                    if result.get("budgetTracked") and result.get("budgetPassed")
                ),
                "tlgfBudgetPassed": sum(
                    1
                    for result in all_tlgd_results
                    if result.get("budgetTracked") and result.get("budgetPassed")
                ),
                "tlgdBudgetPassed": sum(
                    1
                    for result in all_tlgd_results
                    if result.get("budgetTracked") and result.get("budgetPassed")
                ),
                "controlRetries": sum(
                    int(result.get("retryCount") or 0) for result in all_control_results
                ),
                "treatmentRetries": sum(
                    int(result.get("retryCount") or 0) for result in all_tlgd_results
                ),
                "tlgfRetries": sum(
                    int(result.get("retryCount") or 0) for result in all_tlgd_results
                ),
                "tlgdRetries": sum(
                    int(result.get("retryCount") or 0) for result in all_tlgd_results
                ),
            }
        )

    repository = manifest.get("repository")
    if not isinstance(repository, dict):
        repository = {}
    report_config = manifest.get("report")
    if not isinstance(report_config, dict):
        report_config = {}
    return {
        "title": str(report_config.get("title") or f"{treatment_label} benchmark report"),
        "eyebrow": str(report_config.get("eyebrow") or "A/B benchmark"),
        "controlCondition": control_condition,
        "treatmentCondition": treatment_condition,
        "controlLabel": control_label,
        "treatmentLabel": treatment_label,
        "runId": str(environment.get("run_id") or run_root.name),
        "createdAt": environment.get("created_at"),
        "benchmarkId": manifest.get("id"),
        "repository": repository.get("url"),
        "repositoryCommit": repository.get("commit"),
        "seed": environment.get("seed"),
        "timeoutSeconds": environment.get("timeout_seconds"),
        "sourceRuns": environment.get("source_runs", []),
        "pairCount": len(pairs),
        "responseCount": len(pairs) * 2,
        "summaries": summaries,
        "pairs": pairs,
        "agents": agents,
        "cases": list(dict.fromkeys(pair["caseId"] for pair in pairs)),
        "reviewUrl": "REVIEW.md" if (run_root / "REVIEW.md").is_file() else None,
        "analysisUrl": "ANALYSIS.md" if (run_root / "ANALYSIS.md").is_file() else None,
        "markdownReportUrl": "REPORT.md" if (run_root / "REPORT.md").is_file() else None,
        "blindReviewUrl": (
            "BLIND_REVIEW.md" if (run_root / "BLIND_REVIEW.md").is_file() else None
        ),
        "notice": (
            "One repetition per condition. "
            "Summary deltas include only pairs where both answers passed the automated gate. "
            "Complete an independent quality review before publishing a claim."
        ),
    }


def json_for_script(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        encoded.replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render_report(
    run_root: Path,
    output: Path | None = None,
    template_path: Path = DEFAULT_TEMPLATE,
) -> Path:
    run_root = run_root.resolve()
    if not template_path.is_file():
        raise ReportError(f"HTML template not found: {template_path}")
    data = build_report_data(run_root)
    template = template_path.read_text(encoding="utf-8")
    marker = "__REPORT_DATA__"
    if template.count(marker) != 1:
        raise ReportError(f"Expected one {marker} marker in {template_path}")
    rendered = template.replace(marker, json_for_script(data))
    destination = output.resolve() if output else run_root / "REPORT.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path, help="Benchmark run directory")
    parser.add_argument("--output", type=Path, help="Output HTML path")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        destination = render_report(args.run_root, args.output, args.template)
    except ReportError as error:
        print(f"ERROR: {error}")
        return 1
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
