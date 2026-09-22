# Changelog

All notable changes to TLGF are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- The `tlgf` skill: an addressable three-field triptych (`You are here`, `What's happening now`, `Suggested next steps`), a conditional `⛔ Needs you` signal, Addressable Flow references (`expand 2`, `do B`, `B vs C`, `park 4`, `fork 3`, `deep dive 2`, `refresh`), continuity and lineage references, and a `.tlgf/STATE.md` restart index.
- Rules for blank lines around every `---`, one-or-two-sentence points and a 60–150-word status frame, nothing after the closing break, a missing-frame reference, and no trigger-word echo, mirrored in both adapters.
- A Claude Code output style and an `AGENTS.md` instruction block that apply the contract without skill triggering; the output style was forward-tested headlessly (`docs/adapter-forward-test.md`).
- Twelve behavior-evaluation cases, including localized Polish labels, a reference with no frame, a deliverable after the triptych, `park`, and `refresh`.
- A validator that checks the frontmatter, the public template, the required rules in the skill and both adapters, reference routing, the bundled license, and the eval cases.
- The paired benchmark `tlgf-continuity-v2` under `benchmarks/tlgf/`: natural prompts, the prior frame embedded in follow-up prompts, exact-token gates, per-case localized labels, `semantic_facts` for the judge, thirteen default cases and a pinned Flask case.
- Shared benchmark tools: the blinded LLM judge with a `--facts` mode, deterministic style signals, `summarize.py`, `publish_run.py`, and a CI workflow.
- Grader revision 2.1 after the first full run with natural prompts: `missing-frame` accepts a minimal rebuilt frame and the `Needs you` signal, labels accept a list of natural variants per case, paraphrases of "no final answer" count, the TLDF-era `supersede` ban is gone, the branch is no longer required where the prompt doesn't ask for it, and the Flask case flags its deliverable after the frame (`docs/calibration-log.md`).
- The benchmark's workspace-mutation gate ignores `.tlgf/STATE.md`, which the skill may update when writes are authorized, and records `state_file_updated` separately.
- The useful-signal rule no longer says to omit an evidence-backed signal by default; it says to leave out trivia and unsupported patterns. Reason: the old wording told the model to stay silent, which contradicts the contract's promise to surface a genuine signal.

[Unreleased]: https://github.com/alexfafula/skill-tlgf-too-long-give-me-flow/commits/main
