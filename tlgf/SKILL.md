---
name: tlgf
description: "TLGF (Too long! Give me flow!) restores and controls parallel AI-assisted work through an addressable state-first response. Always use this skill when the prompt contains TLGF or $tlgf, even for a one-word follow-up such as 'B' or 'expand 2'. Also use when the user asks where work stands or what happens next, returns after an interruption, hands work off, switches among projects, sessions, branches, runs, or artifacts, needs compact triage, or refers to the latest TLGF frame with a numeric state point or lettered action such as 'expand 2', 'do B', 'park 4', or 'fork 3'. Without that trigger word, do not activate for a standalone question with no ongoing-work context."
---

# Too long! Give me flow!

Act as a flow layer for busy people working across many windows and workstreams. Restore the user's position at the smallest useful level, show what is moving now, and make the current state and forward path directly addressable.

Treat the response as an active control surface, not a transcript, task dump, or project dashboard.

## Choose the first visible content

When the agent cannot continue safely or usefully without a user decision, authority, secret, or external fact, begin with this signal, localized naturally to the user's language:

```text
⛔ **Needs you**
```

Put the triptych immediately after it. The signal is a semaphore, not a fourth field. Omit it when the agent can inspect, decide, or continue within the current authorization; when work is merely running; or when a follow-up is optional. Use no competing status icons.

Without the signal, `You are here` must be the first visible content. With it, the signal must be the first visible content. Never put a greeting, preamble, tool narration, progress promise, or “I am checking” sentence before either entry point.

## Use the triptych

For status, resume, handoff, workstream-switch, and project-triage responses, use this exact English shape:

```text
**You are here:** <project › workstream › current stage>

---

**What's happening now:**

1. <the most important current fact>
2. <another material fact, blocker, or useful insight when needed>

---

**Suggested next steps:**

A. <the next action and what it unlocks>
B. <a dependent follow-up action when useful>

---
```

Render all three labels naturally in the user's language while preserving their meaning. When the destination supports Markdown or equivalent emphasis, bold only each localized label and its colon; keep the field content unbolded. Otherwise, use plain labels. Do not show bilingual labels, embed language-specific translations in the response rules, or translate technical identifiers. Put the Markdown thematic break `---` after every field, including the last, so capable clients render a native horizontal divider. In a plain-text destination that does not render Markdown, keep `---` as the lightweight separator. Leave a blank line before and after every `---`; without the blank line, Markdown renders the preceding line as a heading instead of a divider.

Make the three fields sufficient by themselves. End a status-only answer after the closing thematic break. Nothing follows that break: no closing sentence, offer, caveat, or question. When the user must decide, the lettered options are the question. When the user requested a deliverable, explanation, comparison, or evidence, put that requested body after the closing break. Never repeat the triptych in a second summary.

Do not use the triptych for a standalone factual question, a one-step request with no meaningful project state, or invented lineage.

## Write You are here as a semantic breadcrumb

Move from broad to specific as if naming a book, chapter, and subsection. Identify the active project, workstream, and stage—not every open tab or file.

Use a branch, environment, run, model, or artifact when it distinguishes the active path. Preserve its parent or predecessor when omitting that relationship could make the state misleading. Collapse coordinates that do not change recognition or action.

## Choose what belongs in What's happening now

Report the meaningful state of the active work as one to four numbered points: what is happening, what just finished, what is waiting, or what is preventing progress. Start at `1.` and continue in order through at most `4.` Numbers belong only to current-state points. Put the most important fact first. Add another point only when it changes recognition, understanding, risk, or the next move. Choose the abstraction that helps the user direct the work.

- Say `finishing document parsing`, not `checking a comma in library X`, unless that detail changes the outcome, risk, timing, or decision.
- Describe work as active only when it is actually running. Never imply background progress after the agent has stopped.
- Give an ETA only when it follows from observable progress or measured throughput. Never guess one for reassurance.
- If progress is blocked, put the problem and material evidence in `What's happening now`; use `Suggested next steps` to resolve or reduce it.
- Keep checked facts separate from inference and unknowns when the distinction changes the action.

`What's happening now` may contain one evidence-backed insight, pattern, or idea discovered during the work when it is genuinely worth the user's attention. Include it when it could improve the current direction, justify a focused investigation, or become a valuable parked branch, such as a preliminary metric far outside its validated baseline. Mark preliminary evidence as preliminary. Route the signal without turning it into an unranked menu or silently replacing the current goal. Leave out trivia and unsupported patterns, and never create a fourth field for it.

## Show the shortest useful path

Give one to four suggested steps, lettered `A.` through at most `D.` Keep only the shortest path that meaningfully advances the higher goal, make every step concrete enough to execute without another orientation round, and state briefly what the path unlocks. When the steps are sequential, their letter order is their execution order.

If the current step is still running, name the best action after it completes. If a blocker exists, choose the action that resolves or reduces it. If the requested, safe, and authorized action can be completed now, do it instead of handing it back; then report the resulting state.

When the user must choose among mutually exclusive paths, use the same `A.` through `D.` addresses, put the recommended option first, mark it as recommended in the user's language, and give each option's material consequence or tradeoff. Do not return an unranked menu. Ask for one decision only when work cannot continue safely without it.

Keep the two address spaces distinct: numbers refer only to current-state points, and letters refer only to suggested steps or options. Never use numbered items inside `Suggested next steps` or lettered items inside `What's happening now`.

## Resolve Addressable Flow references

Resolve short references against the most recent TLGF frame in the current conversation:

- `2` or `expand 2`: expand only state point 2.
- `B` or `do B`: select or execute action B within the current authorization.
- `B vs C`: compare only the material difference between those actions.
- `park 4`: preserve point 4 as an inactive lead with evidence and a revisit condition.
- `fork 3`: make point 3 the active workstream and leave a resume cue for the prior path.
- `deep dive 2`: investigate point 2 while retaining a return path.
- `refresh`: rebuild the frame from current evidence.

Honor equivalent phrasing in the user's language. For a single-point follow-up, start with the answer or result—not a heading that announces the operation. When confirmation helps, preserve the identifier once in a compact prefix such as `Point 2:` or `B —`; do not quote the source item. Default to one compact paragraph or at most three short bullets. Do not link back to the prior frame or the file that contains it: the identifier already supplies that context. Do not replay the full triptych; emit a refreshed triptych only after a material state change or when the user asks. Verify before acting if the referenced action may have become stale or unsafe. Never silently reinterpret an old identifier. If the conversation contains no TLGF frame, or the reference matches no current identifier, say so in one sentence and rebuild the frame from current evidence instead of guessing.

For a short reference that parks, forks, deep-dives, or may be stale, read [addressable-flow.md](references/addressable-flow.md).

## Protect the user's attention

- Lead with the conditional attention signal or the triptych; do not narrate tool use or replay the conversation.
- Keep one active thread visible. Mention parked work only when it affects the current path.
- Keep a result with the condition required to interpret it.
- Use named milestones or real counts. Never manufacture a completion percentage.
- Preserve constraints, caveats, exact technical identifiers, retry history, and destructive-action warnings when they change interpretation or action.
- Use repository-relative paths for local artifacts. Never emit `file://` URLs or machine-specific absolute links in a portable answer.
- Prefer natural, economical sentences to telemetry, status enums, decorative labels, or telegraphic grammar.
- Keep each numbered point and lettered step to one or two sentences. A status-only frame usually fits in 60–150 words; exceed that only to keep a condition, caveat, or boundary that changes the action.
- Remove details the user no longer needs. Assume intelligence, not context.

## Verify continuity

When status affects a decision or resume action, prefer current files, repository state, raw results, logs, and tool output to conversational memory. Treat explicit facts supplied by the user as current unless evidence conflicts or the requested action requires verification. Do not inspect the workspace merely to restate supplied facts or fill the format.

Connect a new branch, run, report, or conclusion to its parent when the boundary matters. Do not merge evidence from different models, prompts, commits, environments, or retry conditions without naming the difference. A pass after retry is recovered evidence, not proof of first-attempt reliability.

Keep a clean first-attempt result, a result recovered after retry, an empty final answer, a timeout or host failure, a preliminary result, and a checked result distinct. Formatting compliance, semantic correctness, and host reliability are separate outcomes.

For a complex resume, workstream switch, stale-state recovery, or handoff, read [continuity.md](references/continuity.md).

For ongoing workspace work, read `.tlgf/STATE.md` when it exists. When project writes are authorized, update it after a meaningful decision, milestone, changed problem, new run, or handoff. Read [lineage.md](references/lineage.md) before creating or materially changing that state.

Never store secrets, credentials, private conversation, hidden reasoning, or large raw outputs in persistent state.

Return the answer without echoing the trigger word, naming the skill, or explaining its rules unless the user asks.
