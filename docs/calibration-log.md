# TLGF calibration log

Status: manifest `tlgf-continuity-v2` (grader revision 2.2); published run complete (`tlgf-continuity-v2__20260825T004144Z`)

Each entry records a run, what the gates showed, and any change to the skill or the grader that followed. A skill change is made only for a failure that repeats or that contradicts the product contract.

## Run `tlgf-continuity-v2__20260824T233902Z` — full default suite × 1, plus Flask

Agents: Claude Code 2.1.241 with `claude-opus-5`; Codex CLI 0.149.0 with `gpt-5.6-sol`; Agy 1.1.19 with `gemini-3.7-flash-high`. Thirteen default cases, one repetition, 78 answers, plus the pinned Flask case in `tlgf-continuity-v2__20260825T000928Z` (6 answers). Every answer completed on its first attempt. This was the first run with natural prompts and embedded frames.

| Host | Control quality | TLGF quality | Control budget | TLGF budget |
| --- | ---: | ---: | ---: | ---: |
| Claude, `claude-opus-5` | 5/13 | 12/13 | 3/13 | 4/13 |
| Codex, `gpt-5.6-sol` | 7/13 | 6/13 | 11/13 | 11/13 |
| Agy, `gemini-3.7-flash-high` | 7/13 | 11/13 | 8/13 | 11/13 |
| **All** | **19/39** | **29/39** | **22/39** | **26/39** |

Flask failed on every host in both conditions.

### What the failures were

Control failures were what natural prompts expose: replayed frames on follow-ups, no revisit condition on `park 3`, missing branch or project on resumes, and no preliminary signal on `useful-signal`.

TLGF failures split into three groups:

1. **Good behavior, wrong gate.** On `missing-frame`, Claude and Codex said that no frame existed, rebuilt a minimal frame from the workspace, and asked one bounded question — the behavior the skill prescribes — but the gate forbade any triptych and the `Needs you` signal. On `localized-labels`, Codex used natural Polish variants (`Tu jesteś`, `Co dzieje się teraz`) that the accepted list lacked. On `addressable-expand`, Codex wrote "completed without a final answer" and Agy wrote "empty response payload" without the word `OpenCode`; both answered point 2 correctly. On `stale-state`, Codex used the word `supersede`, which the grader inherited as a ban from the TLDF era although the TLGF skill never prohibits it. On Flask, every TLGF answer put the requested explanation after the closing break, as the contract requires, and the gate counted that as an unclosed frame; the gate also demanded the commit hash and branch, which the natural prompt never asks for.
2. **Unrequested detail.** `run-lineage` and `localized-labels` required the branch `clarity-fork` in an orientation answer to a prompt that doesn't mention it; Codex omitted it under TLGF.
3. **Skill misses.** Codex's `useful-signal` frame didn't surface the partner-north preview at all, and Codex's `decision-blocker` frame never named `migration-dry-run-20260821`. Claude and Agy passed both.

### Changes

1. Grader revision 2.1 (`benchmarks/tlgf/manifest.json`, `benchmarks/tlgf/run.py`): `missing-frame` accepts a minimal rebuilt frame and the `Needs you` signal, with a 120-word budget; per-case labels accept a list of natural variants for the first-content and `Needs you` gates, and the Polish case lists them; `addressable-expand` accepts `Qwen` or `OpenCode` and "without a final answer", "no answer", or "empty"; the `supersede` ban is gone; `branch` is no longer a required orientation fact for `run-lineage` and `localized-labels`; Flask carries `deliverable_after_frame: true`, which skips the closed-frame check, a 320-word budget, and no commit or branch requirement (both moved to `semantic_facts`).
2. Skill (`tlgf/SKILL.md`, "Choose what belongs in What's happening now"): "Omit it by default and never create a fourth field for it" became "Leave out trivia and unsupported patterns, and never create a fourth field for it." Reason: the sentence told the model to stay silent by default, which contradicts the product contract's promise to surface an evidence-backed signal; Codex stayed silent on `useful-signal`.

No change for the missing run name in Codex's `decision-blocker` frame: two hosts included it, and the manifest keeps it required.

## Run `tlgf-continuity-v2__20260825T001852Z` — check of revision 2.1, six cases × 1, plus Flask

Same hosts and models. TLGF quality 14/18 versus control 9/18 on the six revised cases; Flask 2/3 versus 3/3.

Remaining TLGF failures and what followed:

- Claude twice appended a compliance note after the closing break ("Read-only observed: I inspected … and changed nothing"), which the contract forbids. The note answers the prompt trailer "Read-only: don't modify files or use the web," which a real user wouldn't type and which the sandboxes enforce anyway. The trailer is gone from every prompt (`decision-blocker` keeps "Don't run the migration", Flask keeps "don't run the test or install anything"); the `workspace_unchanged` gate still catches a mutation.
- Agy described the stale-state conflict with "supersedes"; the mismatch group now also accepts `supersede`, `differs`, `disagree`, `no longer`, `newer than`, and `still names`.
- Claude quoted the test path in the single-test command; the command group accepts the quoted forms.
- Codex again left partner-north out of its `useful-signal` frame although its tool trace shows it read `preview.json`. The signal rule now names the canonical case — "such as a preliminary metric far outside its validated baseline" — as the example of what belongs in the frame. Claude and Agy surfaced the signal in both runs.

Manifest ID stays `tlgf-continuity-v2` (grader revision 2.2). The publishable run starts from this revision.

## Run `tlgf-continuity-v2__20260825T004144Z` — publishable run, 5 cases × 3 repetitions

Same hosts; Claude Code had auto-updated to 2.1.243. Grader revision 2.2, prompts without the read-only trailer. 90 answers; every answer but one completed on its first attempt, and one Agy TLGF answer came back empty.

| Host | Control quality | TLGF quality | Control budget | TLGF budget |
| --- | ---: | ---: | ---: | ---: |
| Claude, `claude-opus-5` | 5/15 | 15/15 | 5/15 | 8/15 |
| Codex, `gpt-5.6-sol` | 5/15 | 9/15 | 15/15 | 14/15 |
| Agy, `gemini-3.7-flash-high` | 7/15 | 10/15 | 13/15 | 15/15 |
| **All** | **17/45** | **34/45** | **33/45** | **37/45** |

### TLGF failures

- Codex refreshed the whole frame after executing `B` in all three `addressable-action` repetitions (Agy did so once). The contract allows a refreshed frame only after a material state change, and classifying a saved result changes no state, so the gate counts these as replays. Claude never replayed. No skill change was made after the publishable run; a clarifying sentence ("an analysis or classification is not a state change") is a candidate for the next revision.
- Codex never named the run `backfill-2026-08-20` in its `useful-signal` frames, although it now surfaced the partner-north signal in all three (it had missed it in both earlier runs, before the signal rule gained its example).
- Agy omitted the project `Customer analytics` from two `useful-signal` breadcrumbs, omitted alpha's 4/6 score once in `run-lineage`, mutated the workspace once in `addressable-action` (two `run_command` calls after the prompt lost its read-only trailer), and returned one empty `stale-state` answer, a host failure.

### Grader change after the run

The mutation gate now ignores `.tlgf/STATE.md`, which the skill may legitimately create or update when writes are authorized, and records `state_file_updated` beside `workspace_mutated`. The published run keeps its recorded gate results; the change applies to later runs.

### Judge result

Claude judge (`claude-sonnet-5`): TLGF preferred 17, control 19, position-dependent 8. Codex judge (`gpt-5.6-sol`): 27, 11, 6. Unanimous on 27 of 44 pairs (TLGF 15, control 11). Both judges scored TLGF higher on orientation, actionability, completeness, accuracy, and fact coverage (0.94–0.95 vs 0.77–0.84) and lower on natural tone; the Claude judge also scored traceability lower. The Claude judge's session limit interrupted 17 pairwise and 17 fact verdicts; `judge.py --resume` redid exactly those after the limit reset.

Reading: the frame wins on what it is for — position, state, next action — and loses on prose feel. A future revision could test whether shorter points or fewer bold labels recover tone without losing orientation.
