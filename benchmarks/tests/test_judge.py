from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

JUDGE_PATH = Path(__file__).resolve().parents[1] / "judge.py"
SPEC = importlib.util.spec_from_file_location("benchmark_judge", JUDGE_PATH)
judge = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(judge)

FAKE_JUDGE = textwrap.dedent(
    """
    import json, sys
    prompt = sys.stdin.read()
    if "## Statements" in prompt:
        answer = prompt.split("## Answer", 1)[1].split("## Statements", 1)[0]
        statements = [l for l in prompt.split("## Statements", 1)[1].splitlines() if l[:1].isdigit()]
        facts = [{"index": i + 1, "conveyed": "GOOD" in answer, "evidence": "GOOD" if "GOOD" in answer else "BAD"} for i in range(len(statements))]
        print(json.dumps({"facts": facts}))
        raise SystemExit(0)
    a = prompt.split("## Answer A", 1)[1].split("## Answer B", 1)[0]
    b = prompt.split("## Answer B", 1)[1].split("## Scoring", 1)[0]
    names = []
    for line in prompt.split("## Scoring", 1)[1].splitlines():
        if line.startswith("- ") and ":" in line:
            names.append(line[2:].split(":", 1)[0].strip())
    def score(text):
        good = "GOOD" in text
        return {name: (2 if good else 1) for name in names}
    preference = "A" if "GOOD" in a else ("B" if "GOOD" in b else "tie")
    print("```json")
    print(json.dumps({
        "scores": {"A": score(a), "B": score(b)},
        "critical_error": {"A": "BAD" in a, "B": "BAD" in b},
        "ai_mannerisms": {"A": [], "B": ["it is important to note"] if "BAD" in b else []},
        "preference": preference,
        "reason": "GOOD answer cites the exact path.",
    }))
    print("```")
    """
)


def write_run(root: Path, *, good_condition: str = "tlgf") -> None:
    (root / "runs").mkdir(parents=True)
    (root / "environment.json").write_text(
        json.dumps({"run_id": "unit-run", "repository_commit": "abc123"}), encoding="utf-8"
    )
    manifest = {
        "schema_version": 1,
        "id": "unit",
        "repository": {"name": "example/repo", "commit": "abc123"},
        "conditions": {"control": {"skill_enabled": False}, "tlgf": {"skill_enabled": True}},
        "cases": [
            {
                "id": "case-one",
                "prompt": "Where is res.json() implemented?",
                "review_criteria": ["Cite lib/response.js.", "Stop after the answer."],
                "semantic_facts": ["res.json lives in lib/response.js.", "It delegates to res.send."],
            }
        ],
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for agent in ("claude", "codex"):
        for condition in ("control", "tlgf"):
            marker = "GOOD" if condition == good_condition else "BAD"
            (root / "runs" / f"{agent}__case-one__{condition}__r1.json").write_text(
                json.dumps(
                    {
                        "agent": agent,
                        "case_id": "case-one",
                        "condition": condition,
                        "repetition": 1,
                        "response": f"{marker}: res.json() lives in lib/response.js and calls res.send().",
                    }
                ),
                encoding="utf-8",
            )


class JudgeHelperTests(unittest.TestCase):
    def test_blind_swap_matches_core_hash_scheme(self) -> None:
        self.assertIsInstance(judge.blind_swap("run", "claude", "case", 1), bool)
        self.assertEqual(
            judge.blind_swap("run", "claude", "case", 1),
            judge.blind_swap("run", "claude", "case", 1),
        )

    def test_neutralize_workspace_paths_matches_core(self) -> None:
        core = judge.load_core()
        text = "file:///tmp/run/workspaces/codex/control/repository/lib/app.js and RUN_ROOT/workspaces/agy/tlgf/repository/Readme.md:163"
        self.assertEqual(judge.neutralize_workspace_paths(text), core.neutralize_workspace_paths(text))
        self.assertNotIn("/control/", judge.neutralize_workspace_paths(text))
        self.assertNotIn("/tlgf/", judge.neutralize_workspace_paths(text))

    def test_prompts_hide_the_condition_segment_of_workspace_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_run(root)
            for path in (root / "runs").glob("*.json"):
                result = json.loads(path.read_text(encoding="utf-8"))
                result["response"] += (
                    f" See file:///tmp/run/workspaces/{result['agent']}/{result['condition']}/repository/lib/response.js#L10"
                )
                path.write_text(json.dumps(result), encoding="utf-8")
            run = judge.load_run(root)
            self.assertTrue(run["pairs"])
            for pair in run["pairs"]:
                prompt = judge.build_prompt(pair, run["context"], judge.dimensions_for(run["skill"]), ("A", "B"))
                self.assertNotIn("/control/", prompt)
                self.assertNotIn("/tlgf/", prompt)
                self.assertIn(f"workspaces/{pair['agent']}/CONDITION/repository/lib/response.js#L10", prompt)
                for answer in pair["by_condition"].values():
                    facts_prompt = judge.build_facts_prompt(pair["case"], run["context"], answer)
                    self.assertNotIn("/control/", facts_prompt)
                    self.assertNotIn("/tlgf/", facts_prompt)

    def test_map_preference_follows_position_swap(self) -> None:
        condition_of = {"A": "tlgf", "B": "control"}
        self.assertEqual(judge.map_preference("A", ("A", "B"), condition_of), "tlgf")
        self.assertEqual(judge.map_preference("A", ("B", "A"), condition_of), "control")
        self.assertEqual(judge.map_preference("tie", ("B", "A"), condition_of), "tie")

    def test_combine_orders_flags_position_dependence(self) -> None:
        stable = judge.combine_orders(
            [{"preference_condition": "tlgf"}, {"preference_condition": "tlgf"}], "tlgf"
        )
        self.assertEqual(stable["outcome"], "tlgf")
        self.assertTrue(stable["consistent"])
        unstable = judge.combine_orders(
            [{"preference_condition": "tlgf"}, {"preference_condition": "control"}], "tlgf"
        )
        self.assertEqual(unstable["outcome"], "position-dependent")
        missing = judge.combine_orders([{"preference_condition": None}], "tlgf")
        self.assertEqual(missing["outcome"], "unavailable")

    def test_extract_json_object_reads_fenced_and_wrapped_text(self) -> None:
        fenced = "Here you go:\n```json\n{\"preference\": \"A\"}\n```"
        self.assertEqual(judge.extract_json_object(fenced), {"preference": "A"})
        wrapped = "Verdict {\"preference\": \"B\", \"reason\": \"x\"} end"
        self.assertEqual(judge.extract_json_object(wrapped)["preference"], "B")
        self.assertIsNone(judge.extract_json_object("no json here"))

    def test_validate_verdict_rejects_bad_scores(self) -> None:
        dims = judge.SHARED_DIMENSIONS
        good = {
            "preference": "A",
            "scores": {"A": {name: 2 for name, _ in dims}, "B": {name: 1 for name, _ in dims}},
        }
        self.assertIsNone(judge.validate_verdict(good, dims))
        bad = {"preference": "A", "scores": {"A": {name: 3 for name, _ in dims}, "B": {}}}
        self.assertIsNotNone(judge.validate_verdict(bad, dims))


class JudgeRunTests(unittest.TestCase):
    def run_fake_judge(self, good_condition: str) -> tuple[Path, dict]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        run_root = root / "run"
        write_run(run_root, good_condition=good_condition)
        fake = root / "fake_judge.py"
        fake.write_text(FAKE_JUDGE, encoding="utf-8")
        exit_code = judge.main(
            [str(run_root), "--judges", "fake", "--judge-command", f"{sys.executable} {fake}"]
        )
        self.assertEqual(exit_code, 0)
        payload = json.loads((run_root / "judge.json").read_text(encoding="utf-8"))
        return run_root, payload

    def test_treatment_wins_are_mapped_through_blinding_and_position_swap(self) -> None:
        run_root, payload = self.run_fake_judge("tlgf")
        self.assertEqual(payload["pair_count"], 2)
        for pair in payload["pairs"]:
            block = pair["judges"]["fake"]
            self.assertEqual([v["order"] for v in block["verdicts"]], ["AB", "BA"])
            self.assertEqual({v["preference_condition"] for v in block["verdicts"]}, {"tlgf"})
            self.assertEqual(block["combined"], {"outcome": "tlgf", "consistent": True})
            for verdict in block["verdicts"]:
                self.assertEqual(verdict["scores_by_condition"]["tlgf"]["accuracy"], 2)
                self.assertEqual(verdict["scores_by_condition"]["control"]["accuracy"], 1)
                self.assertEqual(verdict["critical_error_by_condition"], {"tlgf": False, "control": True})
        summary = payload["summary"]
        self.assertEqual(summary["per_judge"]["fake"], {"tlgf": 2})
        self.assertEqual(summary["agreement"], {"unanimous": 2, "split": 0, "pairs_with_all_judges": 2})
        self.assertEqual(summary["mean_scores"]["fake"]["tlgf"]["clarity"], 2.0)
        markdown = (run_root / "JUDGE.md").read_text(encoding="utf-8")
        self.assertIn("| fake | 2 | 0 | 0 | 0 | 0 | 0 |", markdown)
        self.assertIn("Complete the human blind review", markdown)

    def test_facts_mode_scores_each_answer_separately(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        run_root = root / "run"
        write_run(run_root, good_condition="tlgf")
        fake = root / "fake_judge.py"
        fake.write_text(FAKE_JUDGE, encoding="utf-8")
        exit_code = judge.main(
            [str(run_root), "--judges", "fake", "--facts", "--single-order", "--judge-command", f"{sys.executable} {fake}"]
        )
        self.assertEqual(exit_code, 0)
        payload = json.loads((run_root / "judge.json").read_text(encoding="utf-8"))
        coverage = payload["summary"]["fact_coverage"]["fake"]
        self.assertEqual(coverage["tlgf"], {"mean": 1.0, "answers": 2})
        self.assertEqual(coverage["control"], {"mean": 0.0, "answers": 2})
        first = payload["pairs"][0]["facts"]["by_judge"]["fake"]
        self.assertEqual(first["tlgf"]["conveyed"], [True, True])
        markdown = (run_root / "JUDGE.md").read_text(encoding="utf-8")
        self.assertIn("## Semantic fact coverage", markdown)
        self.assertIn("| fake | tlgf | 1.0 | 2 |", markdown)

    def test_resume_skips_pairs_recorded_in_progress(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        run_root = root / "run"
        write_run(run_root, good_condition="tlgf")
        fake = root / "fake_judge.py"
        fake.write_text(FAKE_JUDGE, encoding="utf-8")
        first = judge.main([str(run_root), "--judges", "fake", "--limit", "1", "--judge-command", f"{sys.executable} {fake}"])
        self.assertEqual(first, 0)
        payload = json.loads((run_root / "judge.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["pair_count"], 1)
        # Simulate an interrupted second run: the first pair is recorded, the second is not.
        (run_root / "judge-progress.json").write_text(json.dumps({"run_id": "unit-run", "pairs": payload["pairs"]}), encoding="utf-8")
        counter = root / "calls.txt"
        counting = FAKE_JUDGE.replace("prompt = sys.stdin.read()", f"prompt = sys.stdin.read(); open({str(counter)!r}, 'a').write('x')")
        fake.write_text(counting, encoding="utf-8")
        second = judge.main([str(run_root), "--judges", "fake", "--resume", "--judge-command", f"{sys.executable} {fake}"])
        self.assertEqual(second, 0)
        resumed = json.loads((run_root / "judge.json").read_text(encoding="utf-8"))
        self.assertEqual(resumed["pair_count"], 2)
        self.assertEqual(len(counter.read_text(encoding="utf-8")), 2)
        self.assertFalse((run_root / "judge-progress.json").exists())

    def test_resume_retries_only_unusable_verdicts(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        run_root = root / "run"
        write_run(run_root, good_condition="tlgf")
        fake = root / "fake_judge.py"
        fake.write_text(FAKE_JUDGE, encoding="utf-8")
        self.assertEqual(judge.main([str(run_root), "--judges", "fake", "--facts", "--judge-command", f"{sys.executable} {fake}"]), 0)
        payload = json.loads((run_root / "judge.json").read_text(encoding="utf-8"))
        # Poison one pairwise verdict and one facts verdict as if the host had refused them.
        first = payload["pairs"][0]
        first["judges"]["fake"]["verdicts"][1]["preference_condition"] = None
        first["judges"]["fake"]["verdicts"][1]["verdict_problem"] = "host error 429"
        first["facts"]["by_judge"]["fake"]["control"]["coverage"] = None
        (run_root / "judge.json").write_text(json.dumps(payload), encoding="utf-8")
        counter = root / "calls.txt"
        counting = FAKE_JUDGE.replace("prompt = sys.stdin.read()", f"prompt = sys.stdin.read(); open({str(counter)!r}, 'a').write('x')")
        fake.write_text(counting, encoding="utf-8")
        self.assertEqual(judge.main([str(run_root), "--judges", "fake", "--facts", "--resume", "--judge-command", f"{sys.executable} {fake}"]), 0)
        self.assertEqual(len(counter.read_text(encoding="utf-8")), 2)
        repaired = json.loads((run_root / "judge.json").read_text(encoding="utf-8"))
        block = repaired["pairs"][0]["judges"]["fake"]
        self.assertEqual({v["preference_condition"] for v in block["verdicts"]}, {"tlgf"})
        self.assertEqual(block["combined"]["outcome"], "tlgf")
        self.assertEqual(repaired["pairs"][0]["facts"]["by_judge"]["fake"]["control"]["coverage"], 0.0)
        self.assertEqual(repaired["summary"]["per_judge"]["fake"], {"tlgf": 2})

    def test_control_wins_are_not_mislabeled(self) -> None:
        _, payload = self.run_fake_judge("control")
        self.assertEqual(payload["summary"]["per_judge"]["fake"], {"control": 2})

    def test_dry_run_prints_prompts_without_writing(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        run_root = Path(directory.name) / "run"
        write_run(run_root)
        exit_code = judge.main([str(run_root), "--judges", "claude", "--dry-run", "--limit", "1"])
        self.assertEqual(exit_code, 0)
        self.assertFalse((run_root / "judge.json").exists())

    def test_env_file_supplies_judge_models(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        run_root = root / "run"
        write_run(run_root)
        env_file = root / ".env"
        env_file.write_text("JUDGE_CLAUDE_MODEL=claude-env-model\nJUDGE_CODEX_MODEL=codex-env-model\n", encoding="utf-8")
        fake = root / "fake_judge.py"
        fake.write_text(FAKE_JUDGE, encoding="utf-8")
        exit_code = judge.main([
            str(run_root),
            "--judges", "claude,codex",
            "--env-file", str(env_file),
            "--judge-command", f"{sys.executable} {fake}",
        ])
        self.assertEqual(exit_code, 0)
        payload = json.loads((run_root / "judge.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["judge_models"]["claude"], "claude-env-model")
        self.assertEqual(payload["judge_models"]["codex"], "codex-env-model")


if __name__ == "__main__":
    unittest.main()
