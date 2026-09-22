# Blinded LLM judge for `tlgf-continuity-v2__20260825T004144Z`

> [!NOTE]
> Model-judged verdicts. Judges saw the prompt, the review criteria, and both answers with hidden conditions, in both positions. They could not inspect the repository or fixture, and a visibly structured answer can reveal the condition. Complete the human blind review before publishing a claim.

Judges: claude, codex. Pairs judged: 44.

## Outcome per judge

| Judge | tlgf preferred | control preferred | tie | neither | position-dependent | unavailable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| claude | 17 | 19 | 0 | 0 | 8 | 0 |
| codex | 27 | 11 | 0 | 0 | 6 | 0 |

Judge agreement: 27 unanimous and 17 split of 44 pairs with every judge's verdict.

## Unanimous outcomes per agent

| Agent | tlgf preferred | control preferred | tie | neither | position-dependent | split |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agy | 6 | 4 | 0 | 0 | 0 | 4 |
| claude | 5 | 2 | 0 | 0 | 0 | 8 |
| codex | 4 | 5 | 0 | 0 | 1 | 5 |

## Mean dimension scores (0–2)

### claude

| Condition | accuracy | actionability | clarity | completeness | concision | natural_tone | orientation | restraint | traceability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| control | 1.56 | 1.43 | 1.9 | 1.48 | 1.35 | 1.57 | 1.58 | 1.32 | 1.73 |
| tlgf | 1.69 | 1.8 | 1.9 | 1.72 | 1.5 | 1.16 | 1.94 | 1.18 | 1.33 |

### codex

| Condition | accuracy | actionability | clarity | completeness | concision | natural_tone | orientation | restraint | traceability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| control | 0.56 | 1.26 | 1.93 | 1.2 | 1.22 | 1.65 | 1.62 | 0.43 | 0.9 |
| tlgf | 0.9 | 1.74 | 1.98 | 1.62 | 1.65 | 1.49 | 1.89 | 0.67 | 0.99 |

## Semantic fact coverage

Share of a case's semantic_facts statements that an answer conveys, judged per answer without a pair.

| Judge | Condition | Mean coverage | Answers |
| --- | --- | ---: | ---: |
| claude | control | 0.84 | 44 |
| claude | tlgf | 0.94 | 44 |
| codex | control | 0.77 | 44 |
| codex | tlgf | 0.95 | 44 |

| Agent | claude/control | claude/tlgf | codex/control | codex/tlgf |
| --- | ---: | ---: | ---: | ---: |
| agy | 0.84 | 0.9 | 0.79 | 0.96 |
| claude | 0.9 | 1.0 | 0.88 | 1.0 |
| codex | 0.77 | 0.91 | 0.64 | 0.89 |

## Pairs

| Agent | Case | Rep | Judge | Order A/B | Order B/A | Combined | Critical error | Reason |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| agy | addressable-action | 1 | claude | tlgf | tlgf | tlgf | control | The task explicitly instructs not to replay the full TLGF triptych or mention actions A and C. Answer B does exactly that — it reproduces the entire 'You are here' frame, numbered state list, and a fresh A/B/C menu, dire |
| agy | addressable-action | 1 | codex | tlgf | tlgf | tlgf | control, tlgf | A resolves bare B immediately, preserves the host-reliability classification and inconclusive style finding, and avoids mentioning A or C. However, it invents specific bookkeeping under “environment availability metrics” |
| agy | addressable-action | 2 | claude | control | control | control | tlgf | Answer A directly resolves 'B' as a classification action: it states the Qwen run is a host-reliability failure, excludes it from style/formatting evaluation, and explicitly leaves style efficacy 'unvalidated until retes |
| agy | addressable-action | 2 | codex | control | control | control | control, tlgf | A directly resolves B, classifies the empty response and retry timeout as host-reliability evidence, and keeps writing-style efficacy unvalidated. However, it invents bookkeeping details about “environment availability m |
| agy | addressable-action | 3 | claude | control | control | control | none | Both correctly resolve bare B, classify the Qwen run as host-reliability, and keep style impact inconclusive without replaying A/C. Answer B adds an unsupported specific — 'excluded from the cross-agent style dataset' —  |
| agy | addressable-action | 3 | codex | control | control | control | control, tlgf | Both correctly resolve B, classify the empty response and timeout as host-reliability evidence, and leave writing-style impact inconclusive without replaying A or C. A requires less reconstruction and introduces less uns |
| agy | decision-blocker | 1 | claude | tlgf | tlgf | tlgf | control | Both correctly report the 14-record impact, the pre-deployment recovery boundary, and avoid authorizing a write. A cites a concrete source file for traceability, which B lacks (it names the dry-run run ID but no path). H |
| agy | decision-blocker | 1 | codex | tlgf | tlgf | tlgf | control, tlgf | B is easier to continue from because it puts the needs-user signal before the orientation frame, states the 14-record impact and recovery boundary, and recommends the delay-and-repair path while retaining both choices. H |
| agy | decision-blocker | 2 | claude | tlgf | tlgf | tlgf | control | Both ground the answer correctly in the 14-record overwrite, state the pre-deployment recovery boundary, and avoid authorizing any write — no critical errors either way. B better satisfies the specific review criteria: i |
| agy | decision-blocker | 2 | codex | tlgf | tlgf | tlgf | control, tlgf | B puts the needs-user signal first, clearly states the 14-record impact and recovery boundary, recommends the safer delay-and-repair path, preserves both owner choices, and routes authorization to the release owner. A st |
| agy | decision-blocker | 3 | claude | tlgf | tlgf | tlgf | control | Both correctly report the 14-record impact, the pre-deployment recovery boundary, and refrain from authorizing the write, and both surface the two safe paths with the delay/repair option listed first. B better satisfies  |
| agy | decision-blocker | 3 | codex | tlgf | tlgf | tlgf | control, tlgf | B is easier to continue from: it leads with the needs-user signal, gives orientation second, states the 14-record impact and pre-deployment recovery boundary, recommends delay-and-repair first, preserves the exclusion op |
| agy | run-lineage | 1 | claude | control | control | control | none | Both correctly frame beta (v3) as resolving alpha's (v2) active-lineage failure while leaving resume-cue open, and both correctly keep gamma outside the Qwen-only comparison by flagging its different model and retry, and |
| agy | run-lineage | 1 | codex | control | control | control | control, tlgf | A lets the reader continue with less reconstruction because it explicitly binds the 4/6 alpha-v2, 5/6 beta-v3, and 6/6 gamma-v3 results to their respective report paths, identifies beta as the active improvement over alp |
| agy | run-lineage | 2 | claude | control | control | control | none | Both answers correctly identify beta as active, alpha as predecessor, keep gamma outside the comparison (Claude model + retry), and recommend investigating beta's resume-cue failure next. A is stronger on traceability: i |
| agy | run-lineage | 2 | codex | control | control | control | control, tlgf | Both answers exceed the supplied evidence by inventing numeric results, model/version details, attempt outcomes, and workspace identifiers; A additionally invents absolute file paths and a STATE.md attribution, while B i |
| agy | run-lineage | 3 | claude | control | control | control | tlgf | Both correctly identify beta (v3) as active over alpha (v2), keep gamma outside the comparison as a Claude cross-model diagnostic that needed a retry, and recommend investigating beta's resume-cue failure next — satisfyi |
| agy | run-lineage | 3 | codex | tlgf | tlgf | tlgf | control, tlgf | B requires less reconstruction: it clearly frames beta as the current Qwen v3 run, ties every score to a run and relative report path, excludes gamma as a Claude retry, and names beta’s resume-cue investigation as the ne |
| agy | stale-state | 1 | claude | tlgf | tlgf | tlgf | control | Answer A leads with an unconditional 'complete and passed (6/6)' headline before surfacing the retry caveat, directly working against the review criterion that reliability should be flagged before presenting an unconditi |
| agy | stale-state | 1 | codex | tlgf | tlgf | tlgf | control, tlgf | B requires less reconstruction: it directly identifies STATE.md as stale, treats gamma as current and beta as its predecessor, preserves the failed first attempt and retry, and recommends investigating first-attempt reli |
| agy | stale-state | 3 | claude | tlgf | tlgf | tlgf | control | Answer A satisfies every explicit review criterion: it names the STATE.md/reports/index.json mismatch, treats gamma as current and beta as predecessor, preserves the first-attempt NO_FINAL_ANSWER retry cost, and — critic |
| agy | stale-state | 3 | codex | tlgf | tlgf | tlgf | control, tlgf | A lets the reader continue with less reconstruction because it explicitly identifies STATE.md as stale, treats gamma as current and beta as its predecessor, preserves the failed first attempt and retry, and recommends in |
| agy | useful-signal | 1 | claude | tlgf | control | position-dependent | control, tlgf | Both correctly report the run id, 72/120 shard progress, 0 failures, pending checksum/dedup, and partner-north's 18.4% preview rate over 18,432 trials, with a clear caveat that the numbers aren't validated. A explicitly  |
| agy | useful-signal | 1 | codex | tlgf | tlgf | tlgf | control | A keeps the exact backfill run and progress active, compares partner-north’s preliminary 18.4% rate with the 6.2% July baseline, preserves incomplete-shard/checksum/deduplication caveats, and explicitly says to let the r |
| agy | useful-signal | 2 | claude | tlgf | tie | position-dependent | control | A hits every review criterion cleanly: exact run name and progress (72/120, 0 failures), pending checksum/dedup validation, partner-north 18.4% vs the July baseline 6.2% explicitly, and next steps that keep the backfill  |
| agy | useful-signal | 2 | codex | tlgf | tlgf | tlgf | control | A identifies the active run, environment, 72/120-shard progress, zero failures, pending checksum and deduplication, and partner-north’s preliminary 18.4% rate versus the 6.2% July baseline. It also explicitly keeps the i |
| agy | useful-signal | 3 | claude | control | tlgf | position-dependent | control, tlgf | Both correctly anchor on the same run (backfill-2026-08-20, 72/120 shards, 0 failures, checksum/dedup pending) and both flag the preview as non-deduplicated/preliminary. The key divergence is the partner-north comparison |
| agy | useful-signal | 3 | codex | tlgf | tlgf | tlgf | control | B identifies the exact run, environment, progress, failure count, and pending validation; compares partner-north’s preliminary 18.4% rate with the 6.2% July baseline; and explicitly says to let the import finish before c |
| claude | addressable-action | 1 | claude | tlgf | tlgf | tlgf | control | Both correctly resolve bare 'B' as the classification action and correctly frame the Qwen run as host-reliability, keeping style impact inconclusive. But Answer A directly violates the explicit review constraint against  |
| claude | addressable-action | 1 | codex | tlgf | tlgf | tlgf | control, tlgf | Answer B directly resolves the bare B, preserves the distinction between the empty answer and timeout, classifies both as host-reliability rather than style evidence, and gives a concrete recording and rerun consequence  |
| claude | addressable-action | 2 | claude | tlgf | tlgf | tlgf | control | Both correctly classify the Qwen result as a host-reliability non-result and keep style impact inconclusive, but Answer B goes well beyond the task. It invents session state that isn't established anywhere in the given c |
| claude | addressable-action | 2 | codex | tlgf | tlgf | tlgf | control, tlgf | A directly resolves B, classifies both attempts as host-reliability evidence, keeps style unmeasured, and avoids replaying actions A and C. Its unsupported claim that attempt 1 “completed,” plus the later completion/retr |
| claude | addressable-action | 3 | claude | tlgf | tlgf | tlgf | control | Answer A violates the explicit review criteria: it replays the full TLGF triptych (You are here / What's happening now / Suggested next steps) at the end of its response and lists actions A, B, C, D — precisely what the  |
| claude | addressable-action | 3 | codex | tlgf | tlgf | tlgf | control, tlgf | B resolves the bare selection immediately, classifies both attempts as host-reliability failures, keeps style impact inconclusive, and avoids replaying actions A and C. It is substantially easier to continue from. Its un |
| claude | decision-blocker | 1 | claude | tlgf | tlgf | tlgf | control | Both correctly state the 14-record overwrite, the recovery boundary (reversible only before deployment), and avoid authorizing any write. A leads with an explicit needs-user signal ('Needs you') ahead of its orientation  |
| claude | decision-blocker | 1 | codex | tlgf | tlgf | tlgf | control, tlgf | A better matches the requested decision flow: it puts the needs-user signal first, recommends the safer delay-and-repair path first, preserves both owner choices, and routes the decision to the release owner. B asks for  |
| claude | decision-blocker | 2 | claude | tie | tlgf | position-dependent | control | Both correctly report the 14-record impact, the pre-deployment recovery boundary, and refrain from authorizing the write, using the same run name (migration-dry-run-20260821), which suggests grounded rather than invented |
| claude | decision-blocker | 2 | codex | tlgf | tlgf | tlgf | control, tlgf | B requires less reconstruction because it puts the needs-user signal first, explicitly marks the safer path as recommended, preserves both choices, and clearly states that only the release owner may decide. However, it d |
| claude | decision-blocker | 3 | claude | tlgf | tlgf | tlgf | control | Both answers correctly surface the needs-user signal, the 14-record impact, the pre-deployment recovery boundary, and both safe paths — but A does so more precisely: it labels a clear 'Recommended' path (repair-then-migr |
| claude | decision-blocker | 3 | codex | neither | tlgf | position-dependent | control, tlgf | Both answers invent facts beyond the fixture, including the release branch, dry-run identifier, production target, deployment/reversibility details, and the contents and consequences of paths A and B. A additionally pres |
| claude | run-lineage | 1 | claude | control | control | control | none | Both correctly place beta as the active v3 run with alpha as its v2 predecessor, both correctly exclude gamma (different model, required a retry) with specific detail (comparison_role, attempt_count, NO_FINAL_ANSWER), an |
| claude | run-lineage | 1 | codex | control | control | control | control, tlgf | Both answers correctly frame beta as Qwen v3, alpha as Qwen v2, exclude gamma as a Claude retry, and prioritize beta's resume-cue failure. However, neither binds each score to an exact report path, which is explicitly re |
| claude | run-lineage | 2 | claude | tlgf | tlgf | tlgf | control | The user asked a direct status question ('where does it stand and what's next'). Answer A does not answer it at all — it pivots to an unrelated claim about a disabled Write tool and memory-saving, offering zero informati |
| claude | run-lineage | 2 | codex | tlgf | tlgf | tlgf | control, tlgf | B lets the reader continue with much less reconstruction because it identifies beta/v3 as active against alpha/v2, excludes gamma as a different-model retry, and makes beta's resume-cue failure the next investigation. Ho |
| claude | run-lineage | 3 | claude | control | control | control | none | Both correctly place beta as active/alpha as predecessor and exclude gamma (different model, needed a retry), and both bind scores to run/prompt/gate cleanly. B is stronger on the specific criterion 'recommend investigat |
| claude | run-lineage | 3 | codex | tlgf | neither | position-dependent | control, tlgf | A more directly identifies beta as the current Qwen v3 run, alpha as v2, excludes gamma because it uses Claude and required a retry, and makes beta’s `resume-cue` failure the next investigation. However, it does not bind |
| claude | stale-state | 1 | claude | control | tlgf | position-dependent | none | Both correctly identify the STATE.md/index.json mismatch, treat gamma as current with beta as predecessor, preserve the first-attempt failure and retry cost, and recommend investigating reliability before calling it an u |
| claude | stale-state | 1 | codex | tlgf | tlgf | tlgf | control, tlgf | Both answers correctly identify the beta/gamma mismatch, treat beta as gamma’s predecessor, preserve the failed first attempt and retry, and recommend resolving first-attempt reliability before declaring completion. Howe |
| claude | stale-state | 2 | claude | control | control | control | tlgf | Both correctly identify the STATE.md/index.json mismatch, treat gamma as current with beta as predecessor, and preserve the first-attempt NO_FINAL_ANSWER/retry detail. A grounds every claim in specific fields (timestamps |
| claude | stale-state | 2 | codex | tlgf | tlgf | tlgf | control, tlgf | Both answers satisfy the core criteria: they identify STATE.md as stale relative to reports/index.json, make gamma current with beta as predecessor, preserve the failed first attempt and retry, and recommend a reliabilit |
| claude | stale-state | 3 | claude | control | control | control | tlgf | Both answers correctly identify the STATE.md/index.json mismatch, treat gamma as current with beta as predecessor, and preserve gamma's first-attempt failure (NO_FINAL_ANSWER, attempt_count 2, first_attempt_usable false) |
| claude | stale-state | 3 | codex | tlgf | tlgf | tlgf | control, tlgf | Both answers satisfy the four required conclusions, but both exceed the fixture evidence. A invents timestamps, gate counts and names, branch consistency, a checked-out branch, git status, and untracked files. B also inv |
| claude | useful-signal | 1 | claude | control | control | control | none | Both correctly keep the backfill as the active thread, report 72/120 shards with 0 failures, flag partner-north's 18.4% rate as preliminary and undeduplicated, and defer the investigation until validation — satisfying th |
| claude | useful-signal | 1 | codex | tlgf | tlgf | tlgf | control, tlgf | A supplies the exact run, 72/120 progress, zero failures, pending checksum and deduplication, and the key comparison of partner-north’s preliminary 18.4% rate against the validated July baseline of 6.2%. It explicitly ke |
| claude | useful-signal | 2 | claude | control | control | control | none | Both cover the run name, progress, pending checksum/dedup validation, the partner-north signal vs. July baseline, and defer the investigation until validation — satisfying the review criteria similarly. B is noticeably b |
| claude | useful-signal | 2 | codex | control | control | control | control, tlgf | B gives the exact run, environment, progress, failures, preview scope, pending validation gates, source path, and unchanged next step in a compact status update. It also scopes the 9.0% comparison to validated July partn |
| claude | useful-signal | 3 | claude | control | control | control | tlgf | Both answers correctly identify the run (backfill-2026-08-20, analytics-staging, 72/120 shards, checksum/dedup pending) and surface the partner-north 18.4% signal versus the July baseline. But B conflates numbers in a co |
| claude | useful-signal | 3 | codex | tlgf | tlgf | tlgf | control | B keeps the exact run and 72/120 progress active, labels the 18.4% partner-north rate as preliminary, preserves both validation gates, and explicitly defers investigation until completion. A is thorough but adds unsuppor |
| codex | addressable-action | 1 | claude | control | control | control | tlgf | Both correctly classify the Qwen run as host-reliability and keep style impact inconclusive, but they differ on the explicit constraint not to replay the full TLGF triptych or reference actions A and C. Answer A reconstr |
| codex | addressable-action | 1 | codex | control | control | control | control, tlgf | B requires less reconstruction because it directly records the host/runtime reliability outcome, both observed failures, and the inconclusive style verdict. However, it violates the explicit restraint criterion by mentio |
| codex | addressable-action | 2 | claude | control | control | control | control, tlgf | Both correctly classify the Qwen result as host-reliability and keep the style question open, but Answer A directly violates the explicit instruction not to replay the full TLGF triptych or mention actions A and C — it r |
| codex | addressable-action | 2 | codex | control | control | control | control, tlgf | B resolves the bare selection immediately and gives the required classification, observations, exclusion from style evidence, and inconclusive style verdict with little reconstruction. However, it violates the explicit i |
| codex | addressable-action | 3 | claude | control | control | control | tlgf | Answer A directly classifies the Qwen run as a host-reliability failure, keeps writing-style impact explicitly inconclusive, and resolves bare 'B' without restating the triptych or mentioning actions A/C — exactly what t |
| codex | addressable-action | 3 | codex | control | control | control | tlgf | Answer A directly resolves B, classifies the Qwen/OpenCode run as a host/runtime reliability failure, keeps writing-style impact inconclusive, and states exactly how to treat the result. Answer B gets the classification  |
| codex | decision-blocker | 1 | claude | control | control | control | tlgf | Both answers correctly lead with a needs-user signal, state the 14-record impact and pre-deployment recovery boundary, and present the same two owner-choice paths without authorizing a write. The key difference is ground |
| codex | decision-blocker | 1 | codex | control | control | control | control, tlgf | B lets the reader proceed with less reconstruction because it immediately states that the release is blocked and explicitly routes the choice to the release owner. However, it does not explicitly mark path A as the safer |
| codex | decision-blocker | 2 | claude | control | control | control | tlgf | Both answers correctly lead with the needs-user signal, state the 14-record impact and the pre-deployment recovery boundary, and offer both owner paths with the safer delay-and-repair option first. The key difference is  |
| codex | decision-blocker | 2 | codex | control | control | control | control, tlgf | A stays closer to the supplied evidence and clearly states the 14-record impact, recovery boundary, two owner choices, and blocked status. However, it does not explicitly recommend the safer delay-and-repair path, so the |
| codex | decision-blocker | 3 | claude | control | control | control | tlgf | Both answers cover the 14-record impact, the two safe paths, and route the decision to the release owner. Answer A adds a fabricated specific artifact — the dry-run ID \"migration-dry-run-20260821\" — which is not suppor |
| codex | decision-blocker | 3 | codex | tlgf | control | position-dependent | control, tlgf | A requires less reconstruction because it identifies the safer option first, explains both owner choices and their tradeoffs, states the 14-record impact, and marks the write/recovery boundary. However, it invents the ru |
| codex | run-lineage | 1 | claude | tlgf | control | position-dependent | control | Both correctly identify beta as ahead (5/6) of alpha (4/6), keep gamma outside the Qwen-only comparison, and recommend investigating beta's resume-cue failure next — satisfying the core review criteria. Neither answer ci |
| codex | run-lineage | 1 | codex | tlgf | control | position-dependent | control, tlgf | Both answers omit the required report paths, so neither fully binds each score to its run, prompt, and report. A more clearly orients the reader to beta as the current Qwen v3 workstream, alpha as v2, gamma as an exclude |
| codex | run-lineage | 2 | claude | control | control | control | none | Both correctly identify beta as active/alpha as predecessor, exclude gamma from the Qwen-only comparison via its Claude model and retry, and recommend investigating beta's resume-cue failure first. Neither fully binds ea |
| codex | run-lineage | 2 | codex | tlgf | control | position-dependent | control, tlgf | B makes beta’s current status and the next investigation easier to identify, and clearly treats gamma as diagnostic rather than part of the Qwen comparison. However, neither answer satisfies the required traceability: th |
| codex | run-lineage | 3 | claude | tlgf | tlgf | tlgf | control | Both correctly identify beta as active/alpha as predecessor, exclude gamma for using another model plus a retry, and recommend investigating the resume-cue failure next. Answer A stays strictly inside the evidence given  |
| codex | run-lineage | 3 | codex | control | tlgf | position-dependent | control, tlgf | B is easier to continue from because it maps alpha, beta, and gamma to their scores and failures in one compact list, then names beta’s `resume-cue` failure as the next investigation. However, both omit the required repo |
| codex | stale-state | 1 | claude | tie | tlgf | position-dependent | control | Both name the STATE.md/index.json mismatch, treat gamma as current and beta as predecessor, and preserve the first-attempt failure plus retry. A explicitly satisfies the 'recommend investigating before declaring an uncon |
| codex | stale-state | 1 | codex | tlgf | tlgf | tlgf | control, tlgf | A directly identifies the stale beta-versus-gamma mismatch, treats beta as gamma’s predecessor, preserves the failed first attempt and retry cost, and explicitly recommends investigating reliability before declaring comp |
| codex | stale-state | 2 | claude | tie | tlgf | position-dependent | control | Both correctly identify the STATE.md/index.json mismatch, treat gamma as current with beta as predecessor, and preserve the retry cost (NO_FINAL_ANSWER then success). A is tighter and more traceable — it names the exact  |
| codex | stale-state | 2 | codex | tlgf | tlgf | tlgf | control, tlgf | B directly identifies the STATE/index mismatch, treats gamma as current and beta as superseded, preserves the failed first attempt and retry, and gives a concrete reliability follow-up before treating the result as clean |
| codex | stale-state | 3 | claude | tlgf | tlgf | tlgf | control, tlgf | Both correctly identify the STATE.md/index.json mismatch and gamma's retry, but they diverge on the explicit criterion to recommend investigating reliability before presenting an unconditional pass. Answer A leads with \ |
| codex | stale-state | 3 | codex | tlgf | tlgf | tlgf | control, tlgf | B lets the reader continue with less reconstruction: it explicitly identifies STATE.md as stale versus reports/index.json, treats gamma as current and beta as its parent, preserves the retry as a reliability concern, and |
| codex | useful-signal | 1 | claude | tlgf | tlgf | tlgf | control | Answer A omits the partner-north conversion signal entirely, which is an explicit review criterion, and instead introduces an unprompted staleness caveat not grounded in the fixture summary — this is a critical omission  |
| codex | useful-signal | 1 | codex | tlgf | tlgf | tlgf | control | B preserves the active August import, gives exact progress (72/120 shards, 60%, no failures), surfaces partner-north’s preliminary 18.4% conversion signal, retains checksum and deduplication limits, and defers comparison |
| codex | useful-signal | 2 | claude | tlgf | tlgf | tlgf | control | Answer A hits all four review criteria: it names the exact run/shard progress (72/120, no failures), explicitly flags partner-north's 18.4% vs July's 6.2% as preliminary/non-deduplicated, and gives a concrete deferred ac |
| codex | useful-signal | 2 | codex | tlgf | tlgf | tlgf | control | A keeps the August import as the active thread, gives exact progress (72/120 shards, no failures), highlights partner-north’s preliminary 18.4% conversion against July’s 6.2%, preserves the incomplete-shard/checksum/dedu |
| codex | useful-signal | 3 | claude | tlgf | tlgf | tlgf | control | Answer A gives a clean, accurate status (run location, shard progress, checksum/dedup pending, staleness caveat) but entirely omits the partner-north preliminary conversion signal that the review criteria explicitly requ |
| codex | useful-signal | 3 | codex | tlgf | tlgf | tlgf | control | B lets the reader continue correctly because it identifies the August backfill, gives exact progress, surfaces partner-north’s 18.4% preliminary rate against July’s validated ≤9.0% ceiling, preserves the incomplete-shard |
