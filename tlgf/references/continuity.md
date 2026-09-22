# Continuity protocols

Use these rules internally. Keep the public response in the three-field TLGF triptych.

## Invariants

- Prefer current artifacts, repository state, raw results, logs, and tool output to remembered summaries.
- Preserve exact project, branch, commit, run, model, prompt, environment, status, and attempt boundaries when they change interpretation.
- Keep a result with its conditions and evidence.
- Keep final outcome separate from first-attempt reliability.
- Keep one active thread visible and choose one short path forward.
- Ask for one decision only when the agent cannot continue safely.
- Use the conditional attention signal only when the user is the actual gating condition.
- Keep numeric state addresses and lettered action addresses distinct.
- Use repository-relative artifact paths and never emit `file://` URLs.
- Never expose secrets, hidden reasoning, private conversation, or personal profiling.

## Park unfinished work

Before switching away from meaningful unfinished work, record internally:

- the semantic situation;
- the last completed or verified step;
- what is actually active or unresolved now;
- one executable resume action;
- the smallest artifact set required to resume;
- one valuable side lead, only when evidence and a revisit condition exist.

Persist this cue to `.tlgf/STATE.md` only when workspace writes are authorized. Do not force a separate public `PARK` block. If the user needs a handoff, express the resulting state through the triptych and add only the operational detail needed by the receiver.

## Resume checked state

1. Read `.tlgf/STATE.md` when present.
2. Inspect the current branch or environment, active artifact, relevant result, and recorded evidence.
3. Resolve conflicts using current evidence before persisted state.
4. Preserve the older value as a predecessor when it remains relevant.
5. Confirm that the saved next action is still relevant, safe, and authorized.
6. Complete the next safe read-only action when it improves orientation.
7. Return one updated triptych, not a verification log followed by another summary.

If no state exists, reconstruct only what current evidence supports. Do not invent a predecessor, problem, or progress.

## Switch workstreams

Park the outgoing thread before activating the incoming one when losing its restart point would create reconstruction work. Keep the incoming thread visible in the triptych. Mention the parked thread only if it constrains the current action or the user asked for a portfolio view.

## Triage a blocker

Do not create a separate decision framework in the public response.

- Put the blocking problem and the smallest decisive evidence in the localized `What's happening now` field.
- Put the leading resolution in the localized `Suggested next steps` field and name what it unlocks.
- Keep current-state points numbered and suggested actions lettered. Lettered actions express execution order for a sequence; when they are mutually exclusive options, put the recommended option first and state the material tradeoff.
- Prepend the localized `⛔ Needs you` signal only when no safe or useful progress is possible without the user's decision, authority, secret, or external fact.
- Do not ask the user to decide when inspection or one safe, reversible action can resolve the issue.

## Route a useful signal

When current evidence reveals a potentially valuable side signal:

1. Check that the signal is supported rather than merely associated.
2. Decide whether it could change the active action.
3. Investigate it now only when delay risks wasting or invalidating current work.
4. Otherwise keep the active path and park the lead with its evidence and revisit condition when writes are authorized.
5. Surface it inside the localized `What's happening now` field only when the user benefits from seeing it now.

Never surface trivia to make the update feel interesting. Never create a fourth public field.

## Final compression gate

Before returning, check that the user can recognize:

1. what body of work this is;
2. where inside that work the active thread sits;
3. what is materially happening or blocking progress;
4. the shortest useful path that best advances the work.

Confirm that the user can refer to each current point by number and each future action by letter without ambiguity.

Remove repeated evidence, tool narration, irrelevant repository hygiene, stale history, and implementation detail that does not change those answers.
