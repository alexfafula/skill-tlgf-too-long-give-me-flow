#!/usr/bin/env python3
"""Copy the publishable part of a benchmark run into the tracked results directory.

Usage:
    python3 benchmarks/publish_run.py benchmarks/results/RUN_DIRECTORY [--dest benchmarks/published]

Only reports and summaries are published: REPORT.md, REPORT.html, summary.json,
environment.json, the manifest, JUDGE.md, judge.json, and BLIND_REVIEW.md.
Raw traces under runs/ and workspaces are never copied. Absolute paths that
point inside the run directory are replaced with RUN_ROOT before publication.
In BLIND_REVIEW.md the condition directory of workspace paths is replaced with
CONDITION so the sheet stays blind.
The script refuses to publish when any file still contains a machine-specific
path, a file:// URL outside the redacted run root, or the value of a sensitive
key (KEY, TOKEN, SECRET, PASSWORD, CREDENTIAL, URL) from the local .env file.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

BENCHMARK_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = BENCHMARK_ROOT.parent
DEFAULT_DEST = BENCHMARK_ROOT / "published"
PUBLISHABLE = (
    "REPORT.md",
    "REPORT.html",
    "summary.json",
    "environment.json",
    "manifest.json",
    "grader-manifest.json",
    "JUDGE.md",
    "judge.json",
    "SUMMARY.md",
    "per-host-summary.json",
    "BLIND_REVIEW.md",
)
SENSITIVE_KEY = re.compile(r"(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|URL)", re.IGNORECASE)
LEAK_PATTERNS = (
    re.compile(r"file:///"),  # an absolute file URL; the redacted form is file://RUN_ROOT/...
    re.compile(r"/Users/[^/\s\"'`)]+"),
    re.compile(r"/home/[^/\s\"'`)]+"),
    re.compile(r"/private/var/folders/"),
    re.compile(r"/var/folders/"),
)


class PublishError(RuntimeError):
    """A publication check failed."""


WORKSPACE_CONDITION_SEGMENT = re.compile(r"(workspaces/[^/\s\"'`()<>]+/)[^/\s\"'`()<>]+/")


def neutralize_workspace_paths(text: str) -> str:
    """Match neutralize_workspace_paths() in run.py: hide workspaces/<agent>/<condition>/ from a blinded reader."""
    return WORKSPACE_CONDITION_SEGMENT.sub(r"\1CONDITION/", text)


def env_values(env_file: Path) -> list[str]:
    if not env_file.is_file():
        return []
    values: list[str] = []
    for line in env_file.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if not match or not SENSITIVE_KEY.search(match.group(1)):
            continue
        value = match.group(2).strip().strip("\"'")
        if len(value) >= 8:
            values.append(value)
    return values


def redact_run_paths(text: str, run_root: Path) -> str:
    """Replace the run directory, the temp directory, and the home directory."""
    candidates = {str(run_root), str(run_root.resolve())}
    real_home = str(Path.home().resolve())
    for candidate in sorted(candidates, key=len, reverse=True):
        text = text.replace(candidate.replace("/", r"\/"), "RUN_ROOT")
        text = text.replace(candidate, "RUN_ROOT")
        if candidate.startswith(real_home):
            candidate_home = candidate.replace(real_home, "~", 1)
            text = text.replace(candidate_home.replace("/", r"\/"), "RUN_ROOT")
            text = text.replace(candidate_home, "RUN_ROOT")
    temp = tempfile.gettempdir().rstrip("/")
    for prefix in sorted({temp, str(Path(temp).resolve()), "/private" + temp if not temp.startswith("/private") else temp}, key=len, reverse=True):
        if prefix:
            text = text.replace(prefix.replace("/", r"\/"), "TMPDIR")
            text = text.replace(prefix, "TMPDIR")
    for home in sorted({str(Path.home()), real_home}, key=len, reverse=True):
        text = text.replace(home.replace("/", r"\/"), "~")
        text = text.replace(home, "~")
    text = text.replace(r"<\RUN_ROOT", "<RUN_ROOT")
    text = text.replace(r"\RUN_ROOT", "RUN_ROOT")
    text = text.replace(r"<\~", "<~")
    text = text.replace(r"\~", "~")
    text = text.replace(r"<\TMPDIR", "<TMPDIR")
    text = text.replace(r"\TMPDIR", "TMPDIR")
    return text


def json_for_script(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        encoded.replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def redact_data_paths(value: Any, run_root: Path) -> Any:
    """Structurally anonymize data dictionary before JSON serialization."""
    if isinstance(value, str):
        return redact_run_paths(value, run_root)
    if isinstance(value, dict):
        return {k: redact_data_paths(v, run_root) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_data_paths(v, run_root) for v in value]
    return value


def find_leaks(text: str, secrets: list[str]) -> list[str]:
    leaks: list[str] = []
    for pattern in LEAK_PATTERNS:
        match = pattern.search(text)
        if match:
            leaks.append(match.group(0))
    for secret in secrets:
        if secret in text:
            leaks.append("<value from .env>")
    return leaks


def publish(run_root: Path, dest_root: Path, env_file: Path) -> Path:
    if not (run_root / "environment.json").is_file():
        raise PublishError(f"{run_root} is not a benchmark run directory")
    run_id = run_root.name
    destination = dest_root / run_id
    if destination.exists():
        raise PublishError(f"{destination} already exists; remove it first to republish")
    secrets = env_values(env_file)
    staged: dict[str, bytes] = {}
    problems: list[str] = []
    for name in PUBLISHABLE:
        source = run_root / name
        if not source.is_file():
            continue
        raw = source.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"{name}: not UTF-8 text")
            continue
        if name == "REPORT.html":
            match = re.search(r'(<script id="report-data" type="application/json">)(.*?)(</script>)', text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(2))
                    data = redact_data_paths(data, run_root)
                    for pair in data.get("pairs", []):
                        for key in ("control", "treatment", "tlgd", "tlgf"):
                            res = pair.get(key)
                            if isinstance(res, dict) and "rawJsonUrl" in res:
                                res["rawJsonUrl"] = None
                    if not (run_root / "BLIND_REVIEW.md").is_file():
                        data["blindReviewUrl"] = None
                    safe_encoded = json_for_script(data)
                    prefix = redact_run_paths(text[:match.start(1)], run_root)
                    script_open = match.group(1)
                    script_close = match.group(3)
                    suffix = redact_run_paths(text[match.end(3):], run_root)
                    text = prefix + script_open + safe_encoded + script_close + suffix
                except json.JSONDecodeError as err:
                    problems.append(f"{name}: invalid embedded JSON: {err}")
                    continue
            else:
                text = redact_run_paths(text, run_root)
        elif name.endswith(".json"):
            try:
                data = json.loads(text)
                data = redact_data_paths(data, run_root)
                text = json.dumps(data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                text = redact_run_paths(text, run_root)
        else:
            text = redact_run_paths(text, run_root)

        if name in ("BLIND_REVIEW.md", "BLIND_REVIEW.html"):
            text = neutralize_workspace_paths(text)
        if name.endswith(".json"):
            try:
                json.loads(text)
            except json.JSONDecodeError as err:
                problems.append(f"{name}: invalid JSON: {err}")
                continue
        if name.endswith(".html"):
            for m in re.finditer(r'<script\b[^>]*\btype=["\']application/json["\'][^>]*>(.*?)</script>', text, re.DOTALL):
                try:
                    json.loads(m.group(1))
                except json.JSONDecodeError as err:
                    problems.append(f"{name}: invalid embedded JSON: {err}")
        leaks = find_leaks(text, secrets)
        if leaks:
            problems.append(f"{name}: {', '.join(sorted(set(leaks)))}")
            continue
        staged[name] = text.encode("utf-8")
    if "REPORT.md" not in staged and "REPORT.md" not in [p.split(":")[0] for p in problems]:
        problems.append("REPORT.md is missing")
    if problems:
        raise PublishError("refusing to publish:\n  " + "\n  ".join(problems))
    destination.mkdir(parents=True)
    for name, content in staged.items():
        (destination / name).write_bytes(content)
    index = dest_root / "INDEX.md"
    line = f"- [`{run_id}`]({run_id}/REPORT.md)"
    if index.is_file():
        existing = index.read_text(encoding="utf-8")
        if line not in existing:
            index.write_text(existing.rstrip("\n") + "\n" + line + "\n", encoding="utf-8")
    else:
        index.write_text("# Published benchmark runs\n\n" + line + "\n", encoding="utf-8")
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish the reports of a completed benchmark run")
    parser.add_argument("run", type=Path, help="Run directory under benchmarks/results")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST, help="Tracked destination directory")
    parser.add_argument("--env-file", type=Path, default=REPOSITORY_ROOT / ".env")
    args = parser.parse_args(argv)
    try:
        destination = publish(args.run.resolve(), args.dest, args.env_file)
    except PublishError as error:
        print(f"Publish failed: {error}", file=sys.stderr)
        return 1
    print(f"Published: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
