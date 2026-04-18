# 2026-04-13

- Hardened watch-history parsing to require a single tail timestamp and persist parse flags for auditability.
- Excluded URL-only/empty cleaned titles from semantic topic clustering and surfaced exclusion counts/examples in outputs.
- Improved topic labeling and consolidation to reduce duplicate same-label topics and prevent URL labels.
- Stabilized topic timeline calculations by using normalized parsed datetimes for first/last seen fields.
