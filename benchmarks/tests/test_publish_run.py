from __future__ import annotations

import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

PUBLISH_PATH = Path(__file__).resolve().parents[1] / "publish_run.py"
SPEC = importlib.util.spec_from_file_location("benchmark_publish_run", PUBLISH_PATH)
publish_run = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(publish_run)


def make_run(root: Path, report: str) -> Path:
    run_root = root / "results" / "example-run__20260101T000000Z"
    (run_root / "runs").mkdir(parents=True)
    (run_root / "runs" / "claude__case__control__r1.json").write_text("{}", encoding="utf-8")
    (run_root / "environment.json").write_text(json.dumps({"run_id": run_root.name}), encoding="utf-8")
    (run_root / "REPORT.md").write_text(report, encoding="utf-8")
    (run_root / "summary.json").write_text("{}", encoding="utf-8")
    return run_root


class PublishRunTests(unittest.TestCase):
    def test_publishes_reports_and_redacts_run_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_root = make_run(root, "placeholder")
            (run_root / "REPORT.md").write_text(
                f"See {run_root}/workspaces/claude/control/repository/lib/response.js", encoding="utf-8"
            )
            env_file = root / ".env"
            env_file.write_text("SECRET_KEY=abcdefghijkl\nEMBEDDING_INPUT_TYPE=document\n", encoding="utf-8")
            (run_root / "REPORT.md").write_text(
                f"See file://{run_root}/workspaces/claude/control/repository/lib/response.js in the document", encoding="utf-8"
            )
            destination = publish_run.publish(run_root, root / "published", env_file)
            published = (destination / "REPORT.md").read_text(encoding="utf-8")
            self.assertEqual(published, "See file://RUN_ROOT/workspaces/claude/control/repository/lib/response.js in the document")
            (run_root / "environment.json").write_text(
                json.dumps({"run_id": run_root.name, "executable": str(Path.home() / ".local" / "bin" / "agy")}), encoding="utf-8"
            )
            import shutil
            shutil.rmtree(root / "published")
            destination = publish_run.publish(run_root, root / "published", env_file)
            self.assertIn('"~/.local/bin/agy"', (destination / "environment.json").read_text(encoding="utf-8"))
            self.assertTrue((destination / "summary.json").is_file())
            self.assertFalse((destination / "runs").exists())
            index = (root / "published" / "INDEX.md").read_text(encoding="utf-8")
            self.assertIn(run_root.name, index)

    def test_refuses_foreign_paths_file_urls_and_env_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_root = make_run(root, "Answer cites file:///Users/someone/project/lib/app.js")
            env_file = root / ".env"
            env_file.write_text("API_KEY=supersecretvalue\n", encoding="utf-8")
            with self.assertRaises(publish_run.PublishError) as caught:
                publish_run.publish(run_root, root / "published", env_file)
            self.assertIn("REPORT.md", str(caught.exception))
            self.assertFalse((root / "published").exists())

            run_root_2 = make_run(root / "second", "Leaked token supersecretvalue in report")
            with self.assertRaises(publish_run.PublishError) as caught_2:
                publish_run.publish(run_root_2, root / "published", env_file)
            self.assertIn("<value from .env>", str(caught_2.exception))

    def test_blind_review_hides_the_condition_segment_of_workspace_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_root = make_run(root, "Report keeps workspaces/codex/control/ visible")
            (run_root / "BLIND_REVIEW.md").write_text(
                f"A: file://{run_root}/workspaces/codex/tlgf/repository/lib/response.js\n"
                f"B: file://{run_root}/workspaces/codex/control/repository/lib/response.js\n",
                encoding="utf-8",
            )
            env_file = root / ".env"
            env_file.write_text("", encoding="utf-8")
            destination = publish_run.publish(run_root, root / "published", env_file)
            published = (destination / "BLIND_REVIEW.md").read_text(encoding="utf-8")
            self.assertNotIn("/tlgf/", published)
            self.assertNotIn("/control/", published)
            self.assertEqual(published.count("file://RUN_ROOT/workspaces/codex/CONDITION/repository/lib/response.js"), 2)
            self.assertIn("workspaces/codex/control/", (destination / "REPORT.md").read_text(encoding="utf-8"))
            self.assertFalse((destination / "BLIND_REVIEW.html").exists())

    def test_refuses_to_overwrite_an_existing_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_root = make_run(root, "clean report")
            publish_run.publish(run_root, root / "published", root / ".env")
            with self.assertRaises(publish_run.PublishError):
                publish_run.publish(run_root, root / "published", root / ".env")

    def test_publish_sanitizes_html_and_validates_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_root = make_run(root, "clean report")
            other_home_file = Path.home() / "other-project" / "file.md"
            other_temp_file = Path(tempfile.gettempdir()) / "scratch" / "data.csv"
            report_data = {
                "pairs": [
                    {
                        "control": {
                            "rawJsonUrl": "runs/c1.json",
                            "response": f"[run_file](<{run_root}/workspaces/app.js>)\n[home_file](<{other_home_file}>)",
                        },
                        "treatment": {
                            "rawJsonUrl": "runs/t1.json",
                            "response": f"[temp_file](<{other_temp_file}>)",
                        },
                    }
                ],
                "blindReviewUrl": "BLIND_REVIEW.md",
            }
            html_content = (
                "<!DOCTYPE html><html><body>"
                '<script id="report-data" type="application/json">'
                + publish_run.json_for_script(report_data)
                + "</script></body></html>"
            )
            (run_root / "REPORT.html").write_text(html_content, encoding="utf-8")
            destination = publish_run.publish(run_root, root / "published", root / ".env")
            published_html = (destination / "REPORT.html").read_text(encoding="utf-8")
            self.assertNotIn("runs/c1.json", published_html)
            self.assertNotIn(str(run_root), published_html)
            self.assertNotIn(str(Path.home()), published_html)
            m = re.search(r'<script id="report-data" type="application/json">(.*?)</script>', published_html, re.DOTALL)
            self.assertIsNotNone(m)
            parsed = json.loads(m.group(1))
            self.assertIsNone(parsed["pairs"][0]["control"]["rawJsonUrl"])
            self.assertIsNone(parsed["blindReviewUrl"])
            control_resp = parsed["pairs"][0]["control"]["response"]
            treatment_resp = parsed["pairs"][0]["treatment"]["response"]
            self.assertIn("<RUN_ROOT/workspaces/app.js>", control_resp)
            self.assertIn("<~/other-project/file.md>", control_resp)
            self.assertNotIn(r"<\~", control_resp)
            self.assertNotIn(r"\RUN_ROOT", control_resp)
            self.assertIn("<TMPDIR/scratch/data.csv>", treatment_resp)


if __name__ == "__main__":
    unittest.main()
