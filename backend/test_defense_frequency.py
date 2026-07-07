#!/usr/bin/env python3
"""
Integration smoke script for STEP 25: Championship Defense Frequency.

The checks in this file exercise a live Flask server at ``localhost:8080``.
They are skipped during normal pytest runs when the server is not already
running, so the repository test suite remains deterministic.
"""

import pytest

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency for integration script
    requests = None


BASE_URL = "http://localhost:8080"


def _require_requests():
    if requests is None:
        pytest.skip("requests is not installed; skipping defense-frequency integration script")


def _require_live_server():
    _require_requests()
    try:
        return requests.get(f"{BASE_URL}/api/championships", timeout=2)
    except requests.exceptions.RequestException as exc:
        pytest.skip(
            f"Flask server is not running at {BASE_URL}; "
            f"skipping defense-frequency integration script ({exc})"
        )


def test_defense_frequency_system():
    print("=" * 60)
    print("STEP 25: Championship Defense Frequency - Verification Tests")
    print("=" * 60)

    print("\nTest 1: Fetching all championships...")
    response = _require_live_server()
    assert response.status_code == 200
    championships = response.json()["championships"]
    print(f"  Found {len(championships)} championships")

    if not championships:
        print("  No championships found - cannot continue tests")
        return

    test_champ = championships[0]
    print(f"\nTest 2: Getting defense frequency for {test_champ['name']}...")
    response = requests.get(f"{BASE_URL}/api/championships/{test_champ['id']}/defense-frequency")
    assert response.status_code == 200
    freq_data = response.json()
    print(f"  Requirements: {freq_data['requirements']}")
    print(f"  Status: {freq_data['status']}")

    print("\nTest 3: Setting custom defense requirements...")
    response = requests.post(
        f"{BASE_URL}/api/championships/{test_champ['id']}/defense-frequency/set",
        json={"max_days_between_defenses": 21, "min_defenses_per_year": 16},
    )
    assert response.status_code == 200
    print("  Requirements updated successfully")

    print("\nTest 4: Checking if defense is overdue...")
    response = requests.get(f"{BASE_URL}/api/championships/{test_champ['id']}/is-overdue")
    assert response.status_code == 200
    overdue_data = response.json()
    print(f"  Overdue: {overdue_data['is_overdue']}")
    print(f"  Urgency: {overdue_data['urgency_label']}")

    print("\nTest 5: Getting all overdue defenses...")
    response = requests.get(f"{BASE_URL}/api/championships/overdue-defenses")
    assert response.status_code == 200
    overdue = response.json()
    print(f"  Found {overdue['total']} overdue defenses")

    print("\nTest 6: Getting full defense schedule...")
    response = requests.get(f"{BASE_URL}/api/championships/defense-schedule")
    assert response.status_code == 200
    schedule = response.json()
    print(f"  Schedule contains {schedule['total']} championships")

    print("\nTest 7: Getting defense alerts...")
    response = requests.get(f"{BASE_URL}/api/championships/defense-alerts")
    assert response.status_code == 200
    alerts = response.json()
    print(f"  Found {alerts['total']} defense alerts")

    print("\nTest 8: Simulating overdue defense (test endpoint)...")
    response = requests.post(
        f"{BASE_URL}/api/test/defense-frequency/simulate-overdue",
        json={"title_id": test_champ["id"], "days_overdue": 15},
    )
    assert response.status_code == 200
    print("  Successfully simulated overdue defense")

    print("\nTest 9: Verifying overdue status after simulation...")
    response = requests.get(f"{BASE_URL}/api/championships/{test_champ['id']}/is-overdue")
    assert response.status_code == 200
    overdue_data = response.json()
    print(f"  Overdue: {overdue_data['is_overdue']}")
    print(f"  Days since defense: {overdue_data['days_since_defense']}")

    print("\nTest 10: Getting comprehensive defense frequency report...")
    response = requests.get(f"{BASE_URL}/api/test/defense-frequency/report")
    assert response.status_code == 200
    report = response.json()["report"]
    print(f"  Total: {report['total_championships']}")
    print(f"  Normal: {report['normal']}")
    print(f"  Medium: {report['medium_urgency']}")
    print(f"  High: {report['high_urgency']}")
    print(f"  Overdue: {report['overdue']}")
    print(f"  Vacant: {report['vacant']}")

    print("\nTest 11: Resetting all championships to default requirements...")
    response = requests.post(f"{BASE_URL}/api/test/defense-frequency/reset")
    assert response.status_code == 200
    print(f"  Reset {response.json()['reset_count']} championships")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_defense_frequency_system()
    except AssertionError as exc:
        print(f"\nTEST FAILED: {exc}")
        raise SystemExit(1)
    except Exception as exc:
        if requests is not None and isinstance(exc, requests.exceptions.ConnectionError):
            print(f"\nERROR: Cannot connect to {BASE_URL}")
            print("   Make sure the Flask server is running.")
            raise SystemExit(1)
        print(f"\nUNEXPECTED ERROR: {exc}")
        raise
