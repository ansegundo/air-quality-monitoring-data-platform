# ADR-001: Scope Freeze and Golden Pipeline First

- Status: Accepted
- Date: 2026-02-10
- Owner: Alberto Segundo

## Context

The initial roadmap covered multiple platforms and delivery patterns at once:
- AWS native lakehouse components
- Databricks path
- streaming simulation
- orchestration, API, BI, and observability in parallel

For a single-owner project with an 8-week target, this scope increases delivery risk and typically leads to shallow implementation across many tools. The main risk is not technical feasibility; it is ending with partial systems that are hard to operate, test, and explain.

## Decision

Prioritize one production-style vertical slice ("golden path") before adding secondary platform paths.

Phase 1 (in scope):
- one orchestration path (Airflow local-first)
- one ingestion source (OpenAQ)
- explicit data contract and schema validation
- idempotent bronze/silver write strategy
- automated tests (DAG load/structure + ingest behavior + idempotency)
- operational baseline (logs, run metadata, recovery notes)

Phase 2 (explicitly deferred):
- Databricks comparison path
- streaming simulation path
- multiple serving surfaces built in parallel

## Rationale

- Delivery quality is higher when scope is constrained to one end-to-end path.
- Operational behavior (retries, reruns, recovery) is easier to prove on a focused slice.
- Deferred scope is easier to sequence once the core contract is stable.

## Consequences

Positive:
- higher probability of shipping a complete and reliable pipeline
- clearer failure model and easier troubleshooting
- stronger maintainability as the project expands

Negative:
- less short-term tool coverage
- delayed cross-platform benchmark artifacts

## Success Criteria

- A new contributor can run the stack locally with documented steps.
- The golden DAG completes end-to-end and can be rerun safely.
- CI validates linting and tests on each change.
- Deferred work remains documented as backlog, not ad-hoc scope creep.
