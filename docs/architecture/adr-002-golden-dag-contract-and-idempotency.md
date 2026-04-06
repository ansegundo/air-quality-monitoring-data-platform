# ADR-002: Golden DAG Data Contract and Idempotent Load Strategy

- Status: Proposed
- Date: 2026-02-10
- Owner: Alberto Segundo

## Context

Before expanding platform scope, the first pipeline slice needs to behave predictably. In practice that means:
- Predictable schema behavior
- Safe reruns across the same data window
- Clear failure and recovery rules

Without those basics, downstream metrics and analysis are hard to trust.

## Decision

Implement one golden Airflow DAG that ingests OpenAQ records, validates a defined contract, and writes to local bronze/silver layers with idempotent semantics.

Chosen implementation details:
- Local sink: PostgreSQL (separate `air_quality` schema from the Airflow metadata schema)
- Invalid records: quarantine table (`air_quality.quarantine_openaq_v1`) with error reason and raw payload
- Schema evolution policy:
  - additive changes are allowed with contract version update
  - breaking changes fail fast and require an explicit migration/version bump

## Contract Definition (v1)

Status: narrowed after the profiling spike; see `ADR-003`.

Current direction:
- Start with fields that are stable and well-populated in `locations` and `sensors`
- Do not block the first accepted version on full `measurements` coverage
- Keep the dedupe key provisional until implementation confirms the best identity mix

Working hypotheses to confirm during implementation:
- Candidate identity dimensions include location, parameter, and observation timestamp.
- Candidate measure fields include observed value and unit.
- Candidate geo fields include latitude/longitude when present.

Validation rules (target behavior):
- Observation timestamp normalized to UTC ISO-8601.
- Numeric fields cast with explicit error handling.
- Missing required fields are invalid.
- Unexpected extra fields are ignored in silver and counted in logs.

## Load Semantics

Bronze layer:
- Append raw records with ingestion metadata (`ingested_at`, `run_id`, `source`, `extract_start`, `extract_end`)
- No destructive rewrite

Silver layer:
- Normalized queryable records in PostgreSQL
- Dedupe key and upsert conflict strategy stay provisional until implementation confirms stable identity fields

Idempotency rule:
- Rerunning the same extraction window must not increase silver row count for already ingested records

## Failure and Recovery

- API/network errors: retry with bounded backoff, then fail the task
- Contract violations: write invalid records to quarantine and continue with the valid subset
- Reruns/backfills: execute by time window using the same dedupe key strategy

## Observability Requirements

Each run must log:
- Fetched row count
- Valid row count
- Invalid/quarantined row count
- Silver upserted row count
- Extraction window and run duration
- Dedupe conflict/upsert metrics

## Consequences

Positive:
- Deterministic behavior for reprocessing and backfills
- Better trust in downstream curated data
- Easier root-cause analysis through run-level metrics

Negative:
- More initial implementation effort than a simple append-only ingestion
- Contract updates require explicit versioning decisions

## Success Criteria

- DAG runs end-to-end locally.
- Re-run over the same input window produces no duplicates in silver.
- Automated tests cover DAG structure, contract behavior, and idempotent writes.

## Exit Criteria for Acceptance

The profiling spike has been completed and documented in `ADR-003`.

Before moving this ADR to `Accepted`, the implementation should confirm:
- The selected v1 required/optional fields hold up in pipeline runs
- The dedupe key works correctly for reruns and backfills
- Timestamp normalization behaves consistently in practice
- Contract violations are routed cleanly to quarantine with useful error detail
