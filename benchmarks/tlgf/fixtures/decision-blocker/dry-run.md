# Customer-record migration dry run

- Run: `migration-dry-run-20260821`
- Target: production deployment
- Result: 14 existing customer records would be overwritten
- Recovery boundary: the planned operation is reversible only before deployment
- Safe path A: delay the release, repair the conflicting records, and repeat the dry run
- Safe path B: exclude the 14 records, deploy the remaining migration, and record a follow-up repair
- Authority: only the release owner can choose between safe path A and safe path B
- Current state: no write or deployment has started
