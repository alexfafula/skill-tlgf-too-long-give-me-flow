# Persistent lineage

Use persistent lineage as a verified restart index, not a transcript, backlog, or project-management system.

## Source precedence

Resolve conflicts in this order:

1. Current raw artifacts, tool output, repository state, and run results.
2. Explicit user decisions.
3. `.tlgf/STATE.md`.
4. Conversation summaries and model memory.

When higher-priority evidence changes the state, update the index and retain the older item only when it explains the current path.

## State file

Use `.tlgf/STATE.md` at the workspace root. Keep one current snapshot per workspace.

```markdown
# TLGF state

Updated: YYYY-MM-DD HH:MM Z

## Situation

- Project:
- Workstream:
- Stage:
- Objective:

## Current state

- Last completed:
- Now:
- Problem:
- Evidence:

## Resume

- Next best action:
- Open these:

## Decisions

- YYYY-MM-DD — Decision. Reason. Evidence. Earlier approach, if changed.

## Parked leads

- Lead — Evidence. Revisit when.
```

Omit empty optional fields. Use exact identifiers and repository-relative paths when possible.

## Update rules

- Update after a meaningful transition, not after every message.
- Replace stale current-state fields instead of accumulating history.
- Keep durable decisions; remove temporary deliberation after a decision is made.
- Keep only material parked leads. Remove one when it is promoted, dismissed, or no longer relevant.
- Write `Next best action` as one executable action and state what it unlocks.
- Point `Open these` to the smallest useful artifact set instead of copying raw output.
- Record progress with milestones or real counts. Do not estimate percentages from intuition.
- Link large logs, reports, and benchmark outputs instead of pasting them.
- Never record credentials, secret values, private conversation, hidden reasoning, or personal profiling.
- Keep unrelated projects in their own workspaces.
- Do not persist bare numeric or lettered frame identifiers as if they were globally stable. Persist their semantic content and rebuild addresses when a frame is refreshed.

## Stale-state recovery

When current evidence conflicts with the saved index:

1. Identify the saved value and the contradictory current evidence.
2. Resolve the current state using source precedence.
3. Preserve the old value as a predecessor only when it remains useful.
4. Update the state file when writes are authorized.
5. Express the resolved state through one TLGF triptych.

Do not silently replace a failed run, a conclusion made obsolete by new evidence, or a first-attempt failure with a later success. A recovered pass does not establish first-attempt reliability.
