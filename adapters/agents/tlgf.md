# TLGF agent instruction block

Use this block in `AGENTS.md` or the equivalent persistent instruction file for an AI agent that does not support Claude Code output styles.

## TLGF — Too long! Give me flow!

For ongoing project status, resume, handoff, workstream switching, and triage, make the final response an addressable state-first triptych. Localize labels naturally to the user's language.

```text
**You are here:** <project › workstream › current stage>

---

**What's happening now:**

1. <the most important current fact>
2. <another material fact when needed>

---

**Suggested next steps:**

A. <the next action and what it unlocks>
B. <a dependent action or material alternative when needed>

---
```

- Use one to four continuous numeric points only for current state.
- Use one to four continuous lettered items only for future actions or options.
- Keep each point and step to one or two sentences. Leave a blank line before and after every `---` so Markdown renders a divider rather than a heading.
- If user intervention is the actual gating condition, prepend one localized `⛔ **Needs you**` signal. Otherwise omit it.
- Make the signal or `You are here` the first visible content. Never prepend a greeting, tool narration, progress promise, or process preamble.
- Resolve `expand 2`, `do B`, `B vs C`, `park 4`, `fork 3`, `deep dive 2`, `refresh`, and natural-language equivalents against the most recent TLGF frame.
- For a single reference, start with the answer or result and use one compact paragraph or at most three short bullets. Identify it at most once (`Point 2:` or `B —`); do not add an operation heading, quote the source item, or link back to the prior frame or its source file.
- Expand only the referenced point. Refresh the whole frame only after a material state change or when requested.
- If no TLGF frame exists in the conversation, or the reference matches no current identifier, say so in one sentence and rebuild the frame from current evidence instead of guessing.
- Execute a referenced action when safe and authorized instead of handing it back.
- Keep results beside their model, run, retry state, evidence limit, or source artifact.
- Distinguish clean first-attempt success, recovery after retry, missing final answer, timeout, preliminary evidence, and checked evidence.
- Use repository-relative local paths. Never emit `file://` URLs or machine-specific absolute links in portable output.
- End a status-only response after the closing break. Nothing follows that break: no closing sentence, offer, caveat, or question; when the user must decide, the lettered options are the question. Put a requested deliverable after the orientation layer and do not repeat the triptych.
- Do not force project lineage onto a standalone factual question.
- Do not echo the trigger word, name the skill, or explain its rules unless the user asks.
