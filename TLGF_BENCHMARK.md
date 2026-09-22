# TLGF benchmark

The TLGF benchmark tests whether an AI agent restores useful orientation for a returning user: where the work stands, what is happening, and the shortest useful path forward, without losing evidence boundaries or forcing structure onto a standalone question.

The same agent and model answer the same prompt in two conditions inside identical read-only fixtures:

- **Control:** TLGF is unavailable, and the prompt doesn't mention it.
- **TLGF:** TLGF is available as a project skill, and the prompt ends with `TLGF`.

Compare conditions within the same agent and model only. Reader-visible words, quality, host reliability, and host-reported tokens are separate outcomes: a compact answer can still need an expensive agent loop.

The current manifest is `tlgf-continuity-v2`. Version 1 prompts told the agent what to do ("Do not replay the full frame", "the next step genuinely needs my decision"), so both conditions received the behavior as an instruction and the benchmark mostly measured format compliance. Version 2 uses the prompt a busy person would actually type and moves every expectation into the grader. Results from version 1 aren't comparable with version 2.

## Cases

| Case | Mode | What the prompt looks like | What the treatment must do |
| --- | --- | --- | --- |
| `standalone-restraint` | explain | "What does idempotent mean in an HTTP API? … One concrete request example." | Answer plainly; no frame, no invented lineage. |
| `run-lineage` | orient | "Back on the Qwen prompt v3 versus v2 comparison. Where does it stand and what's next?" | Name beta as active and alpha as its predecessor, keep gamma outside the comparison, point at the failed gate. |
| `park-resume` | resume | "New session. Pick up the parked retry investigation where it stopped and check the recorded stopping point." | Use the saved state, verify the stopping point in the source, keep the regression hypothesis unresolved. |
| `stale-state` | resume | "Where does this benchmark stand? Check the saved state against what's actually in the workspace before trusting it." | Report the mismatch, treat gamma as current, keep its retry cost visible. |
| `useful-signal` | orient | "The August backfill is running while I work on other things. Quick status?" | Keep the import running, surface the preliminary partner-north signal unprompted, defer it until validation. |
| `addressable-expand` | follow-up | The prior frame, then "expand 2". | Expand only point 2; no frame replay. |
| `addressable-action` | follow-up | The prior frame, then "B". | Execute the bounded classification; no frame replay; no mention of A or C. |
| `decision-blocker` | orient | "Release status? The migration dry run flagged something." | Detect the owner gate from `dry-run.md`, start with `⛔ Needs you`, put the recommended path first. |
| `park-point` | follow-up | The prior frame, then "park 3". | Keep the lead with evidence and a revisit condition; no frame replay. |
| `refresh-after-action` | orient | The prior frame, then "I ran A … refresh". | One refreshed frame; the resolved action doesn't carry forward. |
| `compare-b-vs-c` | follow-up | The prior frame, then "B vs C". | Compare only the material difference, recommendation first. |
| `missing-frame` | follow-up | "do B" with no prior frame. | Say there is no frame; ask one bounded question; invent nothing. |
| `localized-labels` | orient | The run-lineage question in Polish. | Render the three labels in Polish; keep identifiers exact. |
| `flask-error-handlers` | resume, opt-in | Resume a pinned Flask investigation after a detour; the saved state is stale. | Verify run beta, explain the dispatch boundary once, name one bounded assertion and test command. |

Follow-up prompts embed the previous frame as the assistant's earlier message because the CLIs run one turn at a time. Real multi-turn sessions are planned as a later phase.

## Check the benchmark

```shell
python3 benchmarks/tlgf/run.py doctor
python3 -m unittest discover -s benchmarks/tlgf/tests -p 'test_*.py'
```

## Run it

Run a paired smoke test on Codex for two cases:

```shell
benchmarks/tlgf/run-smoke.sh --cases run-lineage,useful-signal
```

Run the default suite (every case except Flask) on the three agents with pinned models:

```shell
python3 benchmarks/tlgf/run.py run \
  --agents claude,codex,agy \
  --repetitions 1 \
  --claude-model claude-opus-5 \
  --agy-model gemini-3.7-flash-high
```

Prepare and add the pinned Flask case:

```shell
benchmarks/tlgf/prepare-real-repos.sh
python3 benchmarks/tlgf/run.py run --agents claude,codex,agy --cases flask-error-handlers
```

Resume an interrupted run without overwriting saved answers:

```shell
python3 benchmarks/tlgf/run.py run --resume-run benchmarks/results/tlgf/RUN_ID --agents claude,codex,agy
```

Results are written under `benchmarks/results/tlgf/<run-id>/`. Every workspace is a copy of the fixture initialized as its own Git repository, so no memory, rules, or settings from an enclosing checkout reach the agent.

## Grading

Three layers grade every answer. None of them decides alone.

**Deterministic gates** check exact tokens and structure: required run names, branches, paths, and numbers; forbidden legacy labels and `file://` URLs; for orientation and resume cases, `You are here` (or the case's localized label) as the first visible content, one to four numbered points, one to four lettered steps, exactly three `---` breaks, and nothing after the closing break; the `⛔ Needs you` signal exactly when the case requires it; no process narration; an unchanged workspace. The word budget is reported beside quality, not inside it.

**Style signals** (mannerism-lexicon hits, mean sentence length, headings, bullets, bold spans) describe the prose and never gate.

**Semantic facts** are judged, not matched. Each case lists the statements a good answer conveys ("gamma uses a different model and required a retry, so it is outside the comparison"). `benchmarks/judge.py --facts` asks a judge model, per answer, which statements the answer conveys and reports coverage per condition. The same script also runs the blinded pairwise judge: both answers, hidden conditions, both positions, two judges, with agreement and position dependence reported in `JUDGE.md`.

```shell
python3 benchmarks/judge.py benchmarks/results/tlgf/RUN_ID --facts
```

A human blind review worksheet (`BLIND_REVIEW.md`) is generated per run; none was performed for the published run, whose claims rest on the deterministic gates and the two LLM judges.

## Results

Run `tlgf-continuity-v2__20260825T004144Z`: five cases (`run-lineage`, `stale-state`, `useful-signal`, `addressable-action`, `decision-blocker`), three repetitions, condition order alternated, Claude Code 2.1.243 with `claude-opus-5`, Codex CLI 0.149.0 with `gpt-5.6-sol` (`model_reasoning_effort="medium"`), and Agy 1.1.19 with `gemini-3.7-flash-high`. 90 answers; one Agy answer under TLGF came back empty and counts as a failure. The published copy, with the HTML report and the judge output, is under `benchmarks/published/tlgf-continuity-v2__20260825T004144Z/`.

| Host | Control quality | TLGF quality | Control budget | TLGF budget |
| --- | ---: | ---: | ---: | ---: |
| Claude, `claude-opus-5` | 5/15 | 15/15 | 5/15 | 8/15 |
| Codex, `gpt-5.6-sol` | 5/15 | 9/15 | 15/15 | 14/15 |
| Agy, `gemini-3.7-flash-high` | 7/15 | 10/15 | 13/15 | 15/15 |
| **All** | **17/45** | **34/45** | **33/45** | **37/45** |

| Agent | Case | Control quality | tlgf quality | Control budget | tlgf budget | Control words | tlgf words | Word change | Control mannerisms | tlgf mannerisms | Control tokens | tlgf tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agy | addressable-action | 2/3 | 2/3 | 2/3 | 3/3 | 48 | 48 | +23% | 0 | 0 | 150960 | 78668 |
| agy | decision-blocker | 3/3 | 3/3 | 3/3 | 3/3 | 107 | 96 | -8% | 0 | 0 | 83125 | 71130 |
| agy | run-lineage | 2/3 | 2/3 | 3/3 | 3/3 | 145 | 146 | +1% | 0 | 0 | 110047 | 97083 |
| agy | stale-state | 0/3 | 2/3 | 2/3 | 3/3 | 176 | 99 | -44% | 0 | 0 | 124931 | 199253 |
| agy | useful-signal | 0/3 | 1/3 | 3/3 | 3/3 | 87 | 98 | +6% | 0 | 0 | 72543 | 87847 |
| claude | addressable-action | 0/3 | 3/3 | 0/3 | 0/3 | 506 | 145 | -71% | 0 | 0 | 3390 | 762 |
| claude | decision-blocker | 3/3 | 3/3 | 1/3 | 3/3 | 231 | 157 | -32% | 0 | 0 | 763 | 655 |
| claude | run-lineage | 1/3 | 3/3 | 1/3 | 0/3 | 248 | 184 | -13% | 0 | 0 | 2033 | 1191 |
| claude | stale-state | 1/3 | 3/3 | 0/3 | 2/3 | 288 | 195 | -30% | 0 | 0 | 2077 | 2366 |
| claude | useful-signal | 0/3 | 3/3 | 3/3 | 3/3 | 143 | 160 | +13% | 0 | 0 | 1204 | 1139 |
| codex | addressable-action | 1/3 | 0/3 | 3/3 | 2/3 | 55 | 87 | +48% | 0 | 0 | 42162 | 67330 |
| codex | decision-blocker | 0/3 | 3/3 | 3/3 | 3/3 | 61 | 96 | +62% | 0 | 0 | 41493 | 65464 |
| codex | run-lineage | 2/3 | 3/3 | 3/3 | 3/3 | 146 | 114 | -18% | 0 | 0 | 58350 | 67624 |
| codex | stale-state | 2/3 | 3/3 | 3/3 | 3/3 | 111 | 112 | +6% | 0 | 0 | 73293 | 67038 |
| codex | useful-signal | 0/3 | 0/3 | 3/3 | 3/3 | 47 | 78 | +66% | 0 | 0 | 42007 | 65397 |

What the run shows:

- With a natural prompt and no skill, the hosts mostly replayed the embedded frame on `B`, gave no revisit condition or parked lead, missed the stale-state conflict or its retry cost, and left the preliminary partner-north signal out of the status. TLGF answers resolved `B` in place, kept gamma outside the comparison, reported the mismatch and the recovered pass, surfaced the signal as preliminary, and put `⛔ Needs you` before the migration decision.
- Claude passed every TLGF gate. Codex refreshed the whole frame after executing `B` in all three repetitions, which the gate counts as a replay because classifying a result changes no state, and left the run name out of its `useful-signal` frame. Agy omitted the project from one breadcrumb twice, omitted alpha's score once, mutated the workspace once, and returned one empty answer.
- Reader-visible length moved both ways: Claude's TLGF answers were 13% to 71% shorter than its controls, Codex's were longer on three of five cases because its controls were terse, and Agy's were close to even except for `stale-state` (-44%). The mannerism lexicon matched nothing; a frame's compactness is a structural property, not a word-choice one.
- Host-reported tokens moved both ways within each host, so the benchmark makes no compute-cost claim.

### Model judges

`benchmarks/judge.py` judged the 44 complete pairs (the empty Agy answer left one case without a pair) with `claude-sonnet-5` and `gpt-5.6-sol` at medium reasoning effort, each pair in both positions, and graded every answer's coverage of the case's `semantic_facts`. The Claude judge hit a session limit part way through; the affected verdicts were redone after the limit reset, so every pair has both judges.

| Judge | TLGF preferred | Control preferred | Position-dependent |
| --- | ---: | ---: | ---: |
| Claude (`claude-sonnet-5`) | 17 | 19 | 8 |
| Codex (`gpt-5.6-sol`) | 27 | 11 | 6 |

The judges agreed on 27 pairs: TLGF preferred in 15, control in 11, position-dependent in 1. The two judges read the frame differently. Both scored TLGF higher on orientation (1.58 → 1.94 and 1.62 → 1.89), actionability (1.43 → 1.80 and 1.26 → 1.74), completeness, and accuracy, and both found TLGF answers to convey more of the expected facts (0.94 and 0.95 against 0.84 and 0.77). Both scored TLGF lower on natural tone (1.57 → 1.16 and 1.65 → 1.49): a labeled, numbered frame reads as less conversational than prose, and the Claude judge also scored it lower on traceability (1.73 → 1.33), consistent with frames that name fewer files than a control answer that lists everything it opened. The Claude judge's near-even preference reflects that trade-off; the Codex judge weighed orientation and actionability more.

So the model-judged evidence supports the claim TLGF makes — a returning user gets the right position, state, and next action more often — and not a claim that the frame reads more naturally than free prose. The full per-pair table is in `JUDGE.md` of the published run.

**Blinding caveat (found 2026-08-26).** Some Codex and Agy answers cite fixture files by absolute path, and in this run the path named the condition (`workspaces/<agent>/tlgf/…` against `…/control/…`). 15 of the 44 judged pairs (Codex 4, Agy 11) carried such a segment in at least one answer; the Claude pairs cite no absolute paths and were unaffected. The Codex judge's reasons quote such a path in a few pairs as a suspect citation, which is a length-and-style penalty rather than a condition lookup, but the verdicts for those 15 pairs can't be called blind. `judge.py` now replaces the condition directory with `CONDITION` before building a prompt, `BLIND_REVIEW.md` is generated the same way, and the deterministic gates are unaffected. Until the affected pairs are re-judged with neutral paths, treat the pairwise preferences as unblinded for them.

### Blind review

No human review was performed for this run. Scoring factual accuracy against the fixtures needs time with each fixture, and key factual elements are partially verified by the deterministic gates (exact run names, paths, numbers, frame structure, portable links) and by the judges' fact-coverage mode, subject to model-evaluation limits. The harness still writes a `BLIND_REVIEW.md` worksheet per run for anyone who wants to review pairs blind; the claims above rest on the deterministic gates and the two LLM judges.

The diagnostic runs that preceded this one, and every grader or skill change they caused, are recorded in [`docs/calibration-log.md`](docs/calibration-log.md). The adapter forward test is in [`docs/adapter-forward-test.md`](docs/adapter-forward-test.md).
