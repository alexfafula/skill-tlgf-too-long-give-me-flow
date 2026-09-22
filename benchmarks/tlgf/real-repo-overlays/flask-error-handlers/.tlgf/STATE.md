# TLGF state

Updated: 2026-08-18 16:40 UTC

## Situation

- Project: Flask
- Workstream: Blueprint 404 error-handler investigation
- Stage: Source-path verification on `benchmark/flask-error-handlers`.
- Objective: Explain why a blueprint 404 handler handles `abort(404)` inside a blueprint view but not an unmatched URL under the blueprint prefix.

## Current state

- Last completed: Confirmed the documented distinction between an exception raised inside a blueprint view and a 404 raised during routing.
- Now: Trace handler selection in source; saved state still names alpha, while the report index names beta.
- Problem: The exact request-state value that excludes the blueprint during a routing 404 is not yet verified.
- Evidence: `.tlgf/reports/alpha.json` and `.tlgf/reports/index.json`.

## Resume

- Next best action: Inspect `src/flask/sansio/app.py::_find_error_handler` and find the closest regression test.
- Open these: `docs/errorhandling.rst`, `src/flask/sansio/app.py`, and `tests/test_user_error_handler.py`.
