"""
Vital sign validation tests.
Covers: technical validity, out-of-range rejection, BP conflict, missing data.
"""
import pytest
from app.services.vital_service import validate_vitals
from app.schemas.assessment import VitalsCreate
from app.core.exceptions import InvalidVitalError


def make_vitals(**kwargs) -> VitalsCreate:
    defaults = dict(
        spo2=98.0, heart_rate=80.0, respiratory_rate=16.0,
        bp_systolic=120.0, bp_diastolic=80.0, temperature=37.0,
        avpu="Alert", source="Manual Entry",
    )
    defaults.update(kwargs)
    return VitalsCreate(**defaults)


def test_valid_vitals_no_errors():
    v = make_vitals()
    errors = validate_vitals(v)
    assert errors == []


def test_spo2_impossible_value():
    """SpO2 of 900 is physically impossible."""
    v = make_vitals(spo2=900.0)
    errors = validate_vitals(v)
    assert any(e.details["field"] == "spo2" for e in errors)


def test_spo2_below_zero():
    v = make_vitals(spo2=-5.0)
    errors = validate_vitals(v)
    assert any(e.details["field"] == "spo2" for e in errors)


def test_heart_rate_impossible():
    """HR of 600 is not physically possible."""
    v = make_vitals(heart_rate=600.0)
    errors = validate_vitals(v)
    assert any(e.details["field"] == "heart_rate" for e in errors)


def test_temperature_too_high():
    """50°C is above the physiological maximum."""
    v = make_vitals(temperature=50.0)
    errors = validate_vitals(v)
    assert any(e.details["field"] == "temperature" for e in errors)


def test_temperature_too_low():
    v = make_vitals(temperature=20.0)
    errors = validate_vitals(v)
    assert any(e.details["field"] == "temperature" for e in errors)


def test_bp_diastolic_greater_than_systolic():
    """Diastolic BP must be less than systolic."""
    v = make_vitals(bp_systolic=80.0, bp_diastolic=100.0)
    errors = validate_vitals(v)
    assert any(e.details["field"] == "bp_diastolic" for e in errors)


def test_bp_equal_systolic_diastolic():
    """Equal diastolic and systolic is also invalid."""
    v = make_vitals(bp_systolic=80.0, bp_diastolic=80.0)
    errors = validate_vitals(v)
    assert any(e.details["field"] == "bp_diastolic" for e in errors)


def test_spo2_91_is_technically_valid():
    """
    SpO2=91% is clinically concerning but TECHNICALLY valid.
    Vital validation must not reject it — clinical rules handle the risk.
    """
    v = make_vitals(spo2=91.0)
    errors = validate_vitals(v)
    assert errors == [], "SpO2=91 is technically valid — clinical rules handle risk"


def test_all_vitals_none_is_valid():
    """All vitals can be None — missing data is supported by design."""
    v = VitalsCreate(
        spo2=None, heart_rate=None, respiratory_rate=None,
        bp_systolic=None, bp_diastolic=None, temperature=None,
        avpu=None, source="Manual Entry",
    )
    errors = validate_vitals(v)
    assert errors == []


def test_multiple_invalid_fields_reported():
    """Multiple invalid fields should all be reported."""
    v = make_vitals(spo2=999.0, temperature=99.0, heart_rate=999.0)
    errors = validate_vitals(v)
    fields = [e.details["field"] for e in errors]
    assert "spo2" in fields
    assert "temperature" in fields
    assert "heart_rate" in fields
