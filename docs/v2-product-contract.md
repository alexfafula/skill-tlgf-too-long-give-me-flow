# TLGF V2 product contract

Status: implemented and forward-tested on Agy; Qwen/OpenCode host reliability remains unresolved

**TLGF — Too long! Give me flow!** turns an oriented AI response into an addressable control surface for parallel work.

V1 answers three questions: where am I, what is happening, and what should happen next. V2 keeps that triptych and adds four capabilities without adding permanent public sections:

1. addressable progressive disclosure;
2. one conditional attention signal;
3. evidence-bound semantic state;
4. portable enforcement across agent hosts.

The V2 promise is:

> Glance to regain position. Point to the exact state. Act without reconstructing the thread.

## Public interface

Use the localized equivalent of this shape for project orientation, status, resume, handoff, workstream switching, and decision triage:

```text
⛔ **Needs you**

**You are here:** project › workstream › current stage

---

**What's happening now:**

1. the most important current fact
2. another material fact, blocker, or useful insight when needed

---

**Suggested next steps:**

A. the next action and what it unlocks
B. a dependent action or material alternative when needed

---
```

The `Needs you` signal is conditional. Omit it, including its blank line, unless the agent cannot continue safely or usefully without a user action or decision. It is a semaphore, not a fourth field.

Without the signal, `You are here` is the first visible content. With the signal, `Needs you` is the first visible content and `You are here` immediately follows. Do not place a preamble, tool narration, progress promise, or greeting before either entry point.

Every `---` has a blank line before and after it, so Markdown renders a divider rather than promoting the preceding line to a heading. Each numbered point and lettered step is one or two sentences; a status-only frame usually fits in 60–150 words and exceeds that only to keep a condition, caveat, or boundary that changes the action.

## Semantic breadcrumb

`You are here` identifies the project, workstream, and current stage like a book title, chapter, and subsection. It is semantic rather than a duplicate status line.

Include a branch, environment, run, model, or artifact only when it distinguishes the active path or changes how the state must be interpreted. Preserve a relevant predecessor when hiding it would make the current result misleading.

## Numeric state addresses

`What's happening now` contains one to four points numbered continuously from `1.`. Numbers are reserved for current-state observations.

Order points by their value to the user's next judgment. Include a point only when it changes at least one of these:

- recognition of the active work;
- understanding of the result;
- risk or reliability;
- the next action or decision.

Keep a result beside the condition needed to interpret it. For example, keep the run, model, retry status, evidence limit, or source artifact in the same point as the conclusion it qualifies.

An evidence-backed side insight may occupy one numbered point when it could improve the active direction or become a valuable parked branch. Mark preliminary evidence as preliminary. Do not add an insight merely to make the panel interesting.

## Lettered action addresses

`Suggested next steps` contains one to four actions lettered continuously from `A.`. Letters are reserved for future actions or mutually exclusive options.

For a sequence, letter order is execution order. For a real choice, put the recommended option first, mark it as recommended in the user's language, and state the material consequence or tradeoff of each option.

If the agent can safely perform an authorized action now, perform it and report the resulting state instead of handing the action back to the user.

## Addressable Flow grammar

Resolve a short reference against the most recent TLGF frame in the current conversation.

| User reference | Required behavior |
| --- | --- |
| `2` or `expand 2` | Expand current-state point 2 without replaying unrelated points. |
| `B` or `do B` | Select or execute action B within the existing authorization boundary. |
| `B vs C` | Compare only the material difference between actions B and C. |
| `park 4` | Preserve point 4 as an inactive lead with evidence and a revisit condition. |
| `fork 3` | Make point 3 the active workstream and leave a resume cue for the prior path. |
| `deep dive 2` | Investigate point 2 while retaining a clear return path to the current goal. |
| `refresh` | Rebuild the frame from current evidence. |

Natural-language equivalents in the user's language have the same meaning. The grammar is an interaction shortcut, not a command syntax the user must memorize.

When confirmation helps, preserve the referenced identifier once with a compact prefix such as `Point 2:` or `B —`. Start with the answer or result, not a heading that announces the operation. Default to one compact paragraph or at most three short bullets. Do not quote the source item or link back to the prior frame or its source file. Do not emit the full triptych merely because the user asked to expand one point. Emit a refreshed triptych only after a material state change or when the user asks for it.

If a short reference could reasonably target more than one frame, or the referenced action became unsafe after the frame was shown, verify the current state before acting. Never silently reinterpret an old `B` as a new action.

Frame addresses are conversation-local. Persistent state stores semantic resume cues, not globally unique numeric or letter identifiers. When no frame exists in the conversation, or a reference matches no current identifier, the agent says so in one sentence and rebuilds the frame from current evidence instead of guessing; after a resume, it emits one fresh frame before honoring numeric or lettered references.

The response never echoes the trigger word, names the skill, or explains its rules unless the user asks.

## Conditional attention signal

Use `⛔ Needs you` only when the user's intervention is the actual gating condition.

Use it when:

- a material decision cannot be made safely by the agent;
- required authority is missing;
- a secret or external fact must come from the user;
- proceeding would cross a destructive or irreversible boundary without approval.

Do not use it when:

- the agent can resolve the problem through safe inspection;
- authorized work is still running;
- the task completed and the next action is merely optional;
- the model wants reassurance or permission to continue ordinary in-scope work.

Use no competing status icons in the triptych. The signal must remain the single exceptional visual feature across many windows.

## Evidence and reliability boundaries

Prefer current raw artifacts, repository state, logs, and tool output when status affects a decision or resume action. Treat explicit user-supplied current facts as evidence unless they conflict or the requested action requires verification.

Keep these states distinct:

- clean first-attempt result;
- result recovered after retry;
- empty or missing final answer;
- timeout or host failure;
- preliminary result awaiting validation;
- checked result.

Formatting compliance, semantic correctness, and host reliability are separate outcomes. A well-formed answer can still be wrong; a host that returns no answer cannot be graded for style.

Use repository-relative paths for local artifacts. Never emit `file://` URLs or machine-specific absolute links in a portable answer.

## Progressive disclosure

The triptych is the orientation layer. A status-only answer ends after its closing thematic break.

When the user requests a deliverable, explanation, comparison, or evidence, place the compact triptych first and the requested body after the closing break. Do not repeat the triptych as a summary at the end.

When the user references a single number or letter, answer only that reference unless the state changed materially. This is the primary V2 mechanism for reducing reconstruction and avoiding redundant context.

## Continuity engine

Keep PARK, RESUME, stale-state recovery, retry lineage, and useful-signal routing behind the public triptych.

- Before a meaningful workstream switch, leave a ready-to-resume cue.
- On resume, treat persisted state as a retrieval cue rather than a source of truth.
- Resolve conflicts in favor of current evidence.
- Keep one active thread visible and parked work collapsed.
- Update `.tlgf/STATE.md` only after meaningful transitions when project writes are authorized.

## Portable delivery

V2 has one semantic core and host-specific adapters:

1. `tlgf/SKILL.md` provides explicit and intent-based activation.
2. A Claude Code output style applies state-first behavior without relying on skill triggering.
3. An `AGENTS.md`-compatible instruction block provides a portable fallback for Codex, Agy, OpenCode, and other agents.

Adapters may change packaging and instruction priority. They must not change the public contract.

## Research-to-rule map

The cited research informs the design; it did not test TLGF.

| Research input | V2 design inference | Testable implementation rule |
| --- | --- | --- |
| Endsley's situation-awareness levels | Restore perception, comprehension, and near-future projection in a stable order. | Breadcrumb → numbered semantic state → lettered forward actions. |
| Altmann and Trafton's goal-resumption work | A concrete prospective action can serve as a resumption cue. | Preserve the next executable action and a restart artifact before switching. |
| Leroy and Glomb's ready-to-resume planning | A small return plan can protect a suspended thread. | `park N` records a stopping point, next action, problem, and evidence. |
| Split-attention research | Do not force the user to join a conclusion with a distant qualifier. | Co-locate result, condition, and evidence boundary in one numbered point. |
| Coherence and segmentation | Remove material that does not change understanding or action; reveal detail in stages. | Maximum four addressable items per field and expansion by reference. |
| Expertise reversal and guidance fading | Detail useful to one reader can be redundant for another. | Expand only the referenced point and bridge only missing context. |
| Cognitive offloading | External representations can reduce what must be remembered internally. | Stable numeric and lettered handles plus a verified resume cue. |
| Visual-search and glanceability research | One exceptional feature is easier to find across many competing displays. | A single conditional `Needs you` signal in a fixed first position. |

The one-to-four item limit is a product interface constraint, not a claim that human working memory has one universal four-item capacity.

## V2 acceptance checks

A V2 response passes contract checks when:

1. the first visible content is the conditional attention signal or `You are here`;
2. the triptych contains exactly three thematic breaks;
3. current-state identifiers are continuous numbers `1.`–`4.`;
4. future-action identifiers are continuous letters `A.`–`D.`;
5. the signal appears only when user intervention is genuinely required;
6. important evidence, retry, model, run, and uncertainty boundaries remain attached to their conclusions;
7. local references are portable and contain no `file://` URLs;
8. a status-only answer ends after the closing break;
9. a referenced follow-up expands or acts on the correct handle without replaying unrelated state;
10. persistent state is verified against current evidence before a consequential resume action.

## Evaluation boundary

Report three result families separately:

- **contract compliance:** labels, addresses, signal, separators, closure, and portable links;
- **semantic utility:** correct project, state, evidence limits, unresolved problem, and next action, independent of format;
- **host reliability and cost:** missing answers, timeouts, retries, reader-visible output, and host-reported tokens.

Do not use format compliance to claim reduced cognitive load. Human-facing evaluation should measure orientation accuracy, reference resolution, time to first correct action, and multi-window visual search separately.
