# TLGF — Too long! Give me flow!

> [!TIP]
> ## Get your position back in one glance
>
> **When an AI session gets too long to follow, add `TLGF` to your prompt.** You get where you are, what is happening, and the shortest useful path forward — in three fields you can point at by number or letter.

You run several AI sessions at once. You come back to one of them and the last screen is a wall of text: tool narration, replayed history, a status buried in the middle. TLGF turns that screen into a control surface.

TLGF is an [Agent Skill](https://agentskills.io/specification). It restores the user's position at the smallest useful level, shows what is moving now, and makes the current state and the forward path directly addressable. Write `TLGF` in a prompt about ongoing work; steer with `expand 2`, `B`, or `refresh`.

> [!NOTE]
> TLGF is an independent project by one developer. It isn't affiliated with any AI vendor.

## The frame

A TLGF answer to "where does this stand?" has this shape, with the labels rendered in your language:

```text
**You are here:** Customer analytics › August backfill › import running

---

**What's happening now:**

1. The import has completed 72 of 120 shards with no failures.
2. Preliminary: partner-north shows 18.4% conversion in a nondeduplicated preview versus a 6.2% validated baseline.

---

**Suggested next steps:**

A. Let the import finish, then run validation; this decides whether the partner-north signal is real.

---
```

- **You are here** is a semantic breadcrumb: project › workstream › stage, like a book, chapter, and subsection.
- **What's happening now** holds one to four numbered points: what is running, what just finished, what is waiting, what is blocking. Numbers belong only to current state.
- **Suggested next steps** holds one to four lettered actions. Letters belong only to the future path. When you must choose, the recommended option comes first.
- Nothing follows the closing `---` in a status answer. A requested deliverable goes after it, once.

When only you can unblock the work — a decision, an authority, a secret, an external fact — the frame starts with one signal: `⛔ **Needs you**`. Otherwise the signal is absent, so it stays meaningful across many windows.

## Point at the frame

Refer to the latest frame without repeating it:

| You write | TLGF does |
| --- | --- |
| `2` or `expand 2` | Expands only point 2. |
| `B` or `do B` | Selects or executes action B when it's safe and authorized. |
| `B vs C` | Compares only the material difference. |
| `park 4` | Keeps point 4 as an inactive lead with evidence and a revisit condition. |
| `fork 3` | Makes point 3 the active workstream and leaves a resume cue. |
| `deep dive 2` | Investigates point 2 while keeping a return path. |
| `refresh` | Rebuilds the frame from current evidence. |

Natural phrasing in your language works the same way. If no frame exists, TLGF says so and rebuilds one instead of guessing.

TLGF doesn't force the frame onto a standalone question. Ask "What does idempotent mean? TLGF" and you get a plain answer.

## Install

### Claude Code

```shell
npx skills@latest add https://github.com/alexfafula/skill-tlgf-too-long-give-me-flow/tree/main/tlgf -g -a claude-code -y
```

### Codex

```shell
npx skills@latest add https://github.com/alexfafula/skill-tlgf-too-long-give-me-flow/tree/main/tlgf -g -a codex -y
```

These commands install TLGF globally for use across projects. They use the open source [`skills` CLI](https://github.com/vercel-labs/skills) and require Node.js and `npx`. Start a new agent session if TLGF doesn't appear immediately.

### Other popular agents

The following commands are also ready to paste.

#### Cursor

```shell
npx skills@latest add https://github.com/alexfafula/skill-tlgf-too-long-give-me-flow/tree/main/tlgf -g -a cursor -y
```

#### Agy (Antigravity CLI)

```shell
npx skills@latest add https://github.com/alexfafula/skill-tlgf-too-long-give-me-flow/tree/main/tlgf -g -a antigravity-cli -y
```

#### GitHub Copilot

```shell
npx skills@latest add https://github.com/alexfafula/skill-tlgf-too-long-give-me-flow/tree/main/tlgf -g -a github-copilot -y
```

#### OpenCode

```shell
npx skills@latest add https://github.com/alexfafula/skill-tlgf-too-long-give-me-flow/tree/main/tlgf -g -a opencode -y
```

#### Windsurf

```shell
npx skills@latest add https://github.com/alexfafula/skill-tlgf-too-long-give-me-flow/tree/main/tlgf -g -a windsurf -y
```

#### Cline

```shell
npx skills@latest add https://github.com/alexfafula/skill-tlgf-too-long-give-me-flow/tree/main/tlgf -g -a cline -y
```

For every supported target, see the [`skills` CLI agent list](https://github.com/vercel-labs/skills#supported-agents).

## Try without installing

### Claude Code

Start a supported agent with TLGF loaded for one session:

```shell
npx skills@latest use https://github.com/alexfafula/skill-tlgf-too-long-give-me-flow/tree/main/tlgf --agent claude-code
```

### Codex

```shell
npx skills@latest use https://github.com/alexfafula/skill-tlgf-too-long-give-me-flow/tree/main/tlgf --agent codex
```

These commands don't install TLGF or change the agent's persistent configuration.

## Use TLGF

Write `TLGF` in any prompt about ongoing work:

```text
I just came back to this window. Where does the migration stand and what happens next? TLGF
```

Agents that support explicit `$skill` mentions also accept `$tlgf`.

### Resume a parked investigation

```text
New session. Pick up the parked retry investigation where it stopped. TLGF
```

### Hand work off

```text
I'm handing this branch to Dana tomorrow. Give her the frame. TLGF
```

### Get a deliverable with the frame

```text
Status, then the exact command to rerun the failing suite. TLGF
```

### Work in your language

```text
Wracam do tego okna po przerwie. Gdzie jestem i co dalej? TLGF
```

The labels are rendered naturally in the language of the prompt; technical identifiers stay exact.

## What TLGF protects

- One active thread stays visible; parked work appears only when it affects the current path.
- A result stays beside the condition needed to interpret it: run, model, retry state, evidence limit.
- A pass after a retry is recovered evidence, not proof of first-attempt reliability.
- Work is described as running only while it is actually running. Progress uses named milestones or real counts, never a manufactured percentage.
- Local artifacts use repository-relative paths; the answer never emits `file://` URLs.
- The answer never echoes the trigger word or explains the skill.

## Keep state between sessions

When project writes are authorized, TLGF keeps a small restart index in `.tlgf/STATE.md`: situation, current state, resume action, decisions, and parked leads. On resume it verifies that index against the current branch, artifacts, and results before relying on it. It never stores secrets, private conversation, or raw logs there.

## Apply TLGF without skill triggering

Two adapters apply the same contract in hosts that don't discover skills:

- **Claude Code output style:** copy `adapters/claude/output-styles/tlgf.md` to `~/.claude/output-styles/` (or a project's `.claude/output-styles/`), then run `/output-style TLGF` or set `"outputStyle": "TLGF"` in `settings.json`.
- **`AGENTS.md` block:** paste `adapters/agents/tlgf.md` into `AGENTS.md` or the equivalent persistent instruction file.

The adapters change packaging, not the contract.

## Architecture

```text
skill-tlgf-too-long-give-me-flow/
├── tlgf/
│   ├── SKILL.md                 Triptych contract, Addressable Flow rules, continuity gates
│   ├── agents/openai.yaml       Display metadata and default invocation
│   ├── references/
│   │   ├── addressable-flow.md  Resolving numbered and lettered references
│   │   ├── continuity.md        Park, resume, switch, triage, and signal routing
│   │   └── lineage.md           The .tlgf/STATE.md restart index
│   ├── evals/cases.json         Twelve behavior-evaluation cases
│   ├── scripts/check.py         Deterministic package validator
│   └── LICENSE.txt              License included with installed copies
├── adapters/                    Claude Code output style and AGENTS.md block
├── benchmarks/                  Paired control-versus-TLGF benchmark, judge, and reports
├── docs/                        Product contract and forward tests
├── TLGF_BENCHMARK.md            Benchmark method and results
├── CHANGELOG.md                 Version history
├── LICENSE                      Repository license
└── README.md                    This guide
```

The skill keeps its execution contract in `SKILL.md` and opens a reference only for a complex resume, a short reference that parks or forks, or a change to persistent state.

## Validate a checkout

```shell
python3 tlgf/scripts/check.py
```

A valid package reports:

```text
TLGF valid: triptych contract, 12 eval cases
```

The validator checks the frontmatter, the public template, the required rules in the skill and both adapters, the reference routing, the bundled license, and the evaluation cases. It uses only the Python standard library.

## Benchmark

[`TLGF_BENCHMARK.md`](TLGF_BENCHMARK.md) describes the paired benchmark: the same agent and model answer the same natural prompt — "Back on the Qwen prompt v3 versus v2 comparison. Where does it stand and what's next?" — with and without TLGF, inside identical fixtures. Deterministic gates check exact run names, paths, and numbers, the frame structure, the conditional signal, and portable links; two model judges score the answers.

In the published run on Claude Code (`claude-opus-5`), Codex (`gpt-5.6-sol`), and Agy (`gemini-3.7-flash-high`) — five cases, three repetitions each — TLGF answers passed the gates 34 times out of 45 and control answers 17 times. Claude passed all 15 TLGF gates; its TLGF answers were 13% to 71% shorter than its controls. Without the skill, the hosts mostly replayed the frame on `B`, gave no revisit condition on `park`, missed the stale-state conflict or the retry cost behind a recovered pass, and left a preliminary signal out of the status.

What the benchmark doesn't show: a general length reduction (Codex's terse controls were often shorter than its frames) or a compute-cost saving.

Two model judges, shown each pair in both positions, scored TLGF answers higher on orientation, actionability, completeness, and fact coverage (94–95% of the expected facts against 77–84% for control) and lower on natural tone, because a labeled frame reads less like prose. Pairwise, the Codex judge preferred TLGF in 27 of 44 pairs and the Claude judge in 17, with 19 for control; they agreed on 27 pairs, 15 of them for TLGF. Read that as evidence for orientation, not for prose quality. One caveat: the judge prompts for 15 Codex and Agy pairs contained a workspace path segment that could reveal the condition; `TLGF_BENCHMARK.md` records it, and those pairs are due for re-judging with neutral paths.

## Update TLGF

```shell
npx skills@latest update tlgf
```

Restart the agent session if it continues to use a cached version.

## Author

Created by [Aleksander Fafuła](mailto:aleksander@fafula.com).

## License

TLGF is available under the [MIT License](LICENSE).
