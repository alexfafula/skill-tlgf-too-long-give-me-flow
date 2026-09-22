#!/usr/bin/env python3
"""Shared core utilities and execution engine for benchmark runners."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = (
    BENCHMARK_ROOT / "tlgf" / "manifest.json"
    if (BENCHMARK_ROOT / "tlgf" / "manifest.json").is_file()
    else BENCHMARK_ROOT / "manifest.json"
)
SKILL_ROOT = ROOT / "tlgf"
DEFAULT_RESULTS_ROOT = BENCHMARK_ROOT / "results"
DEFAULT_REPO_CACHE = Path(tempfile.gettempdir()) / "tlgf-benchmark-cache"
DEFAULT_ENV_FILE = ROOT / ".env"
AGENTS = ("claude", "codex", "agy")
CONDITIONS = ("control", "tlgf")
AGY_EFFORT = "medium"
SAFE_MODEL_ENV = {
    "claude": "TLGF_BENCH_CLAUDE_MODEL",
    "codex": "TLGF_BENCH_CODEX_MODEL",
    "agy": "TLGF_BENCH_AGY_MODEL",
}
SENSITIVE_KEY = re.compile(r"(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)", re.IGNORECASE)
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
    "XDG_STATE_HOME",
    "__CF_USER_TEXT_ENCODING",
}
REPO_PATH = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"((?:(?:lib|test|examples)/[A-Za-z0-9_./%+-]+\.(?:js|json|md))|"
    r"(?:package\.json|Readme\.md|History\.md|LICENSE))"
)
PROCESS_NARRATION = re.compile(
    r"(?im)^\s*(?:now\s+)?(?:"
    r"let me\b|"
    r"i(?:'ll| will)\s+(?:check|look|inspect|read|search|open)\b|"
    r"i have everything i need\b|"
    r"here(?:'s| is) what i found\b"
    r")[^\n]*"
)
RESULT_PARSER_SCHEMA_VERSION = 4
# Phrases that the skill tells the agent to remove: importance announcements, canned
# transitions, decorative metaphors, praise, inflated verbs, and chatbot filler.
MANNERISM_PHRASES = (
    "it is important to note",
    "it's important to note",
    "it is worth noting",
    "it's worth noting",
    "worth noting",
    "please note",
    "note that",
    "in order to",
    "make use of",
    "is able to",
    "utilize",
    "leverage",
    "delve",
    "crucial",
    "robust",
    "seamless",
    "comprehensive",
    "here's the thing",
    "let's unpack",
    "let's dive",
    "dive into",
    "what matters is",
    "as we'll see",
    "as you can see",
    "the key takeaway",
    "at its core",
    "in essence",
    "essentially",
    "simply put",
    "connective tissue",
    "load-bearing",
    "rough edges",
    "plumbing",
    "magic",
    "great question",
    "good question",
    "i hope this helps",
    "feel free to",
    "let me know if",
    "happy to help",
    "not just",
    "game-changer",
)
MANNERISM_PATTERN = re.compile(
    r"(?i)(?<![\w-])(?:" + "|".join(re.escape(phrase) for phrase in MANNERISM_PHRASES) + r")(?![\w-])"
)
LONG_SENTENCE_WORDS = 26


class BenchmarkError(RuntimeError):
    """A benchmark configuration or execution error."""


def fail(message: str) -> None:
    raise BenchmarkError(message)


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        fail(f"Expected a JSON object in {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def load_manifest() -> dict[str, Any]:
    manifest = read_json(MANIFEST_PATH)
    if manifest.get("schema_version") != 1:
        fail("Unsupported benchmark manifest schema")
    repository = manifest.get("repository")
    if isinstance(repository, dict):
        commit = repository.get("commit")
        if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
            fail("The manifest repository commit must be a full SHA-1")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        fail("The manifest must define at least one case")
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
            fail(f"Benchmark case {case_id} has no prompt")
        for key in ("required_paths", "required_term_groups", "required_commands", "review_criteria"):
            if not isinstance(case.get(key), list):
                fail(f"Benchmark case {case_id} has invalid {key}")
        for key in ("forbidden_terms", "forbidden_commands"):
            value = case.get(key, [])
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                fail(f"Benchmark case {case_id} has invalid {key}")
        max_response_words = case.get("max_response_words")
        if (
            not isinstance(max_response_words, int)
            or isinstance(max_response_words, bool)
            or max_response_words <= 0
        ):
            fail(f"Benchmark case {case_id} has invalid max_response_words")
    return manifest


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse simple KEY=VALUE lines without interpolation or command execution."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, raw_value = line.partition("=")
        key = key.strip()
        if not separator or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) is None:
            fail(f"Invalid environment assignment in {path}:{line_number}")
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def effective_environment(env_file: Path) -> tuple[dict[str, str], dict[str, str]]:
    file_values = parse_env_file(env_file)
    environment = os.environ.copy()
    for key, value in file_values.items():
        environment.setdefault(key, value)
    environment["NO_COLOR"] = "1"
    return environment, file_values


def agent_environment(
    agent: str,
    environment: dict[str, str],
    model_env_keys: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return the minimum environment required by an agent CLI."""
    safe = {
        key: value
        for key, value in environment.items()
        if key in INHERITED_ENV_KEYS or key.startswith("LC_")
    }
    safe["NO_COLOR"] = "1"
    model_key = (model_env_keys or SAFE_MODEL_ENV).get(agent)
    if model_key and environment.get(model_key):
        safe[model_key] = environment[model_key]
    return safe


def atomic_write(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextlib.contextmanager
def temporary_agy_sandbox_settings(enabled: bool) -> Iterable[None]:
    """Enable Agy's documented autonomous sandbox and restore exact settings."""
    if not enabled:
        yield
        return
    path = Path.home() / ".gemini" / "antigravity-cli" / "settings.json"
    if path.is_symlink() or not path.is_file():
        fail(f"Agy settings must be a regular file: {path}")
    original = path.read_bytes()
    try:
        settings = json.loads(original)
    except json.JSONDecodeError as error:
        fail(f"Agy settings aren't valid JSON: {error}")
    if not isinstance(settings, dict):
        fail("Agy settings must contain a JSON object")
    benchmark_settings = dict(settings)
    benchmark_settings["toolPermission"] = "proceed-in-sandbox"
    benchmark_settings["enableTerminalSandbox"] = True
    benchmark_settings["allowNonWorkspaceAccess"] = False
    mode = path.stat().st_mode & 0o777
    updated = (json.dumps(benchmark_settings, ensure_ascii=False, indent=2) + "\n").encode()
    atomic_write(path, updated, mode)
    try:
        yield
    finally:
        atomic_write(path, original, mode)


def configured_agy_model() -> str | None:
    """Resolve the configured Gemini family to the benchmark effort variant."""
    path = Path.home() / ".gemini" / "antigravity-cli" / "settings.json"
    if not path.is_file():
        return None
    try:
        settings = read_json(path)
    except (BenchmarkError, json.JSONDecodeError, OSError):
        return None
    model = settings.get("model")
    if not isinstance(model, str):
        return None
    match = re.fullmatch(r"Gemini (\d+\.\d+) (Flash|Pro) \((?:Low|Medium|High)\)", model)
    if match is None:
        return None
    version, family = match.groups()
    return f"gemini-{version}-{family.lower()}-{AGY_EFFORT}"


def configured_codex_model(config_path: Path | None = None) -> str | None:
    """The default Codex model from ~/.codex/config.toml, which the CLI doesn't report."""
    path = config_path or Path.home() / ".codex" / "config.toml"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r'(?m)^\s*model\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else None


def reasoning_effort(agent: str, requested_model: str | None) -> str | None:
    """The reasoning effort each agent runs with, as recorded for the report."""
    if agent in ("claude", "codex"):
        return "medium"
    if agent == "agy":
        match = re.search(r"-(low|medium|high)$", requested_model or "")
        return match.group(1) if match else AGY_EFFORT
    return None


def redact(text: str, file_values: dict[str, str]) -> str:
    redacted = text
    for key, value in file_values.items():
        if value and len(value) >= 4 and (SENSITIVE_KEY.search(key) or key.endswith("BASE_URL")):
            redacted = redacted.replace(value, f"<{key}:redacted>")
    return redacted


WORKSPACE_CONDITION_SEGMENT = re.compile(r"(workspaces/[^/\s\"'`()<>]+/)[^/\s\"'`()<>]+/")


def neutralize_workspace_paths(text: str) -> str:
    """Replace the condition directory in workspace paths with CONDITION.

    Agents cite files by absolute path, and the path names the condition
    (workspaces/<agent>/<condition>/...). A blinded reader or judge must see
    the same neutral path in both answers of a pair.
    """
    return WORKSPACE_CONDITION_SEGMENT.sub(r"\1CONDITION/", text)


KNOWN_EXECUTABLES: dict[str, str] = {}
EXECUTABLE_RETRIES = 8
EXECUTABLE_RETRY_SECONDS = 15


def locate_executable(agent: str) -> str | None:
    names = {
        "claude": ("claude",),
        "codex": ("codex",),
        "agy": ("agy",),
    }[agent]
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return resolved
        candidate = Path(name)
        if candidate.is_absolute() and candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def find_executable(agent: str, retry: bool = True) -> str | None:
    """Find an agent CLI; wait out a brief absence such as an auto-update."""
    resolved = locate_executable(agent)
    if resolved:
        KNOWN_EXECUTABLES[agent] = resolved
        return resolved
    if not retry or agent not in KNOWN_EXECUTABLES:
        return None
    for _ in range(EXECUTABLE_RETRIES):
        time.sleep(EXECUTABLE_RETRY_SECONDS)
        resolved = locate_executable(agent)
        if resolved:
            KNOWN_EXECUTABLES[agent] = resolved
            return resolved
        cached = KNOWN_EXECUTABLES[agent]
        if Path(cached).exists():
            return cached
    return None


def version_command(agent: str, executable: str) -> list[str]:
    return [executable, "--version"]


def command_version(agent: str, executable: str) -> str | None:
    try:
        completed = subprocess.run(
            version_command(agent, executable),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = (completed.stdout or completed.stderr).strip()
    return output.splitlines()[-1] if output else None


def codex_global_skill_paths(skill_name: str = "tlgf") -> list[Path]:
    candidates = [Path.home() / ".agents" / "skills" / skill_name / "SKILL.md"]
    configured_home = os.environ.get("CODEX_HOME")
    if configured_home:
        candidates.append(
            Path(configured_home).expanduser() / "skills" / skill_name / "SKILL.md"
        )
    else:
        candidates.append(Path.home() / ".codex" / "skills" / skill_name / "SKILL.md")
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.absolute())
        if (path.exists() or path.is_symlink()) and key not in seen:
            unique.append(path.absolute())
            seen.add(key)
    return unique


def codex_all_global_skill_paths() -> list[Path]:
    roots = [Path.home() / ".agents" / "skills"]
    configured_home = os.environ.get("CODEX_HOME")
    roots.append(
        Path(configured_home).expanduser() / "skills"
        if configured_home
        else Path.home() / ".codex" / "skills"
    )
    candidates: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for child in root.iterdir():
            direct = child / "SKILL.md"
            if direct.exists() or direct.is_symlink():
                candidates.append(direct)
            if child.name.startswith(".") and child.is_dir():
                candidates.extend(child.glob("*/SKILL.md"))
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.absolute())
        if key not in seen:
            unique.append(path.absolute())
            seen.add(key)
    return sorted(unique, key=lambda path: str(path))


def doctor(env_file: Path) -> int:
    environment, file_values = effective_environment(env_file)
    agents: dict[str, Any] = {}
    for agent in AGENTS:
        executable = find_executable(agent)
        agents[agent] = {
            "available": executable is not None,
            "executable": executable,
            "version": command_version(agent, executable) if executable else None,
        }
    result = {
        "benchmark": load_manifest()["id"],
        "git_available": shutil.which("git") is not None,
        "agents": agents,
        "codex_global_tlgf_paths": [str(path) for path in codex_global_skill_paths("tlgf")],
        "env_file": str(env_file),
        "env_file_present": env_file.is_file(),
        "secret_values_logged": False,
        "env_keys_loaded": sorted(file_values),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def run_checked(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        fail(f"Command failed ({completed.returncode}): {' '.join(command)}\n{detail}")
    return completed


def git_has_commit(cache: Path, commit: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(cache), "cat-file", "-e", f"{commit}^{{commit}}"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def ensure_repository(cache: Path, manifest: dict[str, Any]) -> Path:
    if shutil.which("git") is None:
        fail("git is required to prepare the repository snapshot")
    repository = manifest["repository"]
    commit = repository["commit"]
    if (cache / ".git").is_dir():
        if not git_has_commit(cache, commit):
            run_checked(["git", "-C", str(cache), "fetch", "--depth", "1", "origin", commit])
    else:
        if cache.exists() and any(cache.iterdir()):
            fail(f"Repository cache exists but isn't a Git checkout: {cache}")
        cache.parent.mkdir(parents=True, exist_ok=True)
        run_checked(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                repository["url"],
                str(cache),
            ]
        )
        if not git_has_commit(cache, commit):
            run_checked(["git", "-C", str(cache), "fetch", "--depth", "1", "origin", commit])
    if not git_has_commit(cache, commit):
        fail(f"Pinned commit {commit} is unavailable in {cache}")
    resolved = run_checked(["git", "-C", str(cache), "rev-parse", commit]).stdout.strip()
    if resolved != commit:
        fail(f"Repository resolved {commit} to unexpected commit {resolved}")
    return cache


def safe_extract_tar(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with tarfile.open(archive, "r") as handle:
        for member in handle.getmembers():
            target = (destination / member.name).resolve()
            if target != root and root not in target.parents:
                fail(f"Unsafe path in repository archive: {member.name}")
            if member.issym() or member.islnk():
                link_target = (target.parent / member.linkname).resolve()
                if link_target != root and root not in link_target.parents:
                    fail(f"Unsafe link in repository archive: {member.name}")
        try:
            handle.extractall(destination, filter="data")
        except TypeError:
            handle.extractall(destination)


def export_repository(cache: Path, commit: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    archive = destination.parent / f"{destination.name}.tar"
    try:
        run_checked(
            ["git", "-C", str(cache), "archive", "--format=tar", "--output", str(archive), commit]
        )
        safe_extract_tar(archive, destination)
    finally:
        archive.unlink(missing_ok=True)


def repository_digest(repository: Path, ignore: tuple[str, ...] = ()) -> str:
    """Digest every file except .git and the relative paths in ``ignore``."""
    digest = hashlib.sha256()
    for path in sorted(repository.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(repository).as_posix()
        if relative == ".git" or relative.startswith(".git/") or relative in ignore:
            continue
        digest.update(relative.encode())
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(b"link\0")
            digest.update(os.readlink(path).encode())
        elif path.is_file():
            digest.update(b"file\0")
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        elif path.is_dir():
            digest.update(b"dir\0")
        digest.update(b"\0")
    return digest.hexdigest()


def install_treatment_skill(agent: str, repository: Path, skill_name: str = "tlgf") -> Path:
    destinations = {
        "claude": repository / ".claude" / "skills" / skill_name,
        "codex": repository / ".agents" / "skills" / skill_name,
        "agy": repository / ".agents" / "skills" / skill_name,
    }
    destination = destinations[agent]
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SKILL_ROOT, destination)
    return destination


install_tlgf = install_treatment_skill
install_tlgd = install_treatment_skill


def create_workspaces(
    run_root: Path,
    agents: Iterable[str],
    cache: Path,
    manifest: dict[str, Any],
    environment: dict[str, str],
) -> dict[tuple[str, str], Path]:
    workspaces: dict[tuple[str, str], Path] = {}
    commit = manifest["repository"]["commit"]
    for agent in agents:
        for condition in CONDITIONS:
            repository = run_root / "workspaces" / agent / condition / "repository"
            export_repository(cache, commit, repository)
            # A workspace-local repository makes every CLI treat the snapshot as
            # its own project, so memory, rules, and settings from an enclosing
            # checkout never reach the agent.
            run_checked(["git", "-C", str(repository), "init", "-q", "-b", "benchmark-snapshot"])
            if condition in ("tlgf", "tlgd"):
                install_treatment_skill(agent, repository)
            workspaces[(agent, condition)] = repository
    return workspaces


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def codex_skill_override(paths: Iterable[Path]) -> str | None:
    entries = [f"{{ path = {toml_string(str(path))}, enabled = false }}" for path in paths]
    return f"skills.config=[{', '.join(entries)}]" if entries else None


def build_command(
    agent: str,
    condition: str,
    repository: Path,
    prompt: str,
    environment: dict[str, str],
    *,
    skill_name: str = "tlgf",
    model_env_keys: dict[str, str] | None = None,
    disable_other_codex_skills: bool = False,
) -> tuple[list[str], str | None]:
    executable = find_executable(agent)
    if executable is None:
        fail(f"Agent CLI isn't available: {agent}")
    requested_model = environment.get((model_env_keys or SAFE_MODEL_ENV).get(agent, "")) or None
    if agent == "claude":
        command = [
            executable,
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--no-session-persistence",
            "--permission-mode",
            "dontAsk",
            "--no-chrome",
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
            "--setting-sources",
            "project",
            "--effort",
            "medium",
            "--tools",
            "Read,Glob,Grep,Skill",
        ]
        if condition == "control":
            command.append("--disable-slash-commands")
        if requested_model:
            command.extend(["--model", requested_model])
        command.extend(["--", prompt])
        return command, requested_model
    if agent == "codex":
        command = [
            executable,
            "-a",
            "never",
            "-s",
            "read-only",
            "-C",
            str(repository),
            "-c",
            'model_reasoning_effort="medium"',
        ]
        disabled_skills = (
            codex_all_global_skill_paths()
            if disable_other_codex_skills
            else codex_global_skill_paths(skill_name)
        )
        override = codex_skill_override(disabled_skills)
        if override:
            command.extend(["-c", override])
        if requested_model:
            command.extend(["--model", requested_model])
        else:
            requested_model = configured_codex_model()
        command.extend(
            [
                "exec",
                "--json",
                "--ephemeral",
                "--skip-git-repo-check",
                "--ignore-user-config",
                "--ignore-rules",
                prompt,
            ]
        )
        return command, requested_model
    if agent == "agy":
        command = [
            executable,
            "--output-format",
            "stream-json",
            "--sandbox",
            "--new-project",
            "--print-timeout",
            "5m",
        ]
        if condition == "control":
            command.append("--disable-slash-commands")
        if requested_model:
            command.extend(["--model", requested_model])
        else:
            command.extend(["--effort", AGY_EFFORT])
        command.extend(["--print", prompt])
        return command, requested_model
    fail(f"Unsupported agent: {agent}")


def json_events(stdout: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    stripped = stdout.strip()
    if not stripped:
        return events
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        value = None
    if isinstance(value, dict):
        return [value]
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def first_number(mapping: dict[str, Any], keys: Iterable[str]) -> int | float | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
    return None


def normalize_usage(mapping: dict[str, Any]) -> dict[str, int | float | None]:
    cache = mapping.get("cache") if isinstance(mapping.get("cache"), dict) else {}
    usage: dict[str, int | float | None] = {
        "input_tokens": first_number(mapping, ("input_tokens", "inputTokens", "input")),
        "cached_input_tokens": first_number(
            mapping, ("cached_input_tokens", "cache_read_input_tokens", "cacheReadInputTokens")
        ),
        "cache_creation_input_tokens": first_number(
            mapping, ("cache_creation_input_tokens", "cache_write_input_tokens", "cacheCreationInputTokens")
        ),
        "output_tokens": first_number(mapping, ("output_tokens", "outputTokens", "output")),
        "reasoning_tokens": first_number(mapping, ("reasoning_tokens", "reasoningTokens", "reasoning")),
        "total_tokens": first_number(mapping, ("total_tokens", "totalTokens", "total")),
        "cost_usd": first_number(mapping, ("cost_usd", "total_cost_usd", "cost")),
    }
    if usage["cached_input_tokens"] is None and isinstance(cache, dict):
        usage["cached_input_tokens"] = first_number(cache, ("read", "input", "read_tokens"))
    if usage["cache_creation_input_tokens"] is None and isinstance(cache, dict):
        usage["cache_creation_input_tokens"] = first_number(cache, ("write", "creation", "write_tokens"))
    if usage["total_tokens"] is None:
        input_tokens = usage["input_tokens"]
        output_tokens = usage["output_tokens"]
        if isinstance(input_tokens, (int, float)) and isinstance(output_tokens, (int, float)):
            usage["total_tokens"] = input_tokens + output_tokens
    return usage


def add_usage(target: dict[str, int | float | None], source: dict[str, int | float | None]) -> None:
    for key, value in source.items():
        if value is None:
            continue
        current = target.get(key)
        target[key] = value if current is None else current + value


def iter_objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from iter_objects(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from iter_objects(nested)


def response_word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text, re.UNICODE))


MARKDOWN_INLINE_LINK = re.compile(
    r"!?\[([^\]\n]+)\]\((?:\\.|[^()\\]|\([^()]*\))*\)"
)
MARKDOWN_REFERENCE_LINK = re.compile(r"!?\[([^\]\n]+)\]\[[^\]\n]*\]")
MARKDOWN_REFERENCE_DEFINITION = re.compile(r"^\s{0,3}\[[^\]\n]+\]:\s+\S+.*$")
MARKDOWN_CODE_SPAN = re.compile(r"(`+)(.*?)(\1)")
MARKDOWN_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


def reader_visible_markdown(text: str) -> str:
    """Remove non-rendered Markdown link destinations before counting words."""
    rendered_lines: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    for line in text.splitlines():
        fence = MARKDOWN_FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if fence_character is None:
                fence_character = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_character and len(marker) >= fence_length:
                fence_character = None
                fence_length = 0
            rendered_lines.append(line)
            continue
        if fence_character is not None:
            rendered_lines.append(line)
            continue
        if MARKDOWN_REFERENCE_DEFINITION.match(line):
            continue

        code_spans: list[tuple[str, str]] = []

        def protect_code_span(match: re.Match[str]) -> str:
            placeholder = f"\uFFF0CODE{len(code_spans)}\uFFF1"
            code_spans.append((placeholder, match.group(0)))
            return placeholder

        rendered = MARKDOWN_CODE_SPAN.sub(protect_code_span, line)
        rendered = MARKDOWN_INLINE_LINK.sub(r"\1", rendered)
        rendered = MARKDOWN_REFERENCE_LINK.sub(r"\1", rendered)
        for placeholder, code_span in code_spans:
            rendered = rendered.replace(placeholder, code_span)
        rendered_lines.append(rendered)
    return "\n".join(rendered_lines)


def prose_only(text: str) -> str:
    """Drop fenced and inline code so style metrics describe prose."""
    without_fences = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    return re.sub(r"`[^`\n]*`", " ", without_fences)


def style_metrics(text: str) -> dict[str, Any]:
    """Deterministic prose-style signals. They inform review; they never gate."""
    prose = prose_only(text)
    mannerisms = [match.group(0).lower() for match in MANNERISM_PATTERN.finditer(prose)]
    sentences: list[int] = []
    for block in re.split(r"\n\s*\n", prose):
        for line in block.splitlines():
            stripped = re.sub(r"^\s*(?:[-*+]|\d+[.)]|#+)\s+", "", line).strip()
            if not stripped:
                continue
            for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9*_`\"(])", stripped):
                words = len(re.findall(r"\S+", sentence))
                if words:
                    sentences.append(words)
    word_total = sum(sentences)
    long_sentences = sum(1 for words in sentences if words > LONG_SENTENCE_WORDS)
    return {
        "mannerism_count": len(mannerisms),
        "mannerisms": mannerisms,
        "mannerisms_per_100_words": round(100 * len(mannerisms) / word_total, 2) if word_total else 0.0,
        "sentence_count": len(sentences),
        "mean_sentence_words": round(word_total / len(sentences), 1) if sentences else 0.0,
        "long_sentence_share": round(long_sentences / len(sentences), 2) if sentences else 0.0,
        "heading_count": len(re.findall(r"(?m)^\s*#{1,6}\s+\S", text)),
        "bullet_count": len(re.findall(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+\S", text)),
        "bold_span_count": len(re.findall(r"\*\*[^*\n]+\*\*", text)),
    }


def reader_response_word_count(text: str) -> int:
    """Count words a reader sees after ordinary Markdown rendering."""
    return response_word_count(reader_visible_markdown(text))


def extract_response(agent: str, events: list[dict[str, Any]]) -> str:
    if agent == "claude":
        for event in reversed(events):
            if event.get("type") == "result" and isinstance(event.get("result"), str):
                return event["result"].strip()
    if agent == "agy":
        for event in reversed(events):
            result = event.get("result")
            if event.get("event") == "result" and isinstance(result, dict):
                response = result.get("response")
                if isinstance(response, str):
                    return response.strip()
    if agent == "codex":
        messages: list[str] = []
        for event in events:
            item = event.get("item")
            if event.get("type") == "item.completed" and isinstance(item, dict):
                if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                    messages.append(item["text"])
        if messages:
            return messages[-1].strip()
    for event in reversed(events):
        for key in ("result", "response", "text", "output"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def unwrap_claude_event(event: dict[str, Any]) -> dict[str, Any]:
    ev = event
    while isinstance(ev, dict) and ev.get("type") == "stream_event" and isinstance(ev.get("event"), dict):
        ev = ev["event"]
    return ev if isinstance(ev, dict) else event


def is_response_accounted_for(messages: list[str], resp: str) -> bool:
    resp = resp.strip()
    if not resp or not messages:
        return False
    if any(m.strip() == resp for m in messages):
        return True
    combined = ""
    for m in reversed(messages):
        combined = f"{m.strip()}\n\n{combined}" if combined else m.strip()
        if combined == resp:
            return True
        if len(combined) > len(resp):
            break
    return False


def extract_visible_text(agent: str, events: list[dict[str, Any]], response: str) -> str:
    messages: list[str] = []
    if agent == "codex":
        for event in events:
            item = event.get("item")
            if event.get("type") == "item.completed" and isinstance(item, dict):
                if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                    text = item["text"].strip()
                    if text:
                        messages.append(text)
    elif agent == "claude":
        for raw_event in events:
            ev = unwrap_claude_event(raw_event)
            etype = ev.get("type")
            if etype in ("user", "system", "result"):
                continue
            msg = ev.get("message")
            if isinstance(msg, dict):
                if msg.get("role") == "user":
                    continue
                content = msg.get("content")
                text_blocks: list[str] = []
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            t = block.get("text")
                            if isinstance(t, str) and t.strip():
                                text_blocks.append(t.strip())
                elif isinstance(content, str) and content.strip():
                    text_blocks.append(content.strip())
                if text_blocks:
                    messages.append("\n\n".join(text_blocks))
            elif etype == "text" and isinstance(ev.get("text"), str):
                if ev.get("role") != "user":
                    t = ev["text"].strip()
                    if t:
                        messages.append(t)
    elif agent == "agy":
        for event in events:
            step_update = event.get("step_update")
            if isinstance(step_update, dict):
                t = step_update.get("text") or step_update.get("message")
                if isinstance(t, str) and t.strip():
                    messages.append(t.strip())
    if response and response.strip():
        if not is_response_accounted_for(messages, response):
            messages.append(response.strip())
    return "\n\n".join(messages) if messages else response


def extract_final_step_usage(
    agent: str, events: list[dict[str, Any]]
) -> dict[str, int | float | None]:
    if agent == "codex":
        # Find the final agent_message item in the events
        last_agent_item: dict[str, Any] | None = None
        last_agent_event: dict[str, Any] | None = None
        for event in reversed(events):
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                last_agent_item = item
                last_agent_event = event
                break

        if last_agent_item is not None:
            # If the final agent_message explicitly contains its own usage, use it
            if isinstance(last_agent_item.get("usage"), dict):
                return normalize_usage(last_agent_item["usage"])
            if (
                last_agent_event is not None
                and last_agent_event.get("type") == "item.completed"
                and isinstance(last_agent_event.get("usage"), dict)
            ):
                return normalize_usage(last_agent_event["usage"])

        # Check the last turn's events to see if intermediate steps occurred
        last_turn_events: list[dict[str, Any]] = []
        for event in reversed(events):
            if event.get("type") == "turn.completed" and last_turn_events:
                break
            last_turn_events.append(event)
        last_turn_events.reverse()

        has_intermediate_steps = False
        agent_message_count = 0
        for event in last_turn_events:
            etype = event.get("type", "")
            item = event.get("item")
            if isinstance(item, dict):
                itype = item.get("type", "")
                if itype == "agent_message":
                    agent_message_count += 1
                elif itype:
                    has_intermediate_steps = True
            if etype in ("tool_call", "tool_result", "command_execution", "call"):
                has_intermediate_steps = True

        # If there were intermediate steps or multiple generation steps in the turn,
        # turn.completed.usage is cumulative across the entire turn, so final step usage is unavailable.
        if has_intermediate_steps or agent_message_count > 1 or last_agent_item is None:
            return normalize_usage({})

        for event in reversed(last_turn_events):
            if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
                return normalize_usage(event["usage"])

    elif agent == "claude":
        for idx in range(len(events) - 1, -1, -1):
            raw_event = events[idx]
            ev = unwrap_claude_event(raw_event)
            etype = ev.get("type")

            if etype in ("result", "turn.completed"):
                continue

            if etype == "assistant":
                msg = ev.get("message")
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    content = msg.get("content")
                    if msg.get("stop_reason") == "tool_use":
                        continue
                    if isinstance(content, list) and any(
                        isinstance(b, dict) and b.get("type") == "tool_use" for b in content
                    ):
                        continue
                    # Found the final assistant answer message
                    if isinstance(msg.get("usage"), dict):
                        return normalize_usage(msg["usage"])
                    # Final message has no usage -> do not fall back to earlier messages
                    return normalize_usage({})

            elif etype == "message_delta":
                delta = ev.get("delta")
                if isinstance(delta, dict) and delta.get("stop_reason") == "tool_use":
                    continue
                usage = ev.get("usage")
                norm = normalize_usage(usage if isinstance(usage, dict) else {})
                # Look backwards strictly within this same generation for message_start (to get input_tokens)
                for prev_idx in range(idx - 1, -1, -1):
                    pev = unwrap_claude_event(events[prev_idx])
                    ptype = pev.get("type")
                    if ptype in ("message_delta", "assistant"):
                        break
                    if ptype == "message_start":
                        pmsg = pev.get("message")
                        if isinstance(pmsg, dict) and isinstance(pmsg.get("usage"), dict):
                            if norm.get("input_tokens") is None:
                                norm["input_tokens"] = pmsg["usage"].get("input_tokens")
                        break
                return norm

            elif etype == "message":
                msg = ev.get("message") if isinstance(ev.get("message"), dict) else ev
                if isinstance(msg, dict):
                    if msg.get("role") == "user":
                        continue
                    if msg.get("stop_reason") == "tool_use":
                        continue
                    if isinstance(msg.get("usage"), dict):
                        return normalize_usage(msg["usage"])
                    # Final message has no usage -> do not fall back to earlier messages
                    return normalize_usage({})

    elif agent == "agy":
        for event in reversed(events):
            if event.get("event") in ("step_finish", "step_update"):
                info = event.get(event["event"])
                if isinstance(info, dict) and isinstance(info.get("usage"), dict):
                    return normalize_usage(info["usage"])
    return normalize_usage({})


def extract_finish_reason(agent: str, events: list[dict[str, Any]]) -> str | None:
    if agent == "claude":
        for raw_event in reversed(events):
            event = unwrap_claude_event(raw_event)
            if event.get("type") == "message_delta":
                delta = event.get("delta")
                if isinstance(delta, dict) and delta.get("stop_reason"):
                    return str(delta["stop_reason"])
            if event.get("type") == "assistant":
                msg = event.get("message")
                if isinstance(msg, dict) and msg.get("stop_reason"):
                    return str(msg["stop_reason"])
            if event.get("type") == "result":
                for key in ("stop_reason", "finish_reason"):
                    if event.get(key):
                        return str(event[key])
            msg = event.get("message")
            if isinstance(msg, dict) and msg.get("stop_reason"):
                return str(msg["stop_reason"])
    elif agent == "codex":
        for event in reversed(events):
            item = event.get("item")
            if isinstance(item, dict) and item.get("finish_reason"):
                return str(item["finish_reason"])
            if event.get("type") == "turn.completed":
                turn = event.get("turn")
                if isinstance(turn, dict) and turn.get("finish_reason"):
                    return str(turn["finish_reason"])
                if event.get("finish_reason"):
                    return str(event["finish_reason"])
    elif agent == "agy":
        for event in reversed(events):
            res = event.get("result")
            if isinstance(res, dict):
                for key in ("finish_reason", "stop_reason", "status"):
                    if res.get(key):
                        return str(res[key])
    for event in reversed(events):
        for key in ("finish_reason", "stop_reason"):
            if event.get(key):
                return str(event[key])
    return None


def extract_usage(agent: str, events: list[dict[str, Any]]) -> dict[str, int | float | None]:
    empty = normalize_usage({})
    if agent == "claude":
        for event in reversed(events):
            if event.get("type") == "result":
                mapping = event.get("usage")
                usage = normalize_usage(mapping if isinstance(mapping, dict) else {})
                cost = event.get("total_cost_usd")
                if isinstance(cost, (int, float)):
                    usage["cost_usd"] = cost
                return usage
    if agent == "agy":
        for event in reversed(events):
            result = event.get("result")
            if event.get("event") != "result" or not isinstance(result, dict):
                continue
            mapping = result.get("usage")
            usage = normalize_usage(mapping if isinstance(mapping, dict) else {})
            if isinstance(mapping, dict):
                if usage["cached_input_tokens"] is None:
                    usage["cached_input_tokens"] = first_number(mapping, ("cache_read_tokens",))
                if usage["reasoning_tokens"] is None:
                    usage["reasoning_tokens"] = first_number(mapping, ("thinking_tokens",))
            return usage
    if agent == "codex":
        for event in reversed(events):
            if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
                return normalize_usage(event["usage"])
    for event in reversed(events):
        usage = event.get("usage")
        if isinstance(usage, dict):
            return normalize_usage(usage)
    return empty


def extract_model(events: list[dict[str, Any]], requested_model: str | None) -> str | None:
    for event in reversed(events):
        model_usage = event.get("modelUsage")
        if isinstance(model_usage, dict) and model_usage:
            # Claude can report a small helper-model call alongside the model
            # that generated the answer. Select the model responsible for the
            # most output instead of relying on map insertion order.
            def output_tokens(item: tuple[str, Any]) -> float:
                details = item[1]
                if not isinstance(details, dict):
                    return -1
                value = details.get("outputTokens")
                return float(value) if isinstance(value, (int, float)) else -1

            return max(model_usage.items(), key=output_tokens)[0]
        value = event.get("model")
        if isinstance(value, str) and value:
            return value
        message = event.get("message")
        if isinstance(message, dict) and isinstance(message.get("model"), str):
            return message["model"]
        init = event.get("init")
        if isinstance(init, dict) and isinstance(init.get("model"), str):
            return init["model"]
    return requested_model


def extract_status(
    agent: str,
    events: list[dict[str, Any]],
    exit_code: int | None,
    timed_out: bool,
    response: str | None = None,
) -> str:
    if timed_out:
        return "TIMEOUT"
    if exit_code != 0:
        return "ERROR"
    if agent == "agy":
        for event in reversed(events):
            result = event.get("result")
            if event.get("event") == "result" and isinstance(result, dict):
                status = result.get("status")
                if isinstance(status, str) and status:
                    delivered = isinstance(result.get("response"), str) and result["response"].strip()
                    if status.upper() == "ERROR" and delivered:
                        # Agy reports ERROR when an intermediate tool call had
                        # invalid arguments, even though the final answer was
                        # delivered. Keep the answer; record the host error.
                        return "SUCCESS"
                    return status.upper()
    if response is not None and not response.strip():
        return "NO_FINAL_ANSWER"
    return "SUCCESS"


def extract_host_error(agent: str, events: list[dict[str, Any]]) -> str | None:
    """A host-reported error that didn't prevent a final answer."""
    if agent != "agy":
        return None
    for event in reversed(events):
        result = event.get("result")
        if event.get("event") == "result" and isinstance(result, dict):
            error = result.get("error")
            if isinstance(error, str) and error.strip():
                return " ".join(error.split())
            return None
    return None


def tool_objects(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for event in events:
        update = event.get("step_update")
        if (
            event.get("event") == "step_update"
            and isinstance(update, dict)
            and update.get("step_type") == "tool"
            and update.get("state") == "ACTIVE"
        ):
            tools.append(update)
            continue
        for value in iter_objects(event):
            value_type = str(value.get("type", "")).lower()
            if value_type in {"tool_use", "tool-call", "tool_call", "command_execution"}:
                tools.append(value)
            elif event.get("type") in {"item.started", "item.completed"} and value is event.get("item"):
                item_type = str(value.get("type", "")).lower()
                if item_type not in {"agent_message", "reasoning"}:
                    tools.append(value)
    return tools


def skill_activation_evidence(
    events: list[dict[str, Any]], skill_name: str = "tlgf"
) -> list[str]:
    evidence: list[str] = []
    skill_file = f"{skill_name}/skill.md"
    skill_path = f"skills/{skill_name}"
    for tool in tool_objects(events):
        serialized = json.dumps(tool, ensure_ascii=False, sort_keys=True).lower()
        tool_name = str(tool.get("name") or tool.get("tool") or tool.get("toolName") or "").lower()
        if skill_file in serialized or skill_path in serialized:
            evidence.append(f"read-{skill_name}-skill")
        elif tool_name == "skill" and re.search(rf'\b{re.escape(skill_name)}\b', serialized):
            evidence.append(f"skill-tool-{skill_name}")
    declaration_patterns = (
        rf"\b(?:use|using|apply|applying|activate|activating|follow|following|load|loading|read|reading)\b"
        rf".{{0,60}}\b{re.escape(skill_name)}\b.{{0,30}}\bskill\b",
        rf"\b{re.escape(skill_name)}\b.{{0,30}}\bskill\b.{{0,60}}"
        rf"\b(?:use|using|apply|applying|activate|activating|follow|following|load|loading|read|reading)\b",
    )
    for event in events:
        for value in iter_objects(event):
            if str(value.get("type", "")).lower() != "agent_message":
                continue
            message = value.get("text")
            if not isinstance(message, str):
                continue
            if any(re.search(pattern, message, re.IGNORECASE) for pattern in declaration_patterns):
                evidence.append(f"declared-{skill_name}-skill")
    return sorted(set(evidence))


def mutation_tool_evidence(events: list[dict[str, Any]]) -> list[str]:
    mutating_names = {
        "apply_patch",
        "create_file",
        "edit",
        "multi_replace_file_content",
        "notebook_edit",
        "replace_file_content",
        "sed_file",
        "write",
        "write_file",
        "write_to_file",
    }
    evidence: list[str] = []
    for tool in tool_objects(events):
        name = str(
            tool.get("name")
            or tool.get("tool")
            or tool.get("toolName")
            or tool.get("tool_name")
            or tool.get("type")
            or ""
        ).lower()
        if name in mutating_names:
            evidence.append(name)
    return sorted(set(evidence))


def extract_paths(response: str) -> list[str]:
    return sorted(set(match.group(1).rstrip(".,:;)") for match in REPO_PATH.finditer(response)))


def evaluate_response(
    case: dict[str, Any],
    condition: str,
    response: str,
    repository: Path,
    activation_evidence: list[str],
    execution_succeeded: bool = True,
    workspace_unchanged: bool = True,
    visible_text: str | None = None,
) -> dict[str, Any]:
    visible_text = response if visible_text is None else visible_text
    response_lower = response.lower()
    normalized_response = re.sub(r"[`*_]", "", response_lower)
    required_paths = {
        path: path.lower() in response_lower for path in case.get("required_paths", [])
    }
    term_groups: list[dict[str, Any]] = []
    for group in case.get("required_term_groups", []):
        matched = [
            term
            for term in group
            if re.sub(r"[`*_]", "", term.lower()) in normalized_response
        ]
        term_groups.append({"terms": group, "matched": matched, "passed": bool(matched)})
    commands = {
        command: command in response for command in case.get("required_commands", [])
    }
    forbidden_terms = {
        term: re.sub(r"[`*_]", "", term.lower()) in normalized_response
        for term in case.get("forbidden_terms", [])
    }
    forbidden_commands = {
        command: command in response for command in case.get("forbidden_commands", [])
    }
    word_count = reader_response_word_count(response)
    max_response_words = case.get("max_response_words")
    word_limit_passed = not isinstance(max_response_words, int) or word_count <= max_response_words
    narration_matches = [match.group(0).strip() for match in PROCESS_NARRATION.finditer(visible_text)]
    cited_paths = extract_paths(response)
    invalid_paths = [path for path in cited_paths if not (repository / path).is_file()]
    expected_activation = condition in ("tlgf", "tlgd")
    observed_activation = bool(activation_evidence)
    checks = {
        "execution_succeeded": execution_succeeded,
        "workspace_unchanged": workspace_unchanged,
        "nonempty": bool(response.strip()),
        "required_paths": all(required_paths.values()),
        "required_term_groups": all(group["passed"] for group in term_groups),
        "required_commands": all(commands.values()),
        "forbidden_terms": not any(forbidden_terms.values()),
        "forbidden_commands": not any(forbidden_commands.values()),
        "response_word_limit": word_limit_passed,
        "no_process_narration": not narration_matches,
        "cited_paths_exist": not invalid_paths,
        "skill_activation": observed_activation == expected_activation,
    }
    budget_check_names = {"response_word_limit"}
    quality_checks = {name: passed for name, passed in checks.items() if name not in budget_check_names}
    budget_checks = {name: passed for name, passed in checks.items() if name in budget_check_names}
    return {
        "passed": all(quality_checks.values()),
        "quality_passed": all(quality_checks.values()),
        "budget_passed": all(budget_checks.values()),
        "all_checks_passed": all(checks.values()),
        "checks": checks,
        "quality_checks": quality_checks,
        "budget_checks": budget_checks,
        "style": style_metrics(response),
        "required_paths": required_paths,
        "term_groups": term_groups,
        "required_commands": commands,
        "forbidden_terms": forbidden_terms,
        "forbidden_commands": forbidden_commands,
        "response_words": word_count,
        "markdown_source_words": response_word_count(response),
        "max_response_words": max_response_words,
        "process_narration": narration_matches,
        "cited_paths": cited_paths,
        "invalid_paths": invalid_paths,
        "activation_expected": expected_activation,
        "activation_observed": observed_activation,
        "activation_evidence": activation_evidence,
    }


def derive_attempt(
    agent: str,
    record: dict[str, Any],
    requested_model: str | None,
    skill_name: str = "tlgf",
) -> dict[str, Any]:
    """Derive one attempt's answer, status, and metrics from its saved trace."""
    stdout = str(record.get("raw_stdout") or "")
    events = json_events(stdout)
    response = extract_response(agent, events)
    visible_text = extract_visible_text(agent, events, response)
    exit_code = record.get("exit_code") if isinstance(record.get("exit_code"), int) else None
    timed_out = bool(record.get("timed_out"))
    return {
        "attempt_number": int(record.get("attempt_number") or 1),
        "agent_status": extract_status(
            agent, events, exit_code, timed_out, response
        ),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_seconds": record.get("duration_seconds"),
        "response": response,
        "response_words": reader_response_word_count(response),
        "markdown_source_words": response_word_count(response),
        "response_characters": len(response),
        "visible_text": visible_text,
        "visible_text_words": reader_response_word_count(visible_text),
        "visible_text_source_words": response_word_count(visible_text),
        "usage": extract_usage(agent, events),
        "final_step_usage": extract_final_step_usage(agent, events),
        "finish_reason": "host-error" if extract_host_error(agent, events) else extract_finish_reason(agent, events),
        "host_error": extract_host_error(agent, events),
        "runtime_model": extract_model(events, requested_model),
        "tool_call_count": len(tool_objects(events)),
        "activation_evidence": skill_activation_evidence(events, skill_name),
        "mutation_evidence": mutation_tool_evidence(events),
        "raw_stdout": stdout,
        "raw_stderr": str(record.get("raw_stderr") or ""),
    }


def aggregate_attempt_usage(attempts: list[dict[str, Any]]) -> dict[str, int | float | None]:
    total = normalize_usage({})
    for attempt in attempts:
        usage = attempt.get("usage")
        if isinstance(usage, dict):
            add_usage(total, usage)
    return total


def should_retry_incomplete_answer(
    status: str, response: str, attempt_number: int, max_attempts: int
) -> bool:
    return (
        attempt_number < max_attempts
        and (
            status == "TRUNCATED"
            or not response.strip()
        )
    )


def regrade_result(
    result: dict[str, Any], case: dict[str, Any], repository: Path
) -> dict[str, Any]:
    """Rebuild all parser- and grader-derived fields from a saved trace."""
    agent = str(result.get("agent") or "")
    condition = str(result.get("condition") or "")
    requested_model = (
        result.get("requested_model")
        if isinstance(result.get("requested_model"), str)
        else None
    )
    stored_attempts = result.get("attempts")
    if isinstance(stored_attempts, list) and stored_attempts:
        attempts = [
            derive_attempt(agent, attempt, requested_model)
            for attempt in stored_attempts
            if isinstance(attempt, dict)
        ]
    else:
        attempts = [derive_attempt(agent, result, requested_model)]
    if not attempts:
        fail("A result must contain at least one execution attempt")
    selected = attempts[-1]
    response = selected["response"]
    visible_text = selected["visible_text"]
    status = selected["agent_status"]
    if "workspace_mutated" in result:
        workspace_unchanged = not bool(result["workspace_mutated"])
        integrity_method = str(result.get("workspace_integrity_method") or "digest")
    else:
        workspace_unchanged = not any(
            attempt.get("mutation_evidence") for attempt in attempts
        )
        integrity_method = "tool-trace"

    duration_seconds = round(
        sum(
            float(attempt["duration_seconds"])
            for attempt in attempts
            if isinstance(attempt.get("duration_seconds"), (int, float))
        ),
        3,
    )

    result.update(
        {
            "parser_schema_version": RESULT_PARSER_SCHEMA_VERSION,
            "agent_status": status,
            "runtime_model": selected["runtime_model"],
            "exit_code": selected["exit_code"],
            "timed_out": selected["timed_out"],
            "duration_seconds": duration_seconds,
            "selected_attempt_duration_seconds": selected["duration_seconds"],
            "response": response,
            "response_words": reader_response_word_count(response),
            "markdown_source_words": response_word_count(response),
            "response_characters": len(response),
            "visible_text": visible_text,
            "visible_text_words": reader_response_word_count(visible_text),
            "visible_text_source_words": response_word_count(visible_text),
            "usage": aggregate_attempt_usage(attempts),
            "selected_attempt_usage": selected["usage"],
            "final_step_usage": selected["final_step_usage"],
            "finish_reason": selected["finish_reason"],
            "tool_call_count": sum(int(attempt["tool_call_count"]) for attempt in attempts),
            "selected_attempt_tool_call_count": selected["tool_call_count"],
            "attempt_count": len(attempts),
            "retry_count": len(attempts) - 1,
            "attempt_statuses": [attempt["agent_status"] for attempt in attempts],
            "attempts": attempts,
            "raw_stdout": selected["raw_stdout"],
            "raw_stderr": selected["raw_stderr"],
            "workspace_mutated": not workspace_unchanged,
            "workspace_integrity_method": integrity_method,
            "evaluation": evaluate_response(
                case,
                condition,
                response,
                repository,
                selected["activation_evidence"],
                execution_succeeded=status == "SUCCESS",
                workspace_unchanged=workspace_unchanged,
                visible_text=visible_text,
            ),
        }
    )
    return result


def execute(
    command: list[str],
    cwd: Path,
    environment: dict[str, str],
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "exit_code": completed.returncode,
            "timed_out": False,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "duration_seconds": round(time.monotonic() - started, 3),
        }
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else (error.stdout or "")
        stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else (error.stderr or "")
        return {
            "exit_code": None,
            "timed_out": True,
            "stdout": stdout,
            "stderr": stderr,
            "duration_seconds": round(time.monotonic() - started, 3),
        }


def stable_condition_order(seed: int, agent: str, case_id: str, repetition: int) -> list[str]:
    material = f"{seed}:{agent}:{case_id}:{repetition}".encode()
    derived = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    order = list(CONDITIONS)
    random.Random(derived).shuffle(order)
    return order


def result_filename(agent: str, case_id: str, condition: str, repetition: int) -> str:
    return f"{agent}__{case_id}__{condition}__r{repetition}.json"


def select_cases(manifest: dict[str, Any], requested: list[str] | None) -> list[dict[str, Any]]:
    cases = manifest["cases"]
    if not requested:
        return cases
    by_id = {case["id"]: case for case in cases}
    unknown = [case_id for case_id in requested if case_id not in by_id]
    if unknown:
        fail(f"Unknown benchmark cases: {', '.join(unknown)}")
    return [by_id[case_id] for case_id in requested]


def safe_command_for_record(command: list[str], prompt: str) -> list[str]:
    return ["<PROMPT>" if argument == prompt else argument for argument in command]


def run_benchmark(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    agents = args.agents
    if not agents:
        fail("Select at least one agent with --agents")
    environment, file_values = effective_environment(args.env_file)
    model_overrides = {
        "claude": args.claude_model,
        "codex": args.codex_model,
        "agy": args.agy_model,
    }
    for agent, model in model_overrides.items():
        if model:
            environment[SAFE_MODEL_ENV[agent]] = model
    if "agy" in agents and not (environment.get("TLGF_BENCH_AGY_MODEL") or environment.get("TLGD_BENCH_AGY_MODEL")):
        model = configured_agy_model()
        if model:
            environment["TLGF_BENCH_AGY_MODEL"] = model
    cases = select_cases(manifest, args.cases)
    cache = ensure_repository(args.repo_cache, manifest)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{manifest['id']}__{timestamp}"
    run_root = args.results_root / run_id
    run_root.mkdir(parents=True, exist_ok=False)
    write_json(run_root / "manifest.json", manifest)
    versions: dict[str, Any] = {}
    for agent in agents:
        executable = find_executable(agent)
        if executable is None:
            fail(f"Agent CLI isn't available: {agent}")
        requested = environment.get(SAFE_MODEL_ENV.get(agent, "")) or None
        source = "flag or environment" if requested else None
        if agent == "codex" and not requested:
            requested = configured_codex_model()
            source = "codex config.toml" if requested else None
        versions[agent] = {
            "executable": executable,
            "version": command_version(agent, executable),
            "requested_model": requested,
            "requested_model_source": source,
            "reasoning_effort": reasoning_effort(agent, requested),
            "display_model": None,
        }
    environment_record = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "repository_cache": str(cache),
        "repository_commit": manifest["repository"]["commit"],
        "agents": versions,
        "seed": args.seed,
        "timeout_seconds": args.timeout,
        "max_attempts": args.max_attempts,
        "retry_policy": "any empty answer or any TRUNCATED result",
        "secrets_recorded": False,
    }
    write_json(run_root / "environment.json", environment_record)
    workspaces = create_workspaces(run_root, agents, cache, manifest, environment)
    print(f"Run: {run_id}")
    print(f"Results: {run_root}")
    for agent in agents:
        manage_agy = agent == "agy" and args.manage_agy_settings
        if manage_agy:
            print("[agy] enabling proceed-in-sandbox temporarily; exact settings will be restored", flush=True)
        with temporary_agy_sandbox_settings(manage_agy):
            isolated_environment = agent_environment(agent, environment)
            for case in cases:
                for repetition in range(1, args.repetitions + 1):
                    order = stable_condition_order(args.seed, agent, case["id"], repetition)
                    for order_index, condition in enumerate(order, 1):
                        suffix = manifest["conditions"][condition]["prompt_suffix"]
                        prompt = case["prompt"] + suffix
                        repository = workspaces[(agent, condition)]
                        command, requested_model = build_command(
                            agent, condition, repository, prompt, environment
                        )
                        print(
                            f"[{agent}] {case['id']} {condition} "
                            f"r{repetition} ({order_index}/2)",
                            flush=True,
                        )
                        workspace_before = repository_digest(repository)
                        attempts: list[dict[str, Any]] = []
                        for attempt_number in range(1, args.max_attempts + 1):
                            execution = execute(
                                command, repository, isolated_environment, args.timeout
                            )
                            attempt = derive_attempt(
                                agent,
                                {
                                    "attempt_number": attempt_number,
                                    "exit_code": execution["exit_code"],
                                    "timed_out": execution["timed_out"],
                                    "duration_seconds": execution["duration_seconds"],
                                    "raw_stdout": redact(execution["stdout"], file_values),
                                    "raw_stderr": redact(execution["stderr"], file_values),
                                },
                                requested_model,
                            )
                            attempts.append(attempt)
                            print(
                                f"  attempt={attempt_number}/{args.max_attempts} "
                                f"status={attempt['agent_status']} "
                                f"words={attempt['response_words']}",
                                flush=True,
                            )
                            if not should_retry_incomplete_answer(
                                attempt["agent_status"],
                                attempt["response"],
                                attempt_number,
                                args.max_attempts,
                            ):
                                break
                            print("  retrying: final answer was missing or truncated", flush=True)
                        workspace_after = repository_digest(repository)
                        workspace_unchanged = workspace_before == workspace_after
                        selected_attempt = attempts[-1]
                        result = {
                            "schema_version": 1,
                            "run_id": run_id,
                            "agent": agent,
                            "agent_version": versions[agent]["version"],
                            "case_id": case["id"],
                            "condition": condition,
                            "repetition": repetition,
                            "condition_order": order_index,
                            "repository_commit": manifest["repository"]["commit"],
                            "prompt": prompt,
                            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                            "command": safe_command_for_record(command, prompt),
                            "requested_model": requested_model,
                            "display_model": None,
                            "max_attempts": args.max_attempts,
                            "attempts": attempts,
                            "raw_stdout": selected_attempt["raw_stdout"],
                            "raw_stderr": selected_attempt["raw_stderr"],
                            "workspace_before_sha256": workspace_before,
                            "workspace_after_sha256": workspace_after,
                            "workspace_mutated": not workspace_unchanged,
                            "workspace_integrity_method": "digest",
                        }
                        regrade_result(result, case, repository)
                        result_path = run_root / "runs" / result_filename(
                            agent, case["id"], condition, repetition
                        )
                        write_json(result_path, result)
                        print(
                            f"  attempts={result['attempt_count']} "
                            f"quality={result['evaluation']['passed']} "
                            f"budget={result['evaluation']['budget_passed']} "
                            f"words={result['response_words']} "
                            f"total_output_tokens={result['usage']['output_tokens']}",
                            flush=True,
                        )
    write_reports(run_root)
    if not args.keep_workspaces:
        shutil.rmtree(run_root / "workspaces", ignore_errors=True)
    print(f"Report: {run_root / 'REPORT.md'}")
    return 0


def percentage_reduction(control: int | float | None, treatment: int | float | None) -> float | None:
    if not isinstance(control, (int, float)) or not isinstance(treatment, (int, float)) or control == 0:
        return None
    return round((1 - treatment / control) * 100, 2)


def delta(control: int | float | None, treatment: int | float | None) -> int | float | None:
    if not isinstance(control, (int, float)) or not isinstance(treatment, (int, float)):
        return None
    return treatment - control


def markdown_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value).replace("|", "\\|")


def paired_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        key = (result["agent"], result["case_id"], result["repetition"])
        grouped[key][result["condition"]] = result
    pairs: list[dict[str, Any]] = []
    for (agent, case_id, repetition), conditions in sorted(grouped.items()):
        if set(conditions) != set(CONDITIONS):
            continue
        control = conditions["control"]
        treatment_name = "tlgf" if "tlgf" in conditions else ("tlgd" if "tlgd" in conditions else [c for c in conditions if c != "control"][0])
        treatment = conditions[treatment_name]
        comparable = bool(
            control["evaluation"]["passed"] and treatment["evaluation"]["passed"]
        )
        control_usage = control["usage"]
        treatment_usage = treatment["usage"]
        control_final_usage = (
            control.get("final_step_usage")
            if isinstance(control.get("final_step_usage"), dict)
            else {}
        )
        treatment_final_usage = (
            treatment.get("final_step_usage")
            if isinstance(treatment.get("final_step_usage"), dict)
            else {}
        )
        pairs.append(
            {
                "agent": agent,
                "case_id": case_id,
                "repetition": repetition,
                "control_pass": control["evaluation"]["passed"],
                "treatment_pass": treatment["evaluation"]["passed"],
                "tlgf_pass": treatment["evaluation"]["passed"],
                "tlgd_pass": treatment["evaluation"]["passed"],
                "control_budget_pass": control["evaluation"].get("budget_passed"),
                "treatment_budget_pass": treatment["evaluation"].get("budget_passed"),
                "tlgf_budget_pass": treatment["evaluation"].get("budget_passed"),
                "tlgd_budget_pass": treatment["evaluation"].get("budget_passed"),
                "comparable": comparable,
                "mannerism_delta": delta(
                    control["evaluation"].get("style", {}).get("mannerism_count"),
                    treatment["evaluation"].get("style", {}).get("mannerism_count"),
                ),
                "mean_sentence_words_delta": delta(
                    control["evaluation"].get("style", {}).get("mean_sentence_words"),
                    treatment["evaluation"].get("style", {}).get("mean_sentence_words"),
                ),
                "output_token_reduction_percent": percentage_reduction(
                    control_usage.get("output_tokens"), treatment_usage.get("output_tokens")
                ),
                "final_step_output_token_reduction_percent": percentage_reduction(
                    control_final_usage.get("output_tokens"),
                    treatment_final_usage.get("output_tokens"),
                ),
                "output_word_reduction_percent": percentage_reduction(
                    control.get("response_words"), treatment.get("response_words")
                ),
                "reported_input_token_delta": delta(
                    control_usage.get("input_tokens"), treatment_usage.get("input_tokens")
                ),
                "reported_total_token_delta": delta(
                    control_usage.get("total_tokens"), treatment_usage.get("total_tokens")
                ),
                "duration_delta_seconds": delta(
                    control.get("duration_seconds"), treatment.get("duration_seconds")
                ),
            }
        )
    return pairs


def blind_label(run_id: str, agent: str, case_id: str, repetition: int) -> bool:
    material = f"{run_id}:{agent}:{case_id}:{repetition}:blind".encode()
    return hashlib.sha256(material).digest()[0] % 2 == 0


def write_reports(run_root: Path) -> None:
    manifest = read_json(run_root / "manifest.json")
    environment = read_json(run_root / "environment.json")
    results = [read_json(path) for path in sorted((run_root / "runs").glob("*.json"))]
    pairs = paired_results(results)
    summary = {
        "schema_version": 1,
        "run_id": environment["run_id"],
        "repository_commit": environment["repository_commit"],
        "run_count": len(results),
        "automated_pass_count": sum(bool(result["evaluation"]["passed"]) for result in results),
        "pairs": pairs,
    }
    write_json(run_root / "summary.json", summary)

    report = [
        f"# TLGF benchmark run `{environment['run_id']}`",
        "",
        "> [!IMPORTANT]",
        "> These are preliminary automated results. Complete the blind quality review before publishing a claim.",
        "",
        f"Commit: `{environment.get('repository_commit', '')}`",
        "",
        "## Runs",
        "",
        "| Agent | Case | Condition | Repetition | Attempts | Status | Finish | Quality | Word budget | Final words | Visible words | Mannerisms | Mean sentence words | Total loop output | Final-step output | Input tokens | Total seconds |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in sorted(results, key=lambda item: (item["agent"], item["case_id"], item["repetition"], item["condition"])):
        report.append(
            "| "
            + " | ".join(
                markdown_value(value)
                for value in (
                    result["agent"],
                    result["case_id"],
                    result["condition"],
                    result["repetition"],
                    result.get("attempt_count", 1),
                    result.get("agent_status"),
                    result.get("finish_reason"),
                    result["evaluation"]["passed"],
                    result["evaluation"].get("budget_passed"),
                    result["response_words"],
                    result.get("visible_text_words", result["response_words"]),
                    result["evaluation"].get("style", {}).get("mannerism_count"),
                    result["evaluation"].get("style", {}).get("mean_sentence_words"),
                    result["usage"].get("output_tokens"),
                    result.get("final_step_usage", {}).get("output_tokens"),
                    result["usage"].get("input_tokens"),
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
            "| Agent | Case | Repetition | Control quality | TLGF quality | Control budget | TLGF budget | Comparable | Loop-output reduction | Final-step reduction | Word reduction | Mannerism delta | Sentence-length delta | Input-token delta | Total-token delta |",
            "| --- | --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
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
                    pair["repetition"],
                    pair["control_pass"],
                    pair.get("tlgf_pass", pair.get("treatment_pass", pair["tlgd_pass"])),
                    pair["control_budget_pass"],
                    pair.get("tlgf_budget_pass", pair.get("treatment_budget_pass", pair["tlgd_budget_pass"])),
                    pair["comparable"],
                    pair["output_token_reduction_percent"],
                    pair["final_step_output_token_reduction_percent"],
                    pair["output_word_reduction_percent"],
                    pair["mannerism_delta"],
                    pair["mean_sentence_words_delta"],
                    pair["reported_input_token_delta"],
                    pair["reported_total_token_delta"],
                )
            )
            + " |"
        )
    report.extend(
        [
            "",
            "Percentages show reduction, so a negative value means that TLGF used more output. Quality excludes the word budget; a negative mannerism or sentence-length delta means that TLGF produced fewer mannerisms or shorter sentences.",
            "Provider token fields retain the provider's semantics. Compare paired runs from the same agent and model only.",
            "",
        ]
    )
    (run_root / "REPORT.md").write_text("\n".join(report), encoding="utf-8")

    cases = {case["id"]: case for case in manifest["cases"]}
    review = [
        f"# Blind review for `{environment['run_id']}`",
        "",
        "Review each pair without trying to identify the condition. For each answer, score factual accuracy from 0–4 and completeness, clarity, concision, and traceability from 0–2. Mark any critical factual error, invented command, weakened condition, or required omission. Workspace paths show `CONDITION` in place of the condition directory, so both answers of a pair cite the same neutral path.",
        "",
    ]
    grouped: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        grouped[(result["agent"], result["case_id"], result["repetition"])][result["condition"]] = result
    for (agent, case_id, repetition), conditions in sorted(grouped.items()):
        if set(conditions) != set(CONDITIONS):
            continue
        swap = blind_label(environment["run_id"], agent, case_id, repetition)
        treatment_cond = "tlgf" if "tlgf" in conditions else ("tlgd" if "tlgd" in conditions else [c for c in conditions if c != "control"][0])
        answer_a = conditions[treatment_cond] if swap else conditions["control"]
        answer_b = conditions["control"] if swap else conditions[treatment_cond]
        review.extend(
            [
                f"## Pair {agent} / {case_id} / repetition {repetition}",
                "",
                "### Prompt",
                "",
                cases[case_id]["prompt"],
                "",
                "### Review criteria",
                "",
                *[f"- {criterion}" for criterion in cases[case_id]["review_criteria"]],
                "",
                "### Answer A",
                "",
                neutralize_workspace_paths(answer_a["response"]),
                "",
                "### Answer B",
                "",
                neutralize_workspace_paths(answer_b["response"]),
                "",
                "| Score | Answer A | Answer B |",
                "| --- | ---: | ---: |",
                "| Factual accuracy (0–4) |  |  |",
                "| Completeness (0–2) |  |  |",
                "| Clarity (0–2) |  |  |",
                "| Concision (0–2) |  |  |",
                "| Natural, human tone (0–2) |  |  |",
                "| Source traceability (0–2) |  |  |",
                "| AI mannerisms present? |  |  |",
                "| Critical error? |  |  |",
                "| Preference: A / B / tie / neither |  |  |",
                "",
            ]
        )
    (run_root / "BLIND_REVIEW.md").write_text("\n".join(review), encoding="utf-8")


def regrade_run(args: argparse.Namespace) -> int:
    """Reparse and regrade a completed run without calling an agent."""
    run_root = args.run_root.resolve()
    if not (run_root / "runs").is_dir():
        fail(f"Run directory has no runs/ folder: {run_root}")
    stored_manifest = read_json(run_root / "manifest.json")
    manifest = load_manifest()
    stored_commit = stored_manifest.get("repository", {}).get("commit")
    if stored_commit != manifest["repository"]["commit"]:
        fail(
            "The saved run and current grader use different repository commits: "
            f"{stored_commit} != {manifest['repository']['commit']}"
        )
    cases = {case["id"]: case for case in manifest["cases"]}
    repository_cache = ensure_repository(args.repo_cache, manifest)
    result_paths = sorted((run_root / "runs").glob("*.json"))
    if not result_paths:
        fail(f"Run directory has no result JSON files: {run_root}")

    status_counts: dict[str, int] = defaultdict(int)
    pass_count = 0
    with tempfile.TemporaryDirectory(prefix="tlgf-regrade-") as directory:
        repository = Path(directory) / "repository"
        export_repository(repository_cache, manifest["repository"]["commit"], repository)
        for result_path in result_paths:
            result = read_json(result_path)
            case_id = result.get("case_id")
            condition = result.get("condition")
            if case_id not in cases or condition not in CONDITIONS:
                fail(f"Unknown case or condition in {result_path}")
            expected_prompt = (
                cases[case_id]["prompt"]
                + manifest["conditions"][condition]["prompt_suffix"]
            )
            if result.get("prompt") != expected_prompt:
                fail(f"Prompt mismatch in {result_path}")
            regrade_result(result, cases[case_id], repository)
            status_counts[str(result["agent_status"])] += 1
            pass_count += int(bool(result["evaluation"]["passed"]))
            write_json(result_path, result)

    environment_path = run_root / "environment.json"
    environment = read_json(environment_path)
    environment.update(
        {
            "regraded_at": datetime.now(timezone.utc).isoformat(),
            "grader_manifest_sha256": hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest(),
            "result_parser_schema_version": RESULT_PARSER_SCHEMA_VERSION,
        }
    )
    write_json(environment_path, environment)
    write_reports(run_root)
    statuses = ", ".join(f"{key}={value}" for key, value in sorted(status_counts.items()))
    print(f"Regraded {len(result_paths)} saved results without calling an agent")
    print(f"Statuses: {statuses}")
    print(f"Automated gates: {pass_count}/{len(result_paths)}")
    print(f"Report: {run_root / 'REPORT.md'}")
    return 0


def merge_runs(args: argparse.Namespace) -> int:
    """Merge agent runs and regrade every response with the current manifest."""
    manifest = load_manifest()
    repository_cache = ensure_repository(args.repo_cache, manifest)
    grading_directory = tempfile.TemporaryDirectory(prefix="tlgf-merge-")
    repository = Path(grading_directory.name) / "repository"
    export_repository(repository_cache, manifest["repository"]["commit"], repository)
    merged_results: list[dict[str, Any]] = []
    cases = {case["id"]: case for case in manifest["cases"]}
    run_directories = [path.resolve() for path in args.runs]
    for directory in run_directories:
        for result_path in sorted((directory / "runs").glob("*.json")):
            result = read_json(result_path)
            case_id = result.get("case_id")
            if case_id not in cases or result.get("condition") not in CONDITIONS:
                continue
            regrade_result(result, cases[case_id], repository)
            merged_results.append(result)
    if not merged_results:
        fail("No valid result files found across input run directories")

    agents = sorted({result["agent"] for result in merged_results})
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{manifest['id']}__{timestamp}"
    run_root = args.results_root / run_id
    (run_root / "runs").mkdir(parents=True)
    write_json(run_root / "manifest.json", manifest)
    source_ids: list[str] = []
    merged: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for source_root in args.runs:
        source_root = source_root.resolve()
        source_manifest = read_json(source_root / "manifest.json")
        source_environment = read_json(source_root / "environment.json")
        if source_manifest.get("repository", {}).get("commit") != manifest["repository"]["commit"]:
            fail(f"Repository commit mismatch in {source_root}")
        source_id = str(source_environment.get("run_id") or source_root.name)
        source_ids.append(source_id)
        source_agents = source_environment.get("agents")
        if isinstance(source_agents, dict):
            agents.update(source_agents)
        for result_path in sorted((source_root / "runs").glob("*.json")):
            result = read_json(result_path)
            case_id = result.get("case_id")
            condition = result.get("condition")
            if case_id not in cases or condition not in CONDITIONS:
                fail(f"Unknown case or condition in {result_path}")
            expected_prompt = (
                cases[case_id]["prompt"]
                + manifest["conditions"][condition]["prompt_suffix"]
            )
            if result.get("prompt") != expected_prompt:
                fail(f"Prompt mismatch in {result_path}")
            key = (
                str(result.get("agent")),
                str(case_id),
                str(condition),
                int(result.get("repetition", 0)),
            )
            replaced = merged.get(key)
            regrade_result(result, cases[case_id], repository)
            result["source_run_id"] = source_id
            if replaced is not None:
                result["replaced_source_run_id"] = replaced.get("source_run_id")
            result["run_id"] = run_id
            merged[key] = result

    environment_record = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "repository_cache": str(repository_cache),
        "repository_commit": manifest["repository"]["commit"],
        "agents": agents,
        "source_run_ids": source_ids,
        "secrets_recorded": False,
    }
    write_json(run_root / "environment.json", environment_record)
    for result in merged.values():
        write_json(
            run_root
            / "runs"
            / result_filename(
                result["agent"],
                result["case_id"],
                result["condition"],
                result["repetition"],
            ),
            result,
        )
    grading_directory.cleanup()
    write_reports(run_root)
    print(f"Merged run: {run_id}")
    print(f"Report: {run_root / 'REPORT.md'}")
    return 0


def prepare(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    cache = ensure_repository(args.repo_cache, manifest)
    print(f"Repository ready: {cache}")
    print(f"Pinned commit: {manifest['repository']['commit']}")
    return 0


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Check local prerequisites without calling a model")
    doctor_parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)

    prepare_parser = subparsers.add_parser("prepare", help="Prepare the pinned repository snapshot")
    prepare_parser.add_argument("--repo-cache", type=Path, default=DEFAULT_REPO_CACHE)

    merge_parser = subparsers.add_parser(
        "merge", help="Merge completed agent runs and regrade them"
    )
    merge_parser.add_argument("--runs", type=Path, nargs="+", required=True)
    merge_parser.add_argument("--repo-cache", type=Path, default=DEFAULT_REPO_CACHE)
    merge_parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)

    regrade_parser = subparsers.add_parser(
        "regrade", help="Reparse and regrade a saved run without calling an agent"
    )
    regrade_parser.add_argument("run_root", type=Path)
    regrade_parser.add_argument("--repo-cache", type=Path, default=DEFAULT_REPO_CACHE)

    run_parser = subparsers.add_parser("run", help="Run paired control and TLGF evaluations")
    run_parser.add_argument("--agents", type=parse_csv, required=True, choices=None)
    run_parser.add_argument("--cases", type=parse_csv)
    run_parser.add_argument("--repetitions", type=int, default=1)
    run_parser.add_argument(
        "--max-attempts",
        type=int,
        default=2,
        help="Maximum attempts when a run returns no final answer",
    )
    run_parser.add_argument("--timeout", type=int, default=300)
    run_parser.add_argument("--seed", type=int, default=20260819)
    run_parser.add_argument("--repo-cache", type=Path, default=DEFAULT_REPO_CACHE)
    run_parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    run_parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    run_parser.add_argument("--claude-model", help="Pin the Claude model for this run")
    run_parser.add_argument("--codex-model", help="Pin the Codex model for this run")
    run_parser.add_argument("--agy-model", help="Pin the Agy model for this run")
    run_parser.add_argument("--keep-workspaces", action="store_true")
    run_parser.add_argument(
        "--manage-agy-settings",
        action="store_true",
        help="Temporarily enable Agy proceed-in-sandbox and restore its settings",
    )
    return parser


def validate_arguments(args: argparse.Namespace) -> None:
    if args.command != "run":
        return
    unknown_agents = [agent for agent in args.agents if agent not in AGENTS]
    if unknown_agents:
        fail(f"Unknown agents: {', '.join(unknown_agents)}")
    if len(set(args.agents)) != len(args.agents):
        fail("Don't repeat an agent in --agents")
    if args.repetitions < 1:
        fail("--repetitions must be at least 1")
    if args.timeout < 30:
        fail("--timeout must be at least 30 seconds")
    if not 1 <= args.max_attempts <= 5:
        fail("--max-attempts must be between 1 and 5")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        validate_arguments(args)
        if args.command == "doctor":
            return doctor(args.env_file)
        if args.command == "prepare":
            return prepare(args)
        if args.command == "merge":
            return merge_runs(args)
        if args.command == "regrade":
            return regrade_run(args)
        if args.command == "run":
            return run_benchmark(args)
        fail(f"Unknown command: {args.command}")
    except BenchmarkError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
