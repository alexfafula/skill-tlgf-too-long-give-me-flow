# TLGF — Too Long! Give Me Flow!

> **Find where you are when you're lost in a long AI chat. Skip the details, get back into flow.**

---

## Why use this

When you run several AI sessions in parallel, returning to an older tab usually means scrolling through screens of tool logs, replayed history, and buried status updates.

**TLGF** replaces that wall of text with a compact, predictable 3-block frame:

- **Where you are** — A semantic breadcrumb of the exact project, workstream, and stage.
- **What's happening now (`1, 2, 3`)** — Numbered points showing what just finished, what is running, and what is blocked.
- **Suggested next steps (`A, B, C`)** — Lettered decisions and forward actions, with the recommended choice listed first.

> **Numbers = current state.** **Letters = decisions and next actions.**

### What it looks like

<pre>
<b>you &gt;</b> <ins><b>How's the Stripe webhook integration going? $tlgf</b></ins>

<b>You are here:</b> Billing › Stripe webhooks › signature verification
────────────────────────────────────────────────────────────
<b>What's happening now:</b>
1. Webhook handler and retry logic are implemented in <code>src/billing/webhooks.ts</code>.
2. Local test suite passes (14/14), except the replay-protection test which is failing on timestamp drift.
3. Staging webhook secret is still missing from <code>.env.staging</code>.
────────────────────────────────────────────────────────────
<b>Suggested next steps:</b>
A. Fix the timestamp drift check in <code>webhooks.ts</code> and re-run the suite (recommended).
B. Skip local replay tests for now and add the staging secret first.
────────────────────────────────────────────────────────────
<b>you &gt;</b> <ins><b>A</b></ins>
</pre>

From there, typing <b><code>A</code></b> immediately kicks off the recommended fix.

---

## Frame controls

Reference items from the latest frame by number or letter without repeating context:

| You write | TLGF does |
| :--- | :--- |
| `2` or `expand 2` | Expands only status point 2. |
| `B` or `do B` | Selects or runs action B (when safe and authorized). |
| `B vs C` | Compares only the key differences between options B and C. |
| `park 4` | Saves point 4 as an inactive lead with its evidence and a revisit condition. |
| `fork 3` | Switches the active workstream to point 3 and leaves a resume cue for the current one. |
| `deep dive 2` | Investigates point 2 while keeping a path back to the main thread. |
| `refresh` | Rebuilds the frame from current evidence. |

*Natural phrasing in your own language works the same way. If there is no active frame yet, TLGF builds one instead of guessing.*

When work is blocked on something only you can provide—a decision, credentials, a secret, or external info—the frame starts with `⛔ **Needs you**`. Otherwise, that banner is omitted so it stays meaningful across multiple open tabs.

---

## Installation

Install TLGF globally across your projects using the open-source [`skills` CLI](https://github.com/vercel-labs/skills):

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

*Supports any agent compatible with the [Agent Skills specification](https://agentskills.io).*

### Try without installing

Run a single session with TLGF loaded in memory:

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

## Usage examples

Add `TLGF` anywhere in your prompt (or `$tlgf` in agents that support skill tags):

```text
# Quick status and decision (trigger only)
$tlgf
# or
TLGF

# Pick up an old session
Where does this stand and what's next? TLGF

# Resume parked work
New session. Pick up the parked retry investigation where it stopped. TLGF

# Hand work off to a teammate
I'm handing this branch to Dana tomorrow. Give her the frame. TLGF

# Request a deliverable alongside the status
Status, then the exact command to rerun the failing suite. TLGF

# Multilingual support (labels adapt naturally, identifiers stay exact)
Wracam do tego okna po przerwie. Gdzie jestem i co dalej? TLGF

# Standalone question (stays out of the way, answers without the frame)
What does idempotent mean? TLGF
```

---

## What TLGF enforces

- **Single focus:** Only one active thread stays visible; parked work appears only when it affects the current path.
- **Context with results:** Metrics and findings stay tied to the conditions needed to read them (run ID, model, retry state, or data limits).
- **Honest retries:** A pass after a retry is reported as recovered evidence, never as proof of first-attempt reliability.
- **Real progress:** Work is described as running only while it's actually running. Progress uses real counts or named milestones, never manufactured percentages.
- **Portable paths:** Local artifacts use repository-relative paths, never `file://` URLs.
- **No meta-chatter:** Replies never echo the `TLGF` trigger or explain how the skill works.

---

## Keep state between sessions

When project writes are authorized, TLGF maintains a lightweight restart index in `.tlgf/STATE.md` tracking the situation, current state, resume action, decisions, and parked leads. On resume, it checks that file against the current branch, artifacts, and results before trusting it. Secrets, private chat, and raw logs are never written there.

---

## Use TLGF without skill triggering

If your host doesn't support automatic skill discovery, two adapters apply the exact same contract:

- **Claude Code output style:** Copy `adapters/claude/output-styles/tlgf.md` to `~/.claude/output-styles/` (or a project's `.claude/output-styles/`), then run `/output-style TLGF` or set `"outputStyle": "TLGF"` in `settings.json`.
- **`AGENTS.md` block:** Paste `adapters/agents/tlgf.md` into your `AGENTS.md` (or equivalent persistent instruction file).

---

## Architecture & Verification

```text
skill-tlgf-too-long-give-me-flow/
├── tlgf/
│   ├── SKILL.md                 Triptych contract, Addressable Flow rules, continuity gates
│   ├── agents/openai.yaml       Display metadata and default invocation
│   ├── references/
│   │   ├── addressable-flow.md  Resolving numbered and lettered references
│   │   ├── continuity.md        Park, resume, switch, triage, and signal routing
│   │   └── lineage.md           The .tlgf/STATE.md restart index
│   ├── evals/cases.json         12 behavior-evaluation cases
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

### Validate local package

```shell
python3 tlgf/scripts/check.py
```

Expected output:
```text
TLGF valid: triptych contract, 12 eval cases
```

---

## Benchmark

[`TLGF_BENCHMARK.md`](TLGF_BENCHMARK.md) details the paired benchmark across Claude Code (Fable 5.2, Opus 5.5), Codex (GPT-5.6-Terra), and Agy (Gemini 3.8 Flash):

- **Deterministic gates:** TLGF passed the gates 34/45 times versus 17/45 for the control group. Claude passed all 15 TLGF gates while cutting response length by 13% to 71% compared to control answers.
- **Control failures:** Without TLGF, models frequently replayed the whole frame on `B`, omitted revisit conditions on `park`, missed stale-state conflicts or retry costs behind recovered passes, and left preliminary signals out of status.
- **Fact coverage & orientation:** Model judges rated TLGF significantly higher on orientation, actionability, completeness, and fact coverage (94–95% of expected facts vs. 77–84% for control).

---

## License & Attribution

Created by [Aleksander Fafuła](mailto:aleksander@fafula.com).  
Available under the [MIT License](LICENSE).

> [!NOTE]
> TLGF is an independent open-source project by one developer, not affiliated with any AI vendor.
