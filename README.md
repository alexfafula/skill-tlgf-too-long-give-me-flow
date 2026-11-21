<h1 align="center">TLGF</h1>

<p align="center">
  <em>Too Long! Give Me Flow! &mdash; Control long AI chats like a gamepad.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/format-3%20blocks-111111?style=flat-square" alt="3 blocks">
  <img src="https://img.shields.io/badge/controls-1--4%20state%20%7C%20A--D%20act-111111?style=flat-square" alt="1-4 state, A-D act">
  <img src="https://img.shields.io/badge/resumes-2x%20cleaner-111111?style=flat-square" alt="2x cleaner resumes">
  <img src="https://img.shields.io/badge/license-MIT-111111?style=flat-square" alt="MIT license">
</p>

<p align="center">
  <img src="assets/gamepad.png" width="880" alt="TLGF: Messy AI chat to back in flow. Control it like a gamepad. Type $tlgf to get 3 short blocks. Press 1-4 to check state, or A-D to act.">
</p>

<p align="center">
  <strong>Messy AI chat &rarr; back in flow. Type <code>$tlgf</code>. Get 3 short blocks. Press one key to move.</strong><br>
  <strong>2&times; more clean resumes (34/45 vs 17/45) &middot; 15/15 on Claude Code &middot; up to &minus;71% less reading</strong><br>
  <sub>Paired benchmark across Claude Code (<code>claude-opus-5</code>), Agy (<code>gemini-3.7-flash-high</code>), and Codex CLI (<code>gpt-5.6-sol</code>). <a href="#numbers">Details</a>.</sub>
</p>

---

When you run several AI tabs at once, coming back to an older chat usually means scrolling through screens of tool logs just to find what's stuck.

**TLGF** replaces that wall of text with the same 3-block frame every time:

- **You are here** — project, thread, and current step in one line.
- **What's happening now (`1–4`)** — what's done, what's running, what's blocked.
- **Suggested next steps (`A–D`)** — concrete options, recommended one first.

**Numbers inspect state. Letters act.**

---

## Before / After

<p align="center">
  <img src="assets/beforeafter.png" width="880" alt="Before and after comparison: 450-word rambling summary without TLGF versus 57-word 3-block TLGF frame with 1-key action A.">
</p>

<details>
<summary>Copyable text version</summary>

<pre>
<b>you &gt;</b> <ins><b>How's the Stripe webhook going? $tlgf</b></ins>

<b>You are here:</b> Billing › Stripe webhooks › signatures
────────────────────────────────────────────────────────────
<b>What's happening now:</b>
1. Handler and retry logic are done in <code>src/billing/webhooks.ts</code>.
2. Replay-protection test fails on timestamp drift (14/15 pass).
3. Staging webhook secret is still missing in <code>.env.staging</code>.
────────────────────────────────────────────────────────────
<b>Suggested next steps:</b>
A. Fix the timestamp drift check in <code>webhooks.ts</code> and re-run tests (recommended).
B. Skip local replay tests for now and add the staging secret first.
────────────────────────────────────────────────────────────
<b>you &gt;</b> <ins><b>A</b></ins>
</pre>

</details>

Typing **`A`** runs the recommended fix directly—no repeating context, no replaying the frame.

---

## Controls

Use the latest frame like a gamepad (**`1–4` = check state**, **`A–D` = run next step**):

| You type | TLGF does |
| :--- | :--- |
| `2` or `expand 2` | Expands only status point 2. |
| `B` or `do B` | Picks or runs step B (when safe and allowed). |
| `B vs C` | Compares only the real difference between B and C. |
| `park 4` | Saves point 4 as an inactive lead with evidence and when to revisit it. |
| `fork 3` | Switches active work to point 3 and leaves a resume note for the current thread. |
| `deep dive 2` | Investigates point 2 while keeping a clear path back. |
| `refresh` | Rebuilds the frame from current files and logs. |

*Natural phrasing in any language works the same way. If there is no frame yet, TLGF builds one instead of guessing.*

When the agent literally cannot continue without you—a decision, secret, approval, or missing info—the frame starts with **⛔ Needs you**. Otherwise that banner stays hidden so it actually means something across open tabs.

---

## Numbers

<p align="center">
  <img src="assets/benchmark-gates.png" width="880" alt="Paired benchmark across 3 agents: TLGF passes 34/45 (76%) vs 17/45 (38%) control. Claude Code 15/15 vs 5/15, Agy 10/15 vs 7/15, Codex CLI 9/15 vs 5/15.">
</p>

<p align="center">
  <img src="assets/benchmark-impact.png" width="880" alt="Fact coverage and word reduction: 94-95% expected facts kept vs 77-84% control; up to -71% fewer words on Claude Code 1-key follow-ups.">
</p>

Full method, fixtures, and raw judge scores are in [`TLGF_BENCHMARK.md`](TLGF_BENCHMARK.md):

- **2× more clean resumes:** 34/45 (76%) with TLGF vs 17/45 (38%) without it across 90 paired runs. On Claude Code, TLGF nailed 15/15 messy resumes (vs 5/15 without) while cutting response length by 13–71% on 4 of 5 cases.
- **Why agents break without it:** When you jump back into an old thread, default agents fail 62% of the time—replaying the whole status on a 1-letter `B`, missing stale saved state or hidden retries, and burying blockers.
- **Less reading, almost nothing missed:** Blind judges scored TLGF at 94–95% of critical facts kept (vs 77–84% without), with higher scores on knowing where you are (1.89–1.94/2) and what to do next (1.74–1.80/2).

---

## Install

Install globally using the open-source [`skills` CLI](https://github.com/vercel-labs/skills):

```shell
npx skills@latest add https://github.com/alexfafula/skill-tlgf-too-long-give-me-flow/tree/main/tlgf -g -y -a <agent>
```

| Agent | CLI Flag |
| :--- | :--- |
| **Claude Code** | `-a claude-code` |
| **Codex CLI** | `-a codex` |
| **Agy (Antigravity CLI)** | `-a antigravity-cli` |
| **Cursor** | `-a cursor` |
| **GitHub Copilot** | `-a github-copilot` |
| **Windsurf** | `-a windsurf` |
| **Cline** | `-a cline` |
| **OpenCode** | `-a opencode` |

*Works with any agent supporting the [Agent Skills specification](https://agentskills.io).*

### Try without installing

```shell
# Claude Code
npx skills@latest use https://github.com/alexfafula/skill-tlgf-too-long-give-me-flow/tree/main/tlgf --agent claude-code

# Codex
npx skills@latest use https://github.com/alexfafula/skill-tlgf-too-long-give-me-flow/tree/main/tlgf --agent codex
```

### Update

```shell
npx skills@latest update tlgf
```

---

## Usage

Add `TLGF` anywhere in your prompt (or `$tlgf` where skill tags are supported):

```text
# Instant status & next steps
$tlgf

# Resume parked work
resume retry fix $tlgf

# Status + deliverable
status + test command $tlgf

# Any language
gdzie jesteśmy? $tlgf
```

---

## What it enforces

- **One thread at a time:** Only the active work stays visible; parked work shows up only if it affects the current path.
- **Numbers stay attached to context:** Results keep their run ID, model, retry state, or data limits.
- **No hidden retries:** If a task needed a retry to pass, say so—don't hide the first failure.
- **Real progress only:** Work is "running" only while it's actually running. Use real counts or milestones, never fake percentages.
- **Portable paths:** Local files use repo-relative paths, never `file://` links.
- **No meta-chatter:** Replies never echo `TLGF` or explain how the skill works.

---

## Keep state between sessions

When file writes are allowed, TLGF keeps a tiny restart index in `.tlgf/STATE.md` (current position, state, resume step, decisions, parked leads). On resume, it checks that file against your actual branch, files, and results before trusting it. Secrets, raw logs, and private chat are never saved there.

---

## Use without skill triggering

If your tool doesn't load skills automatically, two adapters apply the exact same rules:

- **Claude Code output style:** Copy `adapters/claude/output-styles/tlgf.md` to `~/.claude/output-styles/` (or `.claude/output-styles/`), then run `/output-style TLGF` or set `"outputStyle": "TLGF"` in `settings.json`.
- **`AGENTS.md` block:** Paste `adapters/agents/tlgf.md` into your `AGENTS.md` (or equivalent rules file).

---

## Repo layout & local check

```text
skill-tlgf-too-long-give-me-flow/
├── tlgf/
│   ├── SKILL.md                 Core 3-block contract, gamepad controls, continuity rules
│   ├── agents/openai.yaml       Display metadata and default invocation
│   ├── references/
│   │   ├── addressable-flow.md  Resolving 1-4 and A-D references
│   │   ├── continuity.md        Park, resume, switch, triage, and signal routing
│   │   └── lineage.md           The .tlgf/STATE.md restart index
│   ├── evals/cases.json         12 behavior-evaluation cases
│   ├── scripts/check.py         Package validator
│   └── LICENSE.txt              License shipped with installed copies
├── adapters/                    Claude Code output style and AGENTS.md block
├── assets/                      README visuals (gamepad, before/after, benchmarks)
├── benchmarks/                  Paired control-vs-TLGF harness, judge, and reports
├── docs/                        Product contract and forward tests
├── TLGF_BENCHMARK.md            Benchmark method and full results
├── CHANGELOG.md                 Version history
└── README.md                    This guide
```

Validate the local skill package:

```shell
python3 tlgf/scripts/check.py
```

Expected output:

```text
TLGF valid: triptych contract, 12 eval cases
```

---

## License

Created by [Aleksander Fafuła](mailto:aleksander@fafula.com).  
MIT License — see [LICENSE](LICENSE).

> [!NOTE]
> Independent open-source project by one developer, not affiliated with any AI vendor.
