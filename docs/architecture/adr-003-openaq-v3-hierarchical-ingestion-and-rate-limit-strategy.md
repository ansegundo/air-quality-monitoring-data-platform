# ADR-003: OpenAQ v3 Hierarchical Ingestion and Rate-Limit Strategy

- Status: Proposed
- Date: 2026-03-27
- Owner: Alberto Segundo

## Context

ADR-002 left the v1 contract open pending a profiling spike against the real OpenAQ v3 API.

That spike confirmed two practical constraints.

First, the API access pattern is hierarchical. `locations` is a usable top-level entry point, but `sensors` and `measurements` are reached by traversing parent resources:
- `/v3/locations`
- `/v3/locations/{location_id}/sensors`
- `/v3/sensors/{sensor_id}/measurements`

Second, rate limiting becomes a real issue once that traversal fans out. A smaller run completed with `10` locations and `19` sensors. A broader run over `20` locations and `65` sensors failed on measurements with `429 Too many requests`.

The sampled payloads also showed that some sensor metadata fields, especially `datetimeFirst` and `datetimeLast`, were not reliably populated and should not be treated as required in v1.

## Decision

Implement the phase-1 OpenAQ ingestion as a hierarchical flow rooted in `locations`.

For the first accepted version of the golden path:
- ingest `locations`
- ingest `sensors` per location
- keep broad `measurements` ingestion deferred or tightly rate-limited
- use a narrow v1 contract based on fields with strong presence in the spike

Recommended fields for the first slice:
- locations: `id`, `name`, `country`, `coordinates`, `owner`
- sensors: `id`, `name`, `parameter`

## Rationale

- The pipeline should match the actual shape of the source API rather than assume a flat resource model.
- Measurement fan-out is expensive enough to trigger `429` responses in wider runs, so it needs bounded retries, backoff, and clear operational limits.
- `locations` and `sensors` provide enough stable structure to move the first contract forward without blocking on full measurement coverage.

## Consequences

Positive:
- The ingestion design now reflects the real behavior of the external API
- The first pipeline slice can stay reliable without overcommitting to unstable or rate-limited paths
- The contract can move forward using fields with demonstrated presence in sampled data

Negative:
- The phase-1 slice covers less of the full OpenAQ surface than originally hoped
- Measurement-heavy analytics are deferred until rate-limit-aware extraction is in place
- The DAG design must account for parent-child traversal rather than simple flat extraction

## Evidence

Representative artifact kept from the profiling spike:
- `artifacts/spikes/openaq_profile_20260327_123804.json`

Observed runtime evidence:
- Successful end-to-end hierarchical profiling for locations and sensors
- Zero measurements returned for the sampled run
- `429 Too many requests` encountered during broader measurement fan-out

## Success Criteria

This ADR can move from `Proposed` to `Accepted` when:
- The golden DAG uses hierarchical extraction for OpenAQ v3
- Locations and sensors are ingested with stable run metrics
- Reruns remain safe under the chosen contract/idempotency model
- Measurement ingestion is either explicitly deferred or guarded by rate-limit controls
