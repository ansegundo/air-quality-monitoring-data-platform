from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def load_api_key(cli_api_key: str | None) -> tuple[str, str]:
    if cli_api_key:
        return cli_api_key, "cli"
    env_api_key = os.getenv("OPENAQ_API_KEY")
    if env_api_key:
        return env_api_key, "env"
    raise RuntimeError(
        "Missing API key. Provide --api-key or set OPENAQ_API_KEY in environment/.env"
    )


def build_session(api_key: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "X-API-Key": api_key,
            "Accept": "application/json",
            "User-Agent": "openaq-profiling-spike/0.1.0",
        }
    )
    return s


def normalize_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        results = payload.get("results")
        if isinstance(results, list):
            return [r for r in results if isinstance(r, dict)]
        if isinstance(results, dict):
            return [results]
        if "id" in payload or "name" in payload:
            return [payload]

    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]

    raise ValueError("Unsupported payload shape (expected list or {results: [...]})")


def fetch_endpoint(
    session: requests.Session,
    base_url: str,
    endpoint: str,
    limit: int,
    timeout: int,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    query = {"limit": limit}
    if params:
        query.update(params)
    try:
        resp = session.get(url, params=query, timeout=timeout)
        resp.raise_for_status()
        return normalize_records(resp.json())
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        body = e.response.text[:300] if e.response is not None else ""
        raise RuntimeError(
            f"OpenAQ request failed ({endpoint}) [{status}] {body}"
        ) from e


def extract_record_ids(records: list[dict[str, Any]]) -> list[int | str]:
    record_ids: list[int | str] = []
    for record in records:
        record_id = record.get("id")
        if record_id is not None:
            record_ids.append(record_id)
    return record_ids


def fetch_sensors_for_locations(
    session: requests.Session,
    base_url: str,
    location_records: list[dict[str, Any]],
    sensor_limit: int,
    timeout: int,
) -> list[dict[str, Any]]:
    sensors: list[dict[str, Any]] = []
    location_ids = extract_record_ids(location_records)

    logger.info(
        "  Fetching sensors via /locations/{location_id}/sensors "
        f"for {len(location_ids)} locations (limit={sensor_limit} each)"
    )

    for location_id in location_ids:
        child_records = fetch_endpoint(
            session=session,
            base_url=base_url,
            endpoint=f"locations/{location_id}/sensors",
            limit=sensor_limit,
            timeout=timeout,
        )
        sensors.extend(child_records)

    return sensors


def fetch_measurements_for_sensors(
    session: requests.Session,
    base_url: str,
    sensor_records: list[dict[str, Any]],
    measurement_limit: int,
    timeout: int,
) -> list[dict[str, Any]]:
    measurements: list[dict[str, Any]] = []
    sensor_ids = extract_record_ids(sensor_records)

    logger.info(
        "  Fetching measurements via /sensors/{sensor_id}/measurements "
        f"for {len(sensor_ids)} sensors (limit={measurement_limit} each)"
    )

    for sensor_id in sensor_ids:
        child_records = fetch_endpoint(
            session=session,
            base_url=base_url,
            endpoint=f"sensors/{sensor_id}/measurements",
            limit=measurement_limit,
            timeout=timeout,
        )
        measurements.extend(child_records)

    return measurements


def extract_all_keys(records: list[dict[str, Any]]) -> set[str]:
    """Extract all top-level keys from a list of records."""
    keys = set()
    for record in records:
        keys.update(record.keys())
    return keys


def profile_field(records: list[dict[str, Any]], field: str) -> dict[str, Any]:
    """Profile a single field across all records."""
    values = []
    null_count = 0
    types_seen = set()

    for record in records:
        val = record.get(field)
        if val is None:
            null_count += 1
        else:
            values.append(val)
            type_name = type(val).__name__
            types_seen.add(type_name)

    profile = {
        "count": len(records),
        "null_count": null_count,
        "present_count": len(records) - null_count,
        "presence_pct": round(100.0 * (len(records) - null_count) / len(records), 2)
        if records
        else 0.0,
        "types": sorted(types_seen),
    }

    # Compute stats for numeric/string values
    if values:
        sample_size = min(5, len(values))
        profile["sample"] = [
            json.loads(json.dumps(v, default=str)) for v in values[:sample_size]
        ]
        profile["sample_size"] = sample_size

        # Distinct count approximation (up to 100 unique for cheap profiling)
        distinct = set()
        for v in values[:100]:
            try:
                distinct.add(json.dumps(v, sort_keys=True, default=str))
            except (TypeError, ValueError):
                distinct.add(str(v))
        profile["distinct_count_approx"] = len(distinct)

        # Numeric stats
        numeric_vals = []
        for v in values:
            if isinstance(v, (int, float)):
                numeric_vals.append(v)
        if numeric_vals:
            profile["numeric"] = {
                "min": min(numeric_vals),
                "max": max(numeric_vals),
                "mean": round(sum(numeric_vals) / len(numeric_vals), 4),
            }

    return profile


def profile_records(
    records: list[dict[str, Any]], endpoint_name: str
) -> dict[str, Any]:
    """Profile a collection of records."""
    logger.info(f"Profiling {endpoint_name}: {len(records)} records")

    if not records:
        return {
            "endpoint": endpoint_name,
            "total_records": 0,
            "fields": {},
            "note": "No records to profile",
        }

    keys = extract_all_keys(records)
    field_profiles = {}

    for key in sorted(keys):
        field_profiles[key] = profile_field(records, key)

    return {
        "endpoint": endpoint_name,
        "total_records": len(records),
        "total_fields": len(keys),
        "field_names": sorted(keys),
        "fields": field_profiles,
    }


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Profile OpenAQ payloads for contract and dedupe design"
    )
    parser.add_argument("--base-url", default="https://api.openaq.org/v3")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument(
        "--sensor-limit",
        type=int,
        default=5,
        help="Max sensors fetched per location when calling the API",
    )
    parser.add_argument(
        "--measurement-limit",
        type=int,
        default=20,
        help="Max measurements fetched per sensor when calling the API",
    )
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--output", default="openaq_profile_summary.json")
    parser.add_argument(
        "--locations-input",
        default=None,
        help="Path to local JSON for locations payload",
    )
    parser.add_argument(
        "--sensors-input", default=None, help="Path to local JSON for sensors payload"
    )
    parser.add_argument(
        "--measurements-input",
        default=None,
        help="Path to local JSON for measurements payload",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.info("OpenAQ Payload Profiling Spike")
    logger.info(f"Output file: {args.output}")

    try:
        api_key, api_key_source = load_api_key(args.api_key)
        logger.info(f"API key loaded from {api_key_source}")
    except RuntimeError as e:
        logger.error(f"Failed to load API key: {e}")
        sys.exit(1)

    session = build_session(api_key)

    logger.info("Fetching/loading locations...")
    try:
        if args.locations_input:
            logger.info(f"Loading from local file: {args.locations_input}")
            locations_records = normalize_records(
                json.loads(Path(args.locations_input).read_text())
            )
        else:
            logger.info(f"Fetching from {args.base_url}/locations (limit={args.limit})")
            locations_records = fetch_endpoint(
                session=session,
                base_url=args.base_url,
                endpoint="locations",
                limit=args.limit,
                timeout=args.timeout,
            )
        logger.info(f"Loaded {len(locations_records)} location records")
    except Exception as e:
        logger.error(f"Failed to fetch/load locations: {e}")
        sys.exit(1)

    logger.info("Fetching/loading sensors...")
    try:
        if args.sensors_input:
            logger.info(f"Loading from local file: {args.sensors_input}")
            sensors_records = normalize_records(
                json.loads(Path(args.sensors_input).read_text())
            )
        else:
            sensors_records = fetch_sensors_for_locations(
                session=session,
                base_url=args.base_url,
                location_records=locations_records,
                sensor_limit=args.sensor_limit,
                timeout=args.timeout,
            )
        logger.info(f"Loaded {len(sensors_records)} sensor records")
    except Exception as e:
        logger.error(f"Failed to fetch/load sensors: {e}")
        sys.exit(1)

    logger.info("Fetching/loading measurements...")
    try:
        if args.measurements_input:
            logger.info(f"Loading from local file: {args.measurements_input}")
            measurements_records = normalize_records(
                json.loads(Path(args.measurements_input).read_text())
            )
        else:
            measurements_records = fetch_measurements_for_sensors(
                session=session,
                base_url=args.base_url,
                sensor_records=sensors_records,
                measurement_limit=args.measurement_limit,
                timeout=args.timeout,
            )
        logger.info(f"Loaded {len(measurements_records)} measurement records")
    except Exception as e:
        logger.error(f"Failed to fetch/load measurements: {e}")
        sys.exit(1)

    logger.info("Profiling datasets...")
    profiles = {
        "locations": profile_records(locations_records, "locations"),
        "sensors": profile_records(sensors_records, "sensors"),
        "measurements": profile_records(measurements_records, "measurements"),
    }

    summary = {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "api_key_source": api_key_source,
            "base_url": args.base_url,
            "limits": {
                "locations": args.limit,
                "sensors_per_location": args.sensor_limit,
                "measurements_per_sensor": args.measurement_limit,
                "timeout_seconds": args.timeout,
            },
            "input_sources": {
                "locations": args.locations_input or "api",
                "sensors": args.sensors_input or "api",
                "measurements": args.measurements_input or "api",
            },
        },
        "profiles": profiles,
    }

    logger.info(f"Writing summary to {args.output}...")
    Path(args.output).write_text(json.dumps(summary, indent=2))
    logger.info("✓ Done!")


if __name__ == "__main__":
    main()
