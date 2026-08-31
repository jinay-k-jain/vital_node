"""
Data Quality Service tests.
Verifies completeness scoring and field-level flagging.
CRITICAL: completeness is NOT the same as clinical safety.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from app.services.data_quality_service import compute_data_quality
from app.models.assessment import Assessment, HistoryStatus, AssessmentType
from app.models.vital import Vital, VitalSource, AVPU


def make_assessment(**kwargs) -> Assessment:
    a = Assessment()
    a.assessment_type = AssessmentType.INITIAL
    a.chief_complaint = kwargs.get("chief_complaint", "Chest pain")
    a.confirmed_complaint = kwargs.get("confirmed_complaint", "Chest pain")
    a.symptoms = kwargs.get("symptoms", ["Chest pain"])
    a.danger_signs = kwargs.get("danger_signs", [])
    a.none_observed = kwargs.get("none_observed", True)
    a.history_status = kwargs.get("history_status", HistoryStatus.AVAILABLE)
    a.history_conditions = kwargs.get("conditions", ["Hypertension"])
    a.history_medications = kwargs.get("medications", ["Aspirin"])
    a.history_allergies = kwargs.get("allergies", [])
    return a


def make_vital(spo2=98.0, hr=80.0, rr=16.0, sys=120.0, dia=80.0, temp=37.0,
               avpu=AVPU.ALERT, stale=False) -> Vital:
    v = Vital()
    v.spo2 = spo2
    v.heart_rate = hr
    v.respiratory_rate = rr
    v.bp_systolic = sys
    v.bp_diastolic = dia
    v.temperature = temp
    v.avpu = avpu
    v.source = VitalSource.MANUAL
    if stale:
        v.measured_at = datetime.now(timezone.utc) - timedelta(minutes=45)
    else:
        v.measured_at = datetime.now(timezone.utc)
    return v


def test_complete_data_returns_ok():
    assessment = make_assessment()
    vital = make_vital()
    result = compute_data_quality(assessment, vital)
    assert result.status == "OK"
    assert result.completeness_percent >= 80
    assert result.missing_fields == []


def test_missing_spo2_flagged():
    assessment = make_assessment()
    vital = make_vital(spo2=None)
    result = compute_data_quality(assessment, vital)
    assert any("spo2" in f.lower() or "spo" in f.lower() for f in result.missing_fields)


def test_no_vitals_at_all_is_critical():
    assessment = make_assessment()
    result = compute_data_quality(assessment, None)
    assert result.status in ("WARNING", "CRITICAL")
    assert len(result.missing_fields) > 0


def test_missing_chief_complaint_flagged():
    assessment = make_assessment(chief_complaint=None, confirmed_complaint=None)
    vital = make_vital()
    result = compute_data_quality(assessment, vital)
    assert any("complaint" in f.lower() for f in result.missing_fields)


def test_stale_vitals_flagged():
    assessment = make_assessment()
    vital = make_vital(stale=True)
    result = compute_data_quality(assessment, vital)
    assert len(result.stale_fields) > 0 or any("old" in w.lower() or "stale" in w.lower() for w in result.warnings)


def test_bp_conflict_flagged():
    """Diastolic >= systolic is a data conflict."""
    assessment = make_assessment()
    vital = make_vital(sys=80.0, dia=100.0)
    result = compute_data_quality(assessment, vital)
    assert len(result.conflicting_fields) > 0 or len(result.invalid_fields) > 0


def test_completeness_100_percent_does_not_mean_safe():
    """
    Explicitly verify the design principle:
    A fully complete record can describe a critically ill patient.
    Completeness score has nothing to do with clinical safety.
    """
    assessment = make_assessment()
    vital = make_vital(spo2=85.0, hr=140.0, sys=78.0)  # clearly critical vitals
    result = compute_data_quality(assessment, vital)
    # Should be complete (all fields present)
    assert result.completeness_percent >= 80
    # But safety is NOT evaluated here - this is data quality only
    assert "clinical" not in result.status.lower()


def test_missing_symptoms_flagged():
    assessment = make_assessment(symptoms=[])
    vital = make_vital()
    result = compute_data_quality(assessment, vital)
    assert any("symptom" in f.lower() for f in result.missing_fields)


def test_danger_signs_not_recorded_flagged():
    """Neither danger signs nor none_observed set."""
    assessment = make_assessment(danger_signs=[], none_observed=False)
    vital = make_vital()
    result = compute_data_quality(assessment, vital)
    assert any("danger" in f.lower() for f in result.missing_fields)


def test_completeness_between_0_and_1():
    assessment = make_assessment()
    vital = make_vital()
    result = compute_data_quality(assessment, vital)
    assert 0.0 <= result.completeness <= 1.0


def test_completeness_percent_matches_float():
    assessment = make_assessment()
    vital = make_vital()
    result = compute_data_quality(assessment, vital)
    assert result.completeness_percent == int(result.completeness * 100)
