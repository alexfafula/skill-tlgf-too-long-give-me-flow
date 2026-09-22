# Addressable Flow

Use these rules when the user refers to a numeric state point or lettered action from the most recent TLGF frame.

## Resolve the frame

1. Find the most recent TLGF triptych in the current conversation.
2. Resolve numbers only against `What's happening now` and letters only against `Suggested next steps`.
3. Preserve the original identifier once only when it helps confirm resolution.
4. Use current evidence before a consequential action when the frame may be stale.
5. If several frames remain plausible and choosing the wrong one would materially change the action, name the ambiguity and ask one bounded question.

Do not treat numeric and lettered identifiers as globally unique. They are local to the most recent conversation frame.

For a non-state-changing follow-up, begin with the answer or result. Use one compact paragraph or at most three short bullets. Do not add an operation heading, quote the full referenced item, or link back to the prior frame or its source file.

## Expand a point

For `expand 2`, `deep dive 2`, or an equivalent request:

- answer point 2 directly;
- preserve its evidence and uncertainty boundary;
- add only the prerequisites needed to understand or investigate it;
- do not replay points 1, 3, or 4;
- do not emit a new triptych unless the investigation changes the material state.

A deep dive keeps the current goal as the return path. If the investigation becomes the active workstream, refresh the triptych after the transition.

## Select or execute an action

For `B`, `do B`, or an equivalent request:

- identify action B from the most recent frame;
- treat the reference as selection or execution, not a request to explain the alphabet;
- execute it when safe and authorized;
- ask only when a required decision, authority, secret, or external fact is missing;
- refresh the triptych after the action materially changes state.

Do not spend the response restating action B before performing it. A short prefix such as `B —` is enough when confirmation matters.

For `B vs C`, compare only the consequence, risk, cost, or reversibility that distinguishes the two actions. Keep the recommended action first.

## Park a point

For `park 4`:

1. Keep the active workstream unchanged.
2. Persist the lead only when project writes are authorized.
3. Store the signal, smallest supporting evidence, and condition for revisiting it.
4. Remove it from the active frame on the next refresh unless it constrains the current action.

Do not turn a parked lead into another public field.

## Fork from a point

For `fork 3`:

1. Record a ready-to-resume cue for the outgoing workstream when losing it would create reconstruction work.
2. Promote point 3 to the active workstream.
3. Preserve its parent relationship to the prior frame.
4. Verify the branch, run, or artifact before acting when the fork depends on repository state.
5. Emit one refreshed triptych for the new active path.

`fork` changes semantic focus. It does not authorize creating a Git branch, external issue, new process, or other side effect unless the user's request also authorizes that action.

## Refresh

For `refresh`:

- verify current evidence in proportion to the decision at stake;
- rebuild the semantic breadcrumb;
- renumber current points from `1.` and reletter actions from `A.`;
- retain old identifiers only while explaining a transition from the previous frame;
- do not silently carry forward resolved, stale, or disproved items.

## Missing or mismatched reference

When the conversation contains no TLGF frame, or the identifier matches nothing in the most recent frame:

- say so in one sentence; do not guess which item the user meant;
- rebuild the frame from current evidence when ongoing work exists, then answer against the new addresses;
- with no ongoing work and no evidence, ask for the missing context in one bounded question instead of inventing state.

A saved `.tlgf/STATE.md` stores semantic resume cues, not addresses. After a resume, emit one fresh frame before honoring numeric or lettered references.

## Attention signal

Use the localized `⛔ Needs you` signal on a refreshed frame only when the user is the actual gating condition. Do not use it for an issue the agent can safely resolve, normal work in progress, or an optional next action.
