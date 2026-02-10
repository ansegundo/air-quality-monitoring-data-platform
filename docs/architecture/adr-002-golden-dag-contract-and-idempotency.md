# ADR-002: Golden DAG Data Contract and Idempotent Load Strategy

- Status: Proposed
- Date: 2026-02-10
- Owner: Alberto Segundo

## Context

The first pipeline slice must be operationally reliable before expanding platform scope. Reliability here means:
- predictable schema behavior
- safe reruns across the same data window
- clear failure and recovery rules

Without these guarantees, downstream metrics and analysis become difficult to trust.

## Decision

Implement one "golden" Airflow DAG that ingests OpenAQ records, validates a defined contract, and writes to local bronze/silver layers with idempotent semantics.

Chosen implementation details:
- Local sink: PostgreSQL (separate `air_quality` schema from Airflow metadata schema)
- Invalid records: quarantine table (`air_quality.quarantine_openaq_v1`) with error reason and raw payload
- Schema evolution policy:
  - additive changes are allowed with contract version update
  - breaking changes fail-fast and require explicit migration/version bump

## Contract Definition (v1)

Status: `TBD after payload profiling spike`

Initial hypotheses (to validate with sampled payloads):
- Candidate identity dimensions include location, parameter, and observation timestamp.
- Candidate measure fields include observed value and unit.
- Candidate geo fields include latitude/longitude when present.

Validation rules (target behavior once contract is finalized):
- Observation timestamp normalized to UTC ISO-8601.
- Numeric fields cast with explicit error handling.
- Missing required fields are invalid.
- Unexpected extra fields are ignored in silver and counted in logs.

## Load Semantics

Bronze layer:
- append raw records with ingestion metadata (`ingested_at`, `run_id`, `source`, `extract_start`, `extract_end`)
- no destructive rewrite

Silver layer:
- normalized queryable records in PostgreSQL
- dedupe key and upsert conflict strategy are provisional until profiling confirms stable identity fields

Idempotency rule:
- rerunning the same extraction window must not increase silver row count for already ingested records

## Failure and Recovery

- API/network errors: retry with bounded backoff, then fail task
- contract violations: write invalid records to quarantine table and continue with valid subset
- reruns/backfills: execute by time window using same dedupe key strategy

## Observability Requirements

Each run must log:
- fetched row count
- valid row count
- invalid/quarantined row count
- silver upserted row count
- extraction window and run duration
- dedupe conflict/upsert metrics

## Consequences

Positive:
- deterministic behavior for reprocessing and backfills
- better trust in downstream curated data
- easier root-cause analysis through run-level metrics

Negative:
- more initial implementation effort than simple append-only ingestion
- contract updates require explicit versioning decisions

## Success Criteria

- DAG runs end-to-end locally.
- Re-run over same input window produces no duplicates in silver.
- Automated tests cover DAG structure, contract behavior, and idempotent writes.

## Profiling Exit Criteria

Before moving this ADR to `Accepted`, complete a profiling spike and capture:
- field presence matrix across a representative sample window
- null/type quality summary per candidate contract field
- duplicate-pattern analysis for candidate dedupe keys
- timestamp format and timezone normalization behavior
- recommended v1 required/optional field set with evidence
