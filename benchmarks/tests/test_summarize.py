from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SUMMARIZE_PATH = Path(__file__).resolve().parents[1] / "summarize.py"
SPEC = importlib.util.spec_from_file_location("benchmark_summarize", SUMMARIZE_PATH)
summarize = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(summarize)


def write_result(root: Path, agent: str, case_id: str, condition: str, repetition: int, words: int, quality: bool, tokens: int) -> None:
    (root / "runs" / f"{agent}__{case_id}__{condition}__r{repetition}.json").write_text(
        json.dumps(
            {
                "agent": agent,
                "case_id": case_id,
                "condition": condition,
                "repetition": repetition,
                "attempt_count": 1,
                "agent_status": "SUCCESS",
                "response_words": words,
                "duration_seconds": 10.0,
                "usage": {"total_tokens": tokens, "output_tokens": tokens // 10},
                "evaluation": {
                    "quality_passed": quality,
                    "budget_passed": words <= 100,
                    "style": {"mannerism_count": 0 if condition == "tlgf" else 1, "mean_sentence_words": 12.0},
                },
            }
        ),
        encoding="utf-8",
    )


class SummarizeTests(unittest.TestCase):
    def test_medians_and_pairs_per_agent_and_case(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "runs").mkdir()
            (root / "environment.json").write_text(json.dumps({"run_id": "unit"}), encoding="utf-8")
            (root / "manifest.json").write_text(
                json.dumps({"conditions": {"control": {}, "tlgf": {}}, "cases": [{"id": "short"}]}),
                encoding="utf-8",
            )
            for repetition, (control_words, tlgf_words) in enumerate([(100, 50), (120, 60), (300, 90)], start=1):
                write_result(root, "claude", "short", "control", repetition, control_words, repetition != 3, 1000)
                write_result(root, "claude", "short", "tlgf", repetition, tlgf_words, True, 1100)
            summary = summarize.summarize(root)
            row = summary["rows"][0]
            self.assertEqual(row["conditions"]["control"]["median_words"], 120.0)
            self.assertEqual(row["conditions"]["tlgf"]["median_words"], 60.0)
            self.assertEqual(row["conditions"]["control"]["quality_pass"], 2)
            self.assertEqual(row["conditions"]["tlgf"]["quality_pass"], 3)
            self.assertEqual(row["conditions"]["control"]["budget_pass"], 1)
            self.assertEqual(row["conditions"]["tlgf"]["median_mannerisms"], 0.0)
            self.assertEqual(row["pairs"], 3)
            self.assertEqual(row["median_word_reduction_percent"], 50.0)
            self.assertEqual(summary["totals"]["tlgf"], {"answers": 3, "quality_pass": 3, "budget_pass": 3})
            markdown = summarize.to_markdown(summary)
            self.assertIn("| claude | short | 2/3 | 3/3 | 1/3 | 3/3 | 120 | 60 | -50% | 1 | 0 | 1000 | 1100 |", markdown)

    def test_rejects_run_without_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "runs").mkdir()
            (root / "environment.json").write_text("{}", encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({"conditions": {"control": {}, "tlgf": {}}, "cases": []}), encoding="utf-8")
            with self.assertRaises(summarize.SummaryError):
                summarize.summarize(root)


if __name__ == "__main__":
    unittest.main()
