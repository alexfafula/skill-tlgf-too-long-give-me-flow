# Claude Code output-style adapter forward test

Date: 2026-08-25
Agent: Claude Code 2.1.241, model `claude-sonnet-5`, headless `claude -p`
Adapter: `adapters/claude/output-styles/tlgf.md`, selected through a project `.claude/settings.json` with `"outputStyle": "TLGF"`; no skill installed; `--setting-sources project`; tools `Read,Glob,Grep`; stdin closed.
Workspace: a copy of `benchmarks/tlgf/fixtures/run-lineage` initialized as its own Git repository.

The `init` event of every session reported `output_style: TLGF`, so the adapter loaded without skill triggering. Three prompts from the `tlgf-continuity-v2` manifest were sent.

## Result

| Prompt | Behavior | Reader words |
| --- | --- | --- |
| Natural status question (`run-lineage`) | Triptych with the three labels, four numbered points, lettered steps, `---` after every field, nothing after the closing break | 215 |
| `expand 2` with the prior frame embedded | Started with `Point 2:`, answered only point 2, no triptych replay, no `file://` link | 125 |
| `B` with the prior frame embedded | Started with `B —`, executed the classification, no triptych replay, no mention of actions A or C | 123 |

The two follow-up answers checked the embedded frame against the workspace reports and reported that the frame's Qwen timeout claim conflicts with the fixture, where the retry belongs to run gamma. That conflict is an artifact of this test, which reused the `run-lineage` fixture for prompts written for the `addressable-flow` fixture; the adapter's verify-before-acting behavior is the intended one.

Observed deviations from the contract: the status answer used four points and three steps with sentences longer than the one-or-two-sentence guidance, and it exceeded the 180-word budget of the benchmark case. Sonnet showed the same length pattern under the skill, so this is a model tendency rather than an adapter defect.

## Answers

### `status` — 215 reader-visible words

```text
**You are here:** TLGF benchmark › Qwen prompt v2 vs v3 comparison › reviewing beta's remaining gate failure

---

**What's happening now:**

1. v3 (run beta) beats v2 (run alpha) on Qwen: 5/6 gates passed vs 4/6 — v3 fixed the `active-lineage` gate that v2 failed.
2. Both v2 and v3 still fail the same `resume-cue` gate on Qwen, so that regression is not something v3's wording addressed.
3. Run gamma reruns the same v3 prompt on Claude Opus 5 and passes all 6 gates, including `resume-cue`, but only on a retry — attempt 1 returned `NO_FINAL_ANSWER`, attempt 2 succeeded.
4. `.tlgf/STATE.md` (last updated 2026-08-19) already flags the resume-cue failure in beta as the next thing to investigate.

---

**Suggested next steps:**

A. Investigate why `resume-cue` fails on Qwen specifically — compare beta's transcript against gamma's successful attempt to see whether it's a prompt-wording gap or a Qwen capability/formatting limitation.
B. Since gamma needed two attempts to clear all gates, check whether its first `NO_FINAL_ANSWER` attempt is a host-reliability fluke (unrelated to prompt quality) before crediting v3 with the gamma pass.
C. If A confirms a Qwen-specific limitation, decide whether v3 should be considered validated as-is (Qwen's resume-cue gap treated as a known model constraint, not a prompt defect) rather than iterating to v4.

---
```

### `addressable-expand` — 125 reader-visible words

```text
Point 2: The evidence doesn't match — the NO_FINAL_ANSWER-then-retry pattern belongs to run `gamma`, which is `claude-opus-5.0`, not Qwen. Qwen's two runs (`alpha` prompt v2, `beta` prompt v3) each completed in a single attempt with no failed/no-answer status recorded; their only issue is gate failures (`active-lineage` + `resume-cue` for alpha, just `resume-cue` for beta).

- `reports/alpha/summary.json`: qwen, v2, 4/6 gates, 1 attempt, failed `active-lineage` + `resume-cue`.
- `reports/beta/summary.json`: qwen, v3, 5/6 gates, 1 attempt, failed `resume-cue` only — prompt v3 fixed `active-lineage` over v2.
- `reports/gamma/summary.json`: claude-opus-5.0, v3, 6/6 gates, attempt 1 = `NO_FINAL_ANSWER`, attempt 2 = `SUCCESS` (a genuine retry-recovery case).

The prior frame's claim that Qwen timed out is stale/incorrect for this data set — that behavior is on Claude's run, not Qwen's.
```

### `addressable-action` — 123 reader-visible words

```text
**B — classification:** The Qwen result is a host-reliability outcome, not style evidence. Both qwen runs (alpha, beta) completed in a single attempt with no timeout or missing-answer status recorded — alpha failed 2/6 gates (`active-lineage`, `resume-cue`), beta (prompt v3) failed only `resume-cue`. Neither run shows the retry/timeout behavior described; that pattern is only present in gamma, which is a claude-opus-5.0 run (`NO_FINAL_ANSWER` → `SUCCESS` on retry), tagged `cross-model-diagnostic`.

So: no qwen run in `reports/` currently demonstrates a timeout-on-retry. If that observation came from a session outside these three summaries, it isn't captured here and can't be scored as either a style improvement or a style regression — it stays classified as inconclusive/host-side until a qwen run with a matching attempt trace exists.
```
