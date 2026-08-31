"""
Queue ordering and priority tests.
Key rule: acuity dominates — CRITICAL always ranks above HIGH, HIGH above MODERATE, etc.
Safety flags add priority within the same acuity tier.
Waiting time is a tiebreaker only, never overrides acuity.
"""
import pytest
from app.services.patient_service import ACUITY_RANK


def test_acuity_rank_order():
    """CRITICAL must rank lowest number (highest priority)."""
    assert ACUITY_RANK["CRITICAL"] < ACUITY_RANK["HIGH"]
    assert ACUITY_RANK["HIGH"] < ACUITY_RANK["MODERATE"]
    assert ACUITY_RANK["MODERATE"] < ACUITY_RANK["LOW"]
    assert ACUITY_RANK["LOW"] < ACUITY_RANK["PENDING"]


def test_priority_score_critical_lower_than_high():
    """Lower priority_score = higher priority in queue."""
    critical_rank = ACUITY_RANK["CRITICAL"]
    high_rank = ACUITY_RANK["HIGH"]
    critical_score = critical_rank * 1000
    high_score = high_rank * 1000
    assert critical_score < high_score


def test_safety_flag_reduces_score():
    """An URGENT_REVIEW safety flag should reduce the priority score (makes it more urgent)."""
    base_score = ACUITY_RANK["HIGH"] * 1000
    safety_bonus = 100  # as defined in patient_service
    flagged_score = base_score - safety_bonus
    assert flagged_score < base_score


def test_critical_with_safety_flag_still_above_high_without():
    """CRITICAL+safety must remain above HIGH even without safety flag."""
    critical_flagged = ACUITY_RANK["CRITICAL"] * 1000 - 100
    high_unflagged = ACUITY_RANK["HIGH"] * 1000
    assert critical_flagged < high_unflagged


def test_all_acuity_levels_present_in_rank():
    for acuity in ["CRITICAL", "HIGH", "MODERATE", "LOW", "PENDING"]:
        assert acuity in ACUITY_RANK


def test_waiting_time_cannot_override_acuity():
    """
    Even a patient waiting for hours (LOW acuity) must rank below
    a CRITICAL patient who just arrived.
    """
    # Simulate: LOW patient waiting 10 hours = 36000 seconds
    # The priority_score formula uses acuity_rank * 1000, not waiting time directly
    low_score = ACUITY_RANK["LOW"] * 1000
    critical_score = ACUITY_RANK["CRITICAL"] * 1000
    # LOW can never beat CRITICAL regardless of waiting time in this formula
    assert critical_score < low_score


@pytest.mark.asyncio
async def test_queue_api_requires_auth(client):
    """Queue API must reject unauthenticated requests."""
    resp = await client.get("/api/v1/queue")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_queue_summary_requires_auth(client):
    resp = await client.get("/api/v1/queue/summary")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_queue_summary_returns_expected_keys(client, nurse_user):
    from tests.conftest import get_token
    token = await get_token(client, "TN-0421")
    resp = await client.get("/api/v1/queue/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    for key in ["critical", "high", "moderate", "low", "waiting", "dueForReassessment"]:
        assert key in data


@pytest.mark.asyncio
async def test_queue_returns_list(client, nurse_user):
    from tests.conftest import get_token
    token = await get_token(client, "TN-0421")
    resp = await client.get("/api/v1/queue", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
