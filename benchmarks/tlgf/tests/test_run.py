from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


RUNNER_PATH = Path(__file__).resolve().parents[1] / "run.py"
SPEC = importlib.util.spec_from_file_location("tlgf_benchmark_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class ManifestTests(unittest.TestCase):
    def test_manifest_has_first_milestone_cases(self) -> None:
        manifest = runner.load_manifest()
        self.assertEqual(manifest["id"], "tlgf-continuity-v2")
        self.assertEqual(
            [case["id"] for case in runner.select_cases(manifest, None)],
            [
                "standalone-restraint",
                "run-lineage",
                "park-resume",
                "stale-state",
                "useful-signal",
                "addressable-expand",
                "addressable-action",
                "decision-blocker",
                "park-point",
                "refresh-after-action",
                "compare-b-vs-c",
                "missing-frame",
                "localized-labels",
            ],
        )
        self.assertIn(
            "flask-error-handlers",
            [case["id"] for case in manifest["cases"]],
        )

    def test_real_repository_case_is_pinned_and_opt_in(self) -> None:
        manifest = runner.load_manifest()
        case = runner.select_cases(manifest, ["flask-error-handlers"])[0]
        self.assertFalse(case["enabled_by_default"])
        self.assertTrue(case["requires_preparation"])
        self.assertEqual(
            case["source_repository"]["commit"],
            "d318b683471101618febed18996405ad26462110",
        )
        self.assertEqual(case["source_repository"]["license"], "BSD-3-Clause")

    def test_orient_cases_use_triptych_labels(self) -> None:
        old_labels = {
            "TLGF EXEC",
            "Where we are:",
            "Current goal:",
            "What we know:",
            "Why it matters:",
            "Worth noticing:",
            "Progress so far:",
        }
        english_labels = {
            "**You are here:**",
            "**What's happening now:**",
            "**Suggested next steps:**",
            "---",
        }
        for case in runner.load_manifest()["cases"]:
            if case["mode"] not in {"orient", "resume"}:
                continue
            labels = {term for group in case["treatment_required_term_groups"] for term in group}
            self.assertTrue(old_labels.isdisjoint(labels), case["id"])
            localized = runner.case_labels(case)
            if localized == runner.DEFAULT_LABELS:
                self.assertTrue(english_labels.issubset(labels), case["id"])
            else:
                self.assertTrue(
                    any(f"**{label}:**" in labels for label in localized["you_are_here"]), case["id"]
                )
                self.assertIn("---", labels, case["id"])
                self.assertNotIn("**You are here:**", labels, case["id"])

    def test_localized_labels_drive_the_first_content_gate(self) -> None:
        case = next(
            case for case in runner.load_manifest()["cases"] if case["id"] == "localized-labels"
        )
        labels = runner.case_labels(case)
        self.assertIn("Jesteś tutaj", labels["you_are_here"])
        self.assertIn("Tu jesteś", labels["you_are_here"])
        polish = "**Jesteś tutaj:** Benchmark › porównanie promptów › beta\n\n---\n"
        self.assertTrue(runner.first_visible_content(polish, labels)["valid_triptych_start"])
        self.assertFalse(runner.first_visible_content(polish)["valid_triptych_start"])
        gated = "⛔ **Potrzebuję cię**\n\n**Jesteś tutaj:** Wydanie › decyzja\n"
        content = runner.first_visible_content(gated, labels)
        self.assertTrue(content["needs_you_at_start"])
        self.assertTrue(content["valid_triptych_start"])
        self.assertEqual(runner.case_labels({}), runner.DEFAULT_LABELS)

    def test_state_file_updates_do_not_count_as_workspace_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "reports").mkdir()
            (workspace / "reports" / "a.json").write_text("{}", encoding="utf-8")
            (workspace / ".tlgf").mkdir()
            (workspace / ".tlgf" / "STATE.md").write_text("# TLGF state\n", encoding="utf-8")
            before = runner.core.repository_digest(workspace, ignore=(runner.STATE_FILE,))
            state_before = runner.state_file_digest(workspace)
            (workspace / ".tlgf" / "STATE.md").write_text("# TLGF state\n\nUpdated.\n", encoding="utf-8")
            self.assertEqual(runner.core.repository_digest(workspace, ignore=(runner.STATE_FILE,)), before)
            self.assertNotEqual(runner.state_file_digest(workspace), state_before)
            (workspace / "reports" / "a.json").write_text("{\"changed\": true}", encoding="utf-8")
            self.assertNotEqual(runner.core.repository_digest(workspace, ignore=(runner.STATE_FILE,)), before)
            self.assertIsNone(runner.state_file_digest(workspace / "reports"))

    def test_follow_up_cases_embed_the_prior_frame_instead_of_a_file(self) -> None:
        manifest = runner.load_manifest()
        for case_id in ("addressable-expand", "addressable-action", "compare-b-vs-c", "park-point"):
            case = runner.select_cases(manifest, [case_id])[0]
            self.assertEqual(case["mode"], "follow-up", case_id)
            self.assertIn("Your previous message in this conversation was the following frame.", case["prompt"])
            self.assertIn("**Suggested next steps:**", case["prompt"])
            self.assertNotIn("frame.md", case["prompt"])
            self.assertEqual(case["required_paths"], [])
        missing = runner.select_cases(manifest, ["missing-frame"])[0]
        self.assertEqual(missing["prompt"], "do B")
        self.assertEqual(missing["max_user_questions"], 1)
        refresh = runner.select_cases(manifest, ["refresh-after-action"])[0]
        self.assertEqual(refresh["mode"], "orient")
        self.assertIn("A. Validate the V2 package locally", refresh["treatment_forbidden_terms"])

    def test_every_case_carries_semantic_facts_for_the_judge(self) -> None:
        for case in runner.load_manifest()["cases"]:
            self.assertTrue(case.get("semantic_facts"), case["id"])
            self.assertTrue(case.get("review_criteria"), case["id"])

    def test_english_current_label_accepts_typographic_apostrophe(self) -> None:
        case = runner.select_cases(runner.load_manifest(), ["run-lineage"])[0]
        groups = case["treatment_required_term_groups"]
        self.assertTrue(
            runner.match_groups("**What’s happening now:**", groups[1:2])[0]["passed"]
        )

    def test_fixtures_contain_every_required_path(self) -> None:
        for case in runner.load_manifest()["cases"]:
            fixture = runner.fixture_path(case, require_exists=False)
            if case.get("requires_preparation") and not fixture.is_dir():
                continue
            for relative in case["required_paths"]:
                self.assertTrue((fixture / relative).is_file(), f"{case['id']}: {relative}")

    def test_condition_order_is_stable_and_paired(self) -> None:
        first = runner.stable_condition_order(42, "codex", "stale-state", 1)
        second = runner.stable_condition_order(42, "codex", "stale-state", 1)
        self.assertEqual(first, second)
        self.assertEqual(set(first), {"control", "tlgf"})

    def test_fixture_workspace_has_an_isolated_git_branch(self) -> None:
        case = next(
            case
            for case in runner.load_manifest()["cases"]
            if case["id"] == "park-resume"
        )
        with tempfile.TemporaryDirectory() as directory:
            workspace = runner.create_workspace(
                Path(directory), "codex", "control", case, {}
            )
            branch = runner.core.run_checked(
                ["git", "-C", str(workspace), "branch", "--show-current"]
            ).stdout.strip()
        self.assertEqual(branch, "fix/retry")

    def test_repetitions_use_separate_workspaces(self) -> None:
        case = next(
            case
            for case in runner.load_manifest()["cases"]
            if case["id"] == "standalone-restraint"
        )
        with tempfile.TemporaryDirectory() as directory:
            run_root = Path(directory)
            first = runner.create_workspace(
                run_root, "codex", "control", case, {}, repetition=1
            )
            second = runner.create_workspace(
                run_root, "codex", "control", case, {}, repetition=2
            )
        self.assertNotEqual(first, second)
        self.assertIn("r1", first.parts)
        self.assertIn("r2", second.parts)

    def test_codex_command_disables_all_global_skills(self) -> None:
        original_executable = runner.core.find_executable
        original_skills = runner.core.codex_all_global_skill_paths
        runner.core.find_executable = lambda agent: "/example/codex"
        runner.core.codex_all_global_skill_paths = lambda: [
            Path("/global/tlgd/SKILL.md"),
            Path("/global/diagnose/SKILL.md"),
        ]
        try:
            command, _ = runner.core.build_command(
                "codex",
                "tlgf",
                Path("/fixture"),
                "TLGF",
                {},
                skill_name="tlgf",
                disable_other_codex_skills=True,
            )
        finally:
            runner.core.find_executable = original_executable
            runner.core.codex_all_global_skill_paths = original_skills
        serialized = " ".join(command)
        self.assertIn("/global/tlgd/SKILL.md", serialized)
        self.assertIn("/global/diagnose/SKILL.md", serialized)

    def test_measurement_extractions(self) -> None:
        codex_events = [
            {"type": "item.completed", "item": {"type": "agent_message", "text": "Step 1: Reading file"}},
            {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 15}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "Step 2: Analysis complete", "finish_reason": "stop"}},
            {"type": "turn.completed", "usage": {"input_tokens": 120, "output_tokens": 25}},
        ]
        self.assertEqual(
            runner.core.extract_visible_text("codex", codex_events, "Step 2: Analysis complete"),
            "Step 1: Reading file\n\nStep 2: Analysis complete"
        )
        final_usage = runner.core.extract_final_step_usage("codex", codex_events)
        self.assertEqual(final_usage["output_tokens"], 25)
        self.assertEqual(runner.core.extract_finish_reason("codex", codex_events), "stop")

        # Codex turn with intermediate tool steps: turn usage should NOT be attributed to final step
        codex_events_with_tools = [
            {"type": "item.completed", "item": {"type": "tool_call", "name": "exec_command"}},
            {"type": "item.completed", "item": {"type": "tool_result", "output": "ok"}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "Final answer", "finish_reason": "stop"}},
            {"type": "turn.completed", "usage": {"input_tokens": 500, "output_tokens": 100}},
        ]
        self.assertIsNone(runner.core.extract_final_step_usage("codex", codex_events_with_tools)["output_tokens"])
        self.assertEqual(runner.core.extract_usage("codex", codex_events_with_tools)["output_tokens"], 100)

        # Codex turn with explicit item-level usage
        codex_events_item_usage = [
            {"type": "item.completed", "item": {"type": "tool_call", "name": "exec_command"}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "Final answer", "usage": {"output_tokens": 18}}},
            {"type": "turn.completed", "usage": {"input_tokens": 500, "output_tokens": 100}},
        ]
        self.assertEqual(runner.core.extract_final_step_usage("codex", codex_events_item_usage)["output_tokens"], 18)

        # Claude: excludes user prompt, does not duplicate multi-block assistant response, extracts assistant.message.usage
        claude_events = [
            {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "USER PROMPT"}]}},
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "First paragraph."},
                        {"type": "text", "text": "Second paragraph."},
                    ],
                    "usage": {"input_tokens": 50, "output_tokens": 8},
                    "stop_reason": "end_turn",
                },
            },
            {"type": "result", "result": "First paragraph.\n\nSecond paragraph."},
        ]
        self.assertEqual(
            runner.core.extract_visible_text("claude", claude_events, "First paragraph.\n\nSecond paragraph."),
            "First paragraph.\n\nSecond paragraph."
        )
        self.assertEqual(runner.core.extract_final_step_usage("claude", claude_events)["output_tokens"], 8)
        self.assertEqual(runner.core.extract_final_step_usage("claude", claude_events)["input_tokens"], 50)
        self.assertEqual(runner.core.extract_finish_reason("claude", claude_events), "end_turn")

        # Claude: stream_event wrapping
        claude_stream_events = [
            {
                "type": "stream_event",
                "event": {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Stream answer"}],
                        "usage": {"input_tokens": 40, "output_tokens": 12},
                        "stop_reason": "end_turn",
                    },
                },
            },
            {"type": "result", "result": "Stream answer"},
        ]
        self.assertEqual(runner.core.extract_final_step_usage("claude", claude_stream_events)["output_tokens"], 12)
        self.assertEqual(runner.core.extract_finish_reason("claude", claude_stream_events), "end_turn")

        # Claude: intermediate tool use step followed by final answer
        claude_tool_events = [
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "tool_use", "id": "t1", "name": "read"}],
                    "usage": {"input_tokens": 30, "output_tokens": 15},
                    "stop_reason": "tool_use",
                },
            },
            {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "file data"}]}},
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Final answer after tool"}],
                    "usage": {"input_tokens": 70, "output_tokens": 25},
                    "stop_reason": "end_turn",
                },
            },
            {"type": "result", "result": "Final answer after tool", "usage": {"input_tokens": 100, "output_tokens": 40}},
        ]
        self.assertEqual(runner.core.extract_final_step_usage("claude", claude_tool_events)["output_tokens"], 25)
        self.assertEqual(runner.core.extract_finish_reason("claude", claude_tool_events), "end_turn")
        self.assertEqual(runner.core.extract_usage("claude", claude_tool_events)["output_tokens"], 40)

        # Claude: preserves legitimate repeated intermediate narration
        claude_repeat_events = [
            {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Retrying step..."}]}},
            {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Retrying step..."}]}},
            {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Success."}]}},
        ]
        self.assertEqual(
            runner.core.extract_visible_text("claude", claude_repeat_events, "Success."),
            "Retrying step...\n\nRetrying step...\n\nSuccess."
        )

        # Codex: earlier message has usage, but final answer message does not -> final_step_usage must be None
        codex_earlier_usage_events = [
            {"type": "item.completed", "item": {"type": "agent_message", "text": "Intermediate step", "usage": {"output_tokens": 7}}},
            {"type": "item.completed", "item": {"type": "tool_call", "name": "exec_command"}},
            {"type": "item.completed", "item": {"type": "tool_result", "output": "ok"}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "Final answer without usage", "finish_reason": "stop"}},
            {"type": "turn.completed", "usage": {"input_tokens": 500, "output_tokens": 100}},
        ]
        self.assertIsNone(runner.core.extract_final_step_usage("codex", codex_earlier_usage_events)["output_tokens"])
        self.assertEqual(runner.core.extract_usage("codex", codex_earlier_usage_events)["output_tokens"], 100)

        # Codex: earlier message has usage (7), final answer message has usage (18) -> returns 18, not 7
        codex_both_usage_events = [
            {"type": "item.completed", "item": {"type": "agent_message", "text": "Intermediate step", "usage": {"output_tokens": 7}}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "Final answer", "usage": {"output_tokens": 18}}},
            {"type": "turn.completed", "usage": {"input_tokens": 500, "output_tokens": 100}},
        ]
        self.assertEqual(runner.core.extract_final_step_usage("codex", codex_both_usage_events)["output_tokens"], 18)

        # Claude: earlier message has usage (7), but final answer message does not -> final_step_usage must be None
        claude_earlier_usage_events = [
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Earlier message"}],
                    "usage": {"input_tokens": 20, "output_tokens": 7},
                },
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Final answer"}],
                    "stop_reason": "end_turn",
                },
            },
            {"type": "result", "result": "Final answer", "usage": {"input_tokens": 100, "output_tokens": 40}},
        ]
        self.assertIsNone(runner.core.extract_final_step_usage("claude", claude_earlier_usage_events)["output_tokens"])
        self.assertEqual(runner.core.extract_usage("claude", claude_earlier_usage_events)["output_tokens"], 40)

        # Claude: earlier message has usage (7), final answer message has usage (25) -> returns 25, not 7
        claude_both_usage_events = [
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Earlier message"}],
                    "usage": {"input_tokens": 20, "output_tokens": 7},
                },
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Final answer"}],
                    "usage": {"input_tokens": 50, "output_tokens": 25},
                    "stop_reason": "end_turn",
                },
            },
            {"type": "result", "result": "Final answer", "usage": {"input_tokens": 100, "output_tokens": 40}},
        ]
        self.assertEqual(runner.core.extract_final_step_usage("claude", claude_both_usage_events)["output_tokens"], 25)

        # Claude stream: earlier message has usage (7), final stream generation has usage (14) -> returns 14, not 7
        claude_stream_generation_events = [
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Earlier message"}],
                    "usage": {"input_tokens": 20, "output_tokens": 7},
                },
            },
            {"type": "stream_event", "event": {"type": "message_start", "message": {"usage": {"input_tokens": 45}}}},
            {
                "type": "stream_event",
                "event": {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn"},
                    "usage": {"output_tokens": 14},
                },
            },
            {"type": "result", "result": "Stream final answer"},
        ]
        final_stream_usage = runner.core.extract_final_step_usage("claude", claude_stream_generation_events)
        self.assertEqual(final_stream_usage["output_tokens"], 14)
        self.assertEqual(final_stream_usage["input_tokens"], 45)

    def test_installs_tlgf_in_host_specific_skill_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            claude = runner.install_skill("claude", workspace)
            self.assertEqual(claude, workspace / ".claude" / "skills" / "tlgf")
            self.assertTrue((claude / "SKILL.md").is_file())

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            codex = runner.install_skill("codex", workspace)
            self.assertEqual(codex, workspace / ".agents" / "skills" / "tlgf")
            self.assertTrue((codex / "SKILL.md").is_file())

    def test_skill_preserves_comparison_and_retry_boundaries(self) -> None:
        skill = (runner.SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("different models, prompts, commits, environments, or retry conditions", skill)
        self.assertIn("recovered evidence, not proof of first-attempt reliability", skill)

    def test_skill_keeps_the_triptych_closed_and_semantic(self) -> None:
        skill = (runner.SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Never repeat the triptych in a second summary", skill)
        self.assertIn("book, chapter, and subsection", skill)
        self.assertIn("never create a fourth field", skill)
        self.assertIn("Do not inspect the workspace merely to restate supplied facts", skill)
        self.assertIn("one to four numbered points", skill)
        self.assertIn("one to four suggested steps", skill)
        self.assertIn("lettered `A.` through at most `D.`", skill)
        self.assertIn("put the recommended option first", skill)
        self.assertIn("numbers refer only to current-state points", skill)
        self.assertIn("letters refer only to suggested steps or options", skill)

    def test_orient_cases_reject_file_urls_in_tlgf_answers(self) -> None:
        for case in runner.load_manifest()["cases"]:
            if case["mode"] not in {"orient", "resume"}:
                continue
            self.assertIn("file://", case["treatment_forbidden_terms"], case["id"])

    def test_real_repository_prompt_forbids_test_execution(self) -> None:
        manifest = runner.load_manifest()
        case = runner.select_cases(manifest, ["flask-error-handlers"])[0]
        self.assertIn("don't run the test or install anything", case["prompt"])
        self.assertNotIn("Read-only", case["prompt"])
        self.assertIn(
            "pytest tests/test_user_error_handler.py::test_default_error_handler",
            case["required_term_groups"][-1],
        )

    def test_real_repository_routing_mechanism_is_judged_semantically(self) -> None:
        case = runner.select_cases(
            runner.load_manifest(), ["flask-error-handlers"]
        )[0]
        exact_terms = {term for group in case["required_term_groups"] for term in group}
        self.assertIn("_find_error_handler", exact_terms)
        self.assertIn("/bp/missing", exact_terms)
        self.assertNotIn("routing_boundary", case["orientation_facts"])
        self.assertTrue(
            any("request.blueprints is empty" in fact for fact in case["semantic_facts"])
        )

    def test_useful_signal_prompt_is_natural_and_deferral_is_judged(self) -> None:
        case = runner.select_cases(
            runner.load_manifest(), ["useful-signal"]
        )[0]
        self.assertNotIn("worth noticing", case["prompt"].lower())
        self.assertNotIn("surface", case["prompt"].lower())
        self.assertNotIn("routing", case["orientation_facts"])
        self.assertTrue(any("deferred" in fact for fact in case["semantic_facts"]))
        progress_terms = case["orientation_facts"]["progress"]
        self.assertTrue(
            runner.match_groups("72 / 120 shards", [progress_terms])[0]["passed"]
        )

class ResumeTests(unittest.TestCase):
    def make_run(
        self, directory: str
    ) -> tuple[
        Path,
        dict[str, object],
        list[dict[str, object]],
        dict[str, object],
    ]:
        run_root = Path(directory) / "resume-example"
        run_root.mkdir()
        manifest = runner.load_manifest()
        cases = [manifest["cases"][0]]
        versions = {
            "codex": {
                "executable": "/example/codex",
                "version": "codex-cli test",
                "requested_model": None,
                "display_model": None,
            }
        }
        environment = {
            "run_id": run_root.name,
            "status": "running",
            "agents": versions,
            "seed": 42,
            "timeout_seconds": 300,
            "max_attempts": 2,
            "manifest_sha256": runner.manifest_digest(),
            "fixture_set_sha256": runner.fixture_set_digest(manifest, cases),
            "skill_sha256": runner.core.repository_digest(runner.SKILL_ROOT),
        }
        (run_root / "runs").mkdir()
        (run_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (run_root / "environment.json").write_text(
            json.dumps(environment), encoding="utf-8"
        )
        return run_root, manifest, cases, versions

    def test_resume_accepts_only_matching_saved_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_root, manifest, cases, versions = self.make_run(directory)
            expected = runner.expected_results(manifest, cases, ["codex"], 1, 42)
            filename, specification = next(iter(expected.items()))
            result = {
                "schema_version": runner.RESULT_SCHEMA_VERSION,
                "run_id": run_root.name,
                "agent": specification["agent"],
                "agent_version": versions["codex"]["version"],
                "case_id": specification["case_id"],
                "condition": specification["condition"],
                "repetition": specification["repetition"],
                "condition_order": specification["condition_order"],
                "fixture_sha256": specification["fixture_sha256"],
                "prompt": specification["prompt"],
                "prompt_sha256": specification["prompt_sha256"],
                "requested_model": None,
                "max_attempts": 2,
            }
            (run_root / "runs" / filename).write_text(
                json.dumps(result), encoding="utf-8"
            )

            _, existing, count = runner.validate_resume_run(
                run_root,
                manifest,
                cases,
                ["codex"],
                1,
                42,
                300,
                2,
                versions,
                False,
            )

        self.assertEqual(existing, {filename})
        self.assertEqual(count, 2)

    def test_resume_rejects_changed_frozen_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_root, manifest, cases, versions = self.make_run(directory)
            environment_path = run_root / "environment.json"
            environment = json.loads(environment_path.read_text(encoding="utf-8"))
            environment["skill_sha256"] = "changed"
            environment_path.write_text(json.dumps(environment), encoding="utf-8")

            with self.assertRaisesRegex(runner.BenchmarkError, "skill_sha256 changed"):
                runner.validate_resume_run(
                    run_root,
                    manifest,
                    cases,
                    ["codex"],
                    1,
                    42,
                    300,
                    2,
                    versions,
                    False,
                )

    def test_resume_rebuilds_only_an_incomplete_workspace(self) -> None:
        case = runner.load_manifest()["cases"][0]
        with tempfile.TemporaryDirectory() as directory:
            run_root = Path(directory)
            workspace = runner.create_workspace(
                run_root, "codex", "control", case, {}, repetition=1
            )
            marker = workspace / "partial-output.txt"
            marker.write_text("interrupted", encoding="utf-8")
            rebuilt = runner.create_workspace(
                run_root,
                "codex",
                "control",
                case,
                {},
                repetition=1,
                replace_incomplete=True,
            )
            self.assertEqual(workspace, rebuilt)
            self.assertFalse(marker.exists())

    def test_regrade_repetitions_use_separate_workspaces(self) -> None:
        root = Path("/tmp/regrade")
        common = {
            "agent": "agy",
            "case_id": "stale-state",
            "condition": "tlgf",
        }
        first = runner.regrade_workspace_path(root, {**common, "repetition": 1})
        second = runner.regrade_workspace_path(root, {**common, "repetition": 2})
        control = runner.regrade_workspace_path(
            root, {**common, "condition": "control", "repetition": 1}
        )

        self.assertNotEqual(first, second)
        self.assertNotEqual(first, control)
        self.assertEqual(first, root / "agy" / "stale-state" / "tlgf" / "r1")


class EvaluationTests(unittest.TestCase):
    def case(self, case_id: str) -> dict[str, object]:
        return next(
            case for case in runner.load_manifest()["cases"] if case["id"] == case_id
        )

    def test_standalone_treatment_passes_without_exec(self) -> None:
        case = self.case("standalone-restraint")
        response = (
            "An idempotent request has the same intended effect when repeated. "
            "For example, repeating `PUT /users/42` with the same representation "
            "leaves user 42 in the same resulting state, even if each request is logged."
        )
        evaluation = runner.evaluate_response(
            case,
            "tlgf",
            response,
            runner.fixture_path(case),
            ["read-tlgf-skill"],
            execution_succeeded=True,
            workspace_unchanged=True,
            visible_text=response,
        )
        self.assertTrue(evaluation["passed"])
        self.assertEqual(evaluation["missing_orientation_fact_count"], 0)

    def test_rhetorical_question_in_quotes_is_not_user_input_request(self) -> None:
        self.assertEqual(runner.count_questions('Retry without asking "did it land?"'), 0)
        self.assertEqual(runner.count_questions("Do you want me to continue?"), 1)
        self.assertEqual(
            runner.count_questions("| Method | Idempotent? | Why? |\n| --- | --- | --- |"),
            0,
        )
        self.assertEqual(runner.count_questions("### Why?\nBecause retries happen."), 0)

    def test_rubric_accepts_semantically_equivalent_continuity_phrasing(self) -> None:
        lineage = self.case("run-lineage")
        count_groups = lineage["required_term_groups"][2:4]
        matches = runner.match_groups(
            "Alpha passed 4 of 6 gates; beta passed 5 of 6 gates.",
            count_groups,
        )
        self.assertTrue(all(match["passed"] for match in matches))
        self.assertNotIn("different model", {term for group in lineage["required_term_groups"] for term in group})
        self.assertTrue(any("outside the Qwen prompt comparison" in fact for fact in lineage["semantic_facts"]))

        park = self.case("park-resume")
        self.assertNotIn("stopping_point", park["orientation_facts"])
        self.assertTrue(
            runner.match_groups(
                "Open tests/retry.test.ts next.",
                [park["orientation_facts"]["next_action"]],
            )[0]["passed"]
        )

    def test_word_budget_does_not_erase_a_correct_answer(self) -> None:
        case = self.case("standalone-restraint")
        response = (
            "An idempotent request has the same intended effect when repeated. "
            "For example, PUT leaves the resource in the same state. DELETE also "
            "has the same resulting state when repeated. "
            + "Supporting detail. " * 80
        )
        evaluation = runner.evaluate_response(
            case,
            "tlgf",
            response,
            runner.fixture_path(case),
            ["read-tlgf-skill"],
            execution_succeeded=True,
            workspace_unchanged=True,
            visible_text=response,
        )
        self.assertTrue(evaluation["quality_passed"])
        self.assertTrue(evaluation["passed"])
        self.assertFalse(evaluation["budget_passed"])
        self.assertFalse(evaluation["all_checks_passed"])

    def test_stale_state_response_passes_with_bound_evidence(self) -> None:
        case = self.case("stale-state")
        response = """**You are here:** TLGF benchmark › continuity regression suite › clarity-fork › gamma

---

**What's happening now:**

1. `.tlgf/STATE.md` is stale and still names beta, but `reports/index.json` names gamma as current.
2. `reports/beta/summary.json` records beta as the predecessor, while `reports/gamma/summary.json` records 6/6 only after one retry: the first attempt returned no usable answer, so reliability remains unresolved.

---

**Suggested next steps:**

A. Inspect gamma's first-attempt trace before treating the run as reliable.

---
"""
        evaluation = runner.evaluate_response(
            case,
            "tlgf",
            response,
            runner.fixture_path(case),
            ["skill-tool-tlgf"],
            execution_succeeded=True,
            workspace_unchanged=True,
            visible_text=response,
        )
        self.assertTrue(evaluation["passed"])
        self.assertEqual(evaluation["missing_orientation_fact_count"], 0)

    def test_stale_state_rejects_hidden_retry_failure(self) -> None:
        case = self.case("stale-state")
        response = "Gamma is current and passed 6/6 on the first attempt."
        evaluation = runner.evaluate_response(
            case,
            "control",
            response,
            runner.fixture_path(case),
            [],
            execution_succeeded=True,
            workspace_unchanged=True,
            visible_text=response,
        )
        self.assertFalse(evaluation["passed"])
        self.assertFalse(evaluation["checks"]["forbidden_terms"])

    def test_treatment_rejects_framework_vocabulary_only_for_tlgf(self) -> None:
        case = self.case("stale-state")
        response = (
            "Beta is the predecessor. Gamma replaced beta after one retry, "
            "and the first attempt failed on clarity-fork.\n\nProgress so far: 5/6 gates."
        )
        control = runner.evaluate_response(
            case,
            "control",
            response,
            runner.fixture_path(case),
            [],
            execution_succeeded=True,
            workspace_unchanged=True,
            visible_text=response,
        )
        treatment = runner.evaluate_response(
            case,
            "tlgf",
            response,
            runner.fixture_path(case),
            ["skill-tool-tlgf"],
            execution_succeeded=True,
            workspace_unchanged=True,
            visible_text=response,
        )
        self.assertTrue(control["checks"]["forbidden_terms"])
        self.assertFalse(treatment["checks"]["forbidden_terms"])

    def test_useful_signal_can_be_surfaced_without_derailing_import(self) -> None:
        case = self.case("useful-signal")
        response = """**You are here:** Customer analytics › August events backfill › analytics-staging › backfill-2026-08-20

---

**What's happening now:**

1. `.tlgf/STATE.md` and `runs/backfill-2026-08-20/status.json` show 72 of 120 shards complete with no failures; checksums and deduplication are pending.
2. A preliminary, nondeduplicated signal in `runs/backfill-2026-08-20/preview.json` puts partner-north at 18.4% trial-to-paid versus the validated 6.2% July baseline in `notes/baseline.md`; keep it parked until validation.

---

**Suggested next steps:**

A. Keep the backfill running.
B. Validate checksums and deduplication before investigating partner-north.

---
"""
        evaluation = runner.evaluate_response(
            case,
            "tlgf",
            response,
            runner.fixture_path(case),
            ["skill-tool-tlgf"],
            execution_succeeded=True,
            workspace_unchanged=True,
            visible_text=response,
        )
        self.assertTrue(evaluation["passed"])
        self.assertEqual(evaluation["missing_orientation_fact_count"], 0)
        self.assertEqual(evaluation["triptych_separator_count"], 3)

    def test_treatment_triptych_rejects_text_after_the_closing_rule(self) -> None:
        case = self.case("useful-signal")
        response = """**You are here:** Customer analytics › backfill-2026-08-20

---

**What's happening now:**

1. 72/120 shards are complete.
2. The preliminary partner-north signal is 18.4% versus the 6.2% baseline and remains unvalidated.

---

**Suggested next steps:**

A. Finish the import.
B. Revisit partner-north after validation.

---

Continuing with read-only inspection only.
"""
        evaluation = runner.evaluate_response(
            case,
            "tlgf",
            response,
            runner.fixture_path(case),
            ["skill-tool-tlgf"],
            execution_succeeded=True,
            workspace_unchanged=True,
            visible_text=response,
            evidence_text=" ".join(case["required_paths"]),
        )
        self.assertFalse(evaluation["checks"]["triptych_closed"])
        self.assertFalse(evaluation["passed"])

    def test_treatment_triptych_rejects_a_preamble(self) -> None:
        case = self.case("stale-state")
        response = """Status follows.

**You are here:** TLGF benchmark › clarity-fork › gamma

---

**What's happening now:**

1. `.tlgf/STATE.md` is stale: it names beta, while `reports/index.json` names gamma as current.
2. Beta is the predecessor. Gamma reached 6/6 after one retry because its first attempt returned no answer, so reliability remains unresolved.

---

**Suggested next steps:**

A. Inspect gamma's first-attempt trace.

---
"""
        evaluation = runner.evaluate_response(
            case,
            "tlgf",
            response,
            runner.fixture_path(case),
            ["skill-tool-tlgf"],
            execution_succeeded=True,
            workspace_unchanged=True,
            visible_text=response,
            evidence_text=" ".join(case["required_paths"]),
        )
        self.assertFalse(evaluation["checks"]["triptych_first_content"])
        self.assertFalse(evaluation["passed"])

    def test_needs_user_signal_is_conditional_and_must_come_first(self) -> None:
        blocker = self.case("decision-blocker")
        response = """⛔ **Needs you** — choose A or B.

**You are here:** Release › migration-dry-run-20260821 › owner decision

---

**What's happening now:**

1. The dry run shows that 14 customer records would be overwritten.
2. Recovery is reversible only before deployment; no write has started.

---

**Suggested next steps:**

A. Delay the release, repair the records, and repeat the dry run (recommended).
B. Exclude the 14 records and document the follow-up repair.

---
"""
        valid = runner.evaluate_response(
            blocker,
            "tlgf",
            response,
            runner.fixture_path(blocker),
            ["skill-tool-tlgf"],
            execution_succeeded=True,
            workspace_unchanged=True,
            visible_text=response,
            evidence_text="dry-run.md",
        )
        self.assertTrue(valid["checks"]["triptych_first_content"])
        self.assertTrue(valid["checks"]["needs_user_signal"])
        self.assertTrue(valid["passed"])

        misplaced = response.replace(
            "⛔ **Needs you** — choose A or B.\n\n", ""
        ).replace(
            "**You are here:**",
            "**You are here:**\n\n⛔ **Needs you** — choose A or B.\n\n",
            1,
        )
        invalid = runner.evaluate_response(
            blocker,
            "tlgf",
            misplaced,
            runner.fixture_path(blocker),
            ["skill-tool-tlgf"],
            execution_succeeded=True,
            workspace_unchanged=True,
            visible_text=misplaced,
            evidence_text="dry-run.md",
        )
        self.assertFalse(invalid["checks"]["needs_user_signal"])
        self.assertFalse(invalid["passed"])

        nonblocking = self.case("useful-signal")
        forbidden = runner.evaluate_response(
            nonblocking,
            "tlgf",
            "⛔ **Needs you**\n",
            runner.fixture_path(nonblocking),
            ["skill-tool-tlgf"],
            execution_succeeded=True,
            workspace_unchanged=True,
            visible_text="⛔ **Needs you**\n",
        )
        self.assertFalse(forbidden["checks"]["needs_user_signal"])

    def test_addressable_expand_does_not_replay_the_triptych(self) -> None:
        case = self.case("addressable-expand")
        response = (
            "Point 2: Qwen/OpenCode produced no final answer on the first attempt, "
            "and the retry timed out. This is host-reliability evidence; we cannot "
            "judge its writing style from that run."
        )
        evaluation = runner.evaluate_response(
            case,
            "tlgf",
            response,
            runner.fixture_path(case),
            ["skill-tool-tlgf"],
            execution_succeeded=True,
            workspace_unchanged=True,
            visible_text=response,
            evidence_text="frame.md",
        )
        self.assertFalse(evaluation["triptych_expected"])
        self.assertTrue(evaluation["passed"])

    def test_triptych_uses_distinct_numeric_and_lettered_addresses(self) -> None:
        sequential = """**You are here:** Example › verification

---

**What's happening now:**

1. The implementation is complete.
2. Validation remains.

---

**Suggested next steps:**

A. Run the focused checks.
B. Review the rendered output.

---
"""
        alternatives = """**You are here:** Example › blocked choice

---

**What's happening now:**

1. Two safe paths remain.

---

**Suggested next steps:**

A. Continue locally (recommended) — fastest feedback.
B. Wait for remote capacity — closer production match.

---
"""
        mixed = alternatives.replace(
            "B. Wait for remote capacity — closer production match.",
            "1. Wait for remote capacity — closer production match.",
        )

        self.assertTrue(runner.triptych_list_structure(sequential)["current_points_valid"])
        self.assertTrue(runner.triptych_list_structure(sequential)["suggested_steps_valid"])
        self.assertTrue(runner.triptych_list_structure(alternatives)["suggested_steps_valid"])
        self.assertFalse(runner.triptych_list_structure(mixed)["suggested_steps_valid"])

    def test_required_path_can_be_verified_from_tool_trace(self) -> None:
        case = self.case("park-resume")
        response = (
            "API client retry investigation on fix/retry. TimeoutError bypasses "
            "backoff. Timeout coverage is missing, so the regression hypothesis "
            "remains unresolved. Next inspect tests/retry.test.ts."
        )
        trace = " ".join(case["required_paths"])
        evaluation = runner.evaluate_response(
            case,
            "control",
            response,
            runner.fixture_path(case),
            [],
            execution_succeeded=True,
            workspace_unchanged=True,
            visible_text=response,
            evidence_text=trace,
        )
        self.assertTrue(evaluation["checks"]["required_paths"])
        self.assertEqual(
            evaluation["required_path_evidence_scope"],
            "response_or_tool_trace",
        )

    def test_generic_activation_parser_recognizes_tlgf(self) -> None:
        events = [
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "sed -n 1,120p .agents/skills/tlgf/SKILL.md",
                },
            }
        ]
        self.assertEqual(
            runner.core.skill_activation_evidence(events, "tlgf"),
            ["read-tlgf-skill"],
        )

    def test_generic_activation_parser_recognizes_declaration(self) -> None:
        events = [
            {
                "type": "item.completed",
                "item": {
                    "type": "agent_message",
                    "text": "I'm using the TLGF skill to restore the current run.",
                },
            }
        ]
        self.assertEqual(
            runner.core.skill_activation_evidence(events, "tlgf"),
            ["declared-tlgf-skill"],
        )

    def test_fixture_cases_allow_read_only_inspection(self) -> None:
        for case_id in ("run-lineage", "park-resume", "stale-state", "useful-signal", "decision-blocker"):
            prompt = self.case(case_id)["prompt"]
            self.assertNotIn("Read-only", prompt)
            self.assertNotIn("run commands", prompt)
            self.assertNotIn("Do not replay", prompt)
            self.assertNotIn("genuinely needs my decision", prompt)

class ReportTests(unittest.TestCase):
    def write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_shared_renderer_uses_tlgf_labels_and_keeps_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_root = Path(directory)
            manifest = runner.load_manifest()
            manifest["cases"] = [manifest["cases"][0]]
            self.write_json(run_root / "manifest.json", manifest)
            grader_manifest = json.loads(json.dumps(manifest))
            grader_manifest["report"]["title"] = "Regraded TLGF report"
            self.write_json(run_root / "grader-manifest.json", grader_manifest)
            self.write_json(
                run_root / "environment.json",
                {"run_id": "example", "seed": 42},
            )
            common = {
                "agent": "codex",
                "case_id": "standalone-restraint",
                "repetition": 1,
                "agent_status": "SUCCESS",
                "response_words": 10,
                "duration_seconds": 1,
                "usage": {"output_tokens": 20, "total_tokens": 100},
                "evaluation": {
                    "passed": True,
                    "budget_passed": True,
                    "checks": {"nonempty": True},
                },
                "attempt_count": 1,
                "retry_count": 0,
                "attempt_statuses": ["SUCCESS"],
                "attempts": [
                    {
                        "attempt_number": 1,
                        "agent_status": "SUCCESS",
                        "response": "Answer",
                        "usage": {"output_tokens": 20},
                    }
                ],
            }
            self.write_json(
                run_root / "runs" / "control.json",
                {**common, "condition": "control", "prompt": "Prompt", "response": "Control"},
            )
            self.write_json(
                run_root / "runs" / "tlgf.json",
                {
                    **common,
                    "condition": "tlgf",
                    "prompt": "Prompt\n\nTLGF",
                    "response": "Treatment",
                    "attempt_count": 2,
                    "retry_count": 1,
                    "attempt_statuses": ["NO_FINAL_ANSWER", "SUCCESS"],
                    "attempts": [
                        {
                            "attempt_number": 1,
                            "agent_status": "NO_FINAL_ANSWER",
                            "response": "",
                            "usage": {"output_tokens": 5},
                        },
                        {
                            "attempt_number": 2,
                            "agent_status": "SUCCESS",
                            "response": "Treatment",
                            "usage": {"output_tokens": 20},
                        },
                    ],
                },
            )
            data = runner.renderer.build_report_data(run_root)
            output = runner.renderer.render_report(run_root)
            rendered = output.read_text(encoding="utf-8")

        self.assertEqual(data["controlLabel"], "Control")
        self.assertEqual(data["treatmentLabel"], "TLGF")
        self.assertEqual(data["title"], "Regraded TLGF report")
        self.assertEqual(data["pairs"][0]["tlgd"]["attemptCount"], 2)
        self.assertEqual(len(data["pairs"][0]["tlgd"]["attempts"]), 2)
        self.assertTrue(data["summaries"][0]["budgetTracked"])
        self.assertEqual(data["summaries"][0]["allTotalTokenReduction"], 0.0)
        self.assertIn('"treatmentLabel":"TLGF"', rendered)
        self.assertIn("All attempts", rendered)


if __name__ == "__main__":
    unittest.main()


class BlindingTests(unittest.TestCase):
    def test_core_hides_the_condition_segment_of_workspace_paths(self) -> None:
        treatment = "According to [dry-run.md](RUN_ROOT/workspaces/agy/tlgf/workspace/dry-run.md) the run is beta."
        control = treatment.replace("/tlgf/", "/control/")
        neutral = runner.core.neutralize_workspace_paths(control)
        self.assertEqual(runner.core.neutralize_workspace_paths(treatment), neutral)
        self.assertEqual(neutral, "According to [dry-run.md](RUN_ROOT/workspaces/agy/CONDITION/workspace/dry-run.md) the run is beta.")

