"""
Danger signs validation tests.
Key rule: none_observed cannot coexist with any selected danger sign.
"""
import pytest
from pydantic import ValidationError
from app.schemas.assessment import AssessmentCreate, VitalsCreate


def base_payload(**kwargs) -> dict:
    defaults = {
        "age": 35,
        "sex": "Male",
        "arrival_mode": "walk-in",
        "danger_signs": [],
        "none_observed": False,
        "vitals": {
            "spo2": 98.0, "heart_rate": 80.0, "respiratory_rate": 16.0,
            "bp_systolic": 120.0, "bp_diastolic": 80.0, "temperature": 37.0,
            "avpu": "Alert", "source": "Manual Entry",
        },
        "symptoms": ["Headache"],
        "chief_complaint": "Headache",
        "history": {"available": False},
    }
    defaults.update(kwargs)
    return defaults


def test_none_observed_with_no_danger_signs_valid():
    payload = base_payload(danger_signs=[], none_observed=True)
    obj = AssessmentCreate(**payload)
    assert obj.none_observed is True
    assert obj.danger_signs == []


def test_danger_signs_without_none_observed_valid():
    payload = base_payload(danger_signs=["Breathing difficulty"], none_observed=False)
    obj = AssessmentCreate(**payload)
    assert "Breathing difficulty" in obj.danger_signs
    assert obj.none_observed is False


def test_none_observed_plus_danger_sign_raises_error():
    """none_observed=True + any danger sign must raise a validation error."""
    payload = base_payload(
        danger_signs=["Breathing difficulty"],
        none_observed=True,
    )
    with pytest.raises(ValidationError) as exc_info:
        AssessmentCreate(**payload)
    errors = exc_info.value.errors()
    assert any("none_observed" in str(e).lower() or "danger" in str(e).lower() for e in errors)


def test_none_observed_plus_multiple_danger_signs_raises():
    payload = base_payload(
        danger_signs=["Breathing difficulty", "Seizure", "Major trauma"],
        none_observed=True,
    )
    with pytest.raises(ValidationError):
        AssessmentCreate(**payload)


def test_all_danger_sign_options_accepted():
    """All 6 valid danger sign strings must be accepted."""
    valid_signs = [
        "Breathing difficulty",
        "Severe bleeding",
        "Altered consciousness",
        "Seizure",
        "Major trauma",
        "Severe distress",
    ]
    payload = base_payload(danger_signs=valid_signs, none_observed=False)
    obj = AssessmentCreate(**payload)
    assert len(obj.danger_signs) == 6


def test_empty_danger_signs_without_none_observed_valid():
    """Neither danger signs nor none_observed is a valid intermediate state during data entry."""
    payload = base_payload(danger_signs=[], none_observed=False)
    obj = AssessmentCreate(**payload)
    assert obj.danger_signs == []
    assert obj.none_observed is False


def test_missing_vitals_still_valid():
    """Assessment must succeed even with all vitals missing."""
    payload = base_payload(
        vitals={"source": "Manual Entry"},
        danger_signs=[],
        none_observed=True,
    )
    obj = AssessmentCreate(**payload)
    assert obj.vitals.spo2 is None
    assert obj.vitals.heart_rate is None


def test_all_required_fields_present():
    payload = base_payload()
    obj = AssessmentCreate(**payload)
    assert obj.age == 35
    assert obj.sex == "Male"
