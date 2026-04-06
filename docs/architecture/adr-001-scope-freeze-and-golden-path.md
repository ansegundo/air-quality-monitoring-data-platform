# ADR-001: Scope Freeze and Golden Pipeline First

- Status: Accepted
- Date: 2026-02-10
- Owner: Alberto Segundo

## Context

The initial roadmap tried to move several tracks at once:
- AWS native lakehouse components
- Databricks path
- Streaming simulation
- Orchestration, API, BI, and observability in parallel

For a single-owner project, that spread makes it too easy to end up with a little of everything and not enough of anything that is operationally solid. The risk is less about technical feasibility and more about ending with partial systems that are hard to run, test, and explain.

## Decision

Prioritize one end-to-end vertical slice (the "golden path") before adding secondary platform paths.

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
- Higher probability of shipping a complete and reliable pipeline
- Clearer failure model and easier troubleshooting
- Stronger maintainability as the project expands

Negative:
- Less short-term tool coverage
- Delayed cross-platform benchmark artifacts

## Success Criteria

- A new contributor can run the stack locally with documented steps.
- The golden DAG completes end-to-end and can be rerun safely.
- CI validates linting and tests on each change.
- Deferred work remains documented as backlog, not ad-hoc scope creep.
