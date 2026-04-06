from __future__ import annotations

import json
from unittest.mock import call

from scripts.profile_openaq_payload import (
    fetch_measurements_for_sensors,
    fetch_sensors_for_locations,
    main,
    normalize_records,
    profile_records,
)


def test_normalize_records_from_results_list():
    payload = {"results": [{"id": 1}, {"id": 2}, "skip-me"]}

    records = normalize_records(payload)

    assert records == [{"id": 1}, {"id": 2}]


def test_profile_records_aggregates_basic_contract_fields():
    records = [
        {"id": 1, "name": "A"},
        {"id": 2},
        {"id": 3, "name": "C"},
    ]

    prof = profile_records(records, "locations")

    assert prof["endpoint"] == "locations"
    assert prof["total_records"] == 3
    assert prof["total_fields"] == 2
    assert prof["field_names"] == ["id", "name"]
    assert "id" in prof["fields"]
    assert "name" in prof["fields"]


def test_nested_fetches_use_hierarchical_endpoints(mocker):
    session = object()
    fetch_endpoint = mocker.patch(
        "scripts.profile_openaq_payload.fetch_endpoint",
        side_effect=[
            [{"id": 11}, {"id": 12}],
            [{"id": 101}],
            [{"id": 1001}],
            [{"id": 1002}],
        ],
    )

    sensors = fetch_sensors_for_locations(
        session=session,
        base_url="https://api.openaq.org/v3",
        location_records=[{"id": 1}, {"id": 2}],
        sensor_limit=5,
        timeout=30,
    )
    measurements = fetch_measurements_for_sensors(
        session=session,
        base_url="https://api.openaq.org/v3",
        sensor_records=[{"id": 11}, {"id": 12}],
        measurement_limit=20,
        timeout=30,
    )

    assert sensors == [{"id": 11}, {"id": 12}, {"id": 101}]
    assert measurements == [{"id": 1001}, {"id": 1002}]
    assert fetch_endpoint.call_args_list == [
        call(
            session=session,
            base_url="https://api.openaq.org/v3",
            endpoint="locations/1/sensors",
            limit=5,
            timeout=30,
        ),
        call(
            session=session,
            base_url="https://api.openaq.org/v3",
            endpoint="locations/2/sensors",
            limit=5,
            timeout=30,
        ),
        call(
            session=session,
            base_url="https://api.openaq.org/v3",
            endpoint="sensors/11/measurements",
            limit=20,
            timeout=30,
        ),
        call(
            session=session,
            base_url="https://api.openaq.org/v3",
            endpoint="sensors/12/measurements",
            limit=20,
            timeout=30,
        ),
    ]


def test_main_with_local_inputs_generates_summary_file(tmp_path, monkeypatch):
    locations_file = tmp_path / "locations.json"
    sensors_file = tmp_path / "sensors.json"
    measurements_file = tmp_path / "measurements.json"
    output_file = tmp_path / "summary.json"

    locations_file.write_text(json.dumps({"results": [{"id": 1, "name": "Loc"}]}))
    sensors_file.write_text(json.dumps({"results": [{"id": 11, "name": "Sensor"}]}))
    measurements_file.write_text(json.dumps({"results": [{"id": 111, "value": 12.5}]}))

    monkeypatch.setenv("OPENAQ_API_KEY", "test-key")
    monkeypatch.setattr(
        "sys.argv",
        [
            "profile_openaq_payload.py",
            "--locations-input",
            str(locations_file),
            "--sensors-input",
            str(sensors_file),
            "--measurements-input",
            str(measurements_file),
            "--output",
            str(output_file),
        ],
    )

    main()

    assert output_file.exists()
    summary = json.loads(output_file.read_text())
    assert summary["metadata"]["api_key_source"] == "env"
    assert summary["profiles"]["locations"]["total_records"] == 1
    assert summary["profiles"]["sensors"]["total_records"] == 1
    assert summary["profiles"]["measurements"]["total_records"] == 1
