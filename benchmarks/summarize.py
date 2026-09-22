#!/usr/bin/env python3
"""Summarize a completed benchmark run per host and case for publication.

Usage:
    python3 benchmarks/summarize.py benchmarks/results/RUN_DIRECTORY [--markdown]

For every (agent, case) the summary reports, per condition, the number of
answers, quality and budget pass counts, the median reader-visible words,
the median mannerism count, the median host-reported total tokens, and the
median duration. The paired columns report the median per-pair word change.
Medians over repetitions are robust to one verbose or one terse outlier.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


class SummaryError(RuntimeError):
    """A summary could not be produced."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SummaryError(f"Cannot read {path}: {error}") from error


def median(values: list[float | int]) -> float | None:
    clean = [float(value) for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
    if not clean:
        return None
    return round(statistics.median(clean), 1)


def load_results(run_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    manifest_path = run_root / "grader-manifest.json"
    if not manifest_path.is_file():
        manifest_path = run_root / "manifest.json"
    manifest = read_json(manifest_path)
    conditions = list(manifest.get("conditions", {}))
    treatment = [name for name in conditions if name != "control"]
    if "control" not in conditions or len(treatment) != 1:
        raise SummaryError("The manifest must define control and exactly one treatment condition")
    results = [read_json(path) for path in sorted((run_root / "runs").glob("*.json"))]
    if not results:
        raise SummaryError(f"No results under {run_root / 'runs'}")
    return manifest, results, treatment[0]


def summarize(run_root: Path) -> dict[str, Any]:
    manifest, results, treatment = load_results(run_root)
    environment = read_json(run_root / "environment.json")
    grouped: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for result in results:
        grouped[(result["agent"], result["case_id"])][result["condition"]].append(result)
    rows: list[dict[str, Any]] = []
    for (agent, case_id), by_condition in sorted(grouped.items()):
        row: dict[str, Any] = {"agent": agent, "case_id": case_id, "conditions": {}}
        for condition in ("control", treatment):
            items = by_condition.get(condition, [])
            evaluations = [item.get("evaluation", {}) for item in items]
            row["conditions"][condition] = {
                "answers": len(items),
                "quality_pass": sum(1 for evaluation in evaluations if evaluation.get("quality_passed", evaluation.get("passed"))),
                "budget_pass": sum(1 for evaluation in evaluations if evaluation.get("budget_passed")),
                "first_attempt_success": sum(1 for item in items if item.get("attempt_count", 1) == 1 and item.get("agent_status") == "SUCCESS"),
                "median_words": median([item.get("response_words") for item in items]),
                "median_mannerisms": median([evaluation.get("style", {}).get("mannerism_count") for evaluation in evaluations]),
                "median_sentence_words": median([evaluation.get("style", {}).get("mean_sentence_words") for evaluation in evaluations]),
                "median_total_tokens": median([(item.get("usage") or {}).get("total_tokens") for item in items]),
                "median_output_tokens": median([(item.get("usage") or {}).get("output_tokens") for item in items]),
                "median_seconds": median([item.get("duration_seconds") for item in items]),
            }
        pairs = []
        by_rep_control = {item["repetition"]: item for item in by_condition.get("control", [])}
        for item in by_condition.get(treatment, []):
            control = by_rep_control.get(item["repetition"])
            if control and control.get("response_words") and item.get("response_words") is not None:
                pairs.append(100.0 * (1 - item["response_words"] / control["response_words"]))
        row["median_word_reduction_percent"] = median(pairs)
        row["pairs"] = len(pairs)
        rows.append(row)
    totals: dict[str, dict[str, int]] = {}
    for condition in ("control", treatment):
        totals[condition] = {
            "answers": sum(row["conditions"][condition]["answers"] for row in rows),
            "quality_pass": sum(row["conditions"][condition]["quality_pass"] for row in rows),
            "budget_pass": sum(row["conditions"][condition]["budget_pass"] for row in rows),
        }
    return {
        "schema_version": 1,
        "run_id": environment.get("run_id", run_root.name),
        "treatment": treatment,
        "agents": sorted({row["agent"] for row in rows}),
        "cases": [case["id"] for case in manifest.get("cases", []) if any(row["case_id"] == case["id"] for row in rows)],
        "rows": rows,
        "totals": totals,
    }


def format_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.0f}" if value.is_integer() else f"{value:.1f}"
    return str(value)


def to_markdown(summary: dict[str, Any]) -> str:
    treatment = summary["treatment"]
    lines = [
        f"### Run `{summary['run_id']}`",
        "",
        f"| Agent | Case | Control quality | {treatment} quality | Control budget | {treatment} budget | Control words | {treatment} words | Word change | Control mannerisms | {treatment} mannerisms | Control tokens | {treatment} tokens |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["rows"]:
        control = row["conditions"]["control"]
        treated = row["conditions"][treatment]
        change = row["median_word_reduction_percent"]
        change_text = "—" if change is None else f"{-change:+.0f}%"
        lines.append(
            "| "
            + " | ".join(
                [
                    row["agent"],
                    row["case_id"],
                    f"{control['quality_pass']}/{control['answers']}",
                    f"{treated['quality_pass']}/{treated['answers']}",
                    f"{control['budget_pass']}/{control['answers']}",
                    f"{treated['budget_pass']}/{treated['answers']}",
                    format_value(control["median_words"]),
                    format_value(treated["median_words"]),
                    change_text,
                    format_value(control["median_mannerisms"]),
                    format_value(treated["median_mannerisms"]),
                    format_value(control["median_total_tokens"]),
                    format_value(treated["median_total_tokens"]),
                ]
            )
            + " |"
        )
    totals = summary["totals"]
    lines.extend(
        [
            "",
            f"Totals: control quality {totals['control']['quality_pass']}/{totals['control']['answers']}, {treatment} quality {totals[treatment]['quality_pass']}/{totals[treatment]['answers']}; control budget {totals['control']['budget_pass']}/{totals['control']['answers']}, {treatment} budget {totals[treatment]['budget_pass']}/{totals[treatment]['answers']}.",
            "",
            "Words, mannerisms, and tokens are medians over repetitions; word change is the median per-pair change, negative when the treatment is shorter. Tokens are host-reported totals and compare only within one agent and model.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize a benchmark run per host and case")
    parser.add_argument("run", type=Path)
    parser.add_argument("--markdown", action="store_true", help="Print a Markdown table instead of JSON")
    parser.add_argument("--write", action="store_true", help="Write SUMMARY.md and per-host-summary.json into the run directory")
    args = parser.parse_args(argv)
    try:
        summary = summarize(args.run.resolve())
    except SummaryError as error:
        print(f"Summary failed: {error}", file=sys.stderr)
        return 1
    markdown = to_markdown(summary)
    if args.write:
        (args.run / "SUMMARY.md").write_text(markdown, encoding="utf-8")
        (args.run / "per-host-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {args.run / 'SUMMARY.md'}")
    elif args.markdown:
        print(markdown, end="")
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
