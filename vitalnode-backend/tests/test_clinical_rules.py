"""
Clinical rules service tests.
Covers: safety escalation, danger signs, AVPU, pediatric pathway,
low data completeness, zero-history + altered consciousness.

IMPORTANT: These tests verify the SAFETY BEHAVIOR of the rule engine,
not clinical accuracy. The rules are prototype-level only.
"""
import pytest
from app.ml.interface import MLFeatures
from app.services.clinical_rules import evaluate_clinical_rules


def base_features(**kwargs) -> MLFeatures:
    defaults = dict(
        age=40, sex="Male", age_group="ADULT",
        spo2=98.0, heart_rate=80.0, respiratory_rate=16.0,
        bp_systolic=120.0, bp_diastolic=80.0, temperature=37.0,
        avpu="Alert", danger_signs=[], none_observed=True,
        history_available=True, has_cardiac_history=False,
        on_anticoagulants=False, data_completeness=0.9,
        symptoms=[], chief_complaint="headache",
    )
    defaults.update(kwargs)
    return MLFeatures(**defaults)


def test_normal_patient_no_flags():
    f = base_features()
    result = evaluate_clinical_rules(f)
    assert result.recommended_safety_action == "NORMAL"
    assert result.flags == []


def test_critical_spo2_triggers_urgent_review():
    f = base_features(spo2=88.0)
    result = evaluate_clinical_rules(f)
    assert result.recommended_safety_action == "URGENT_REVIEW"
    assert any(flag.code == "SPO2_CRITICAL" for flag in result.flags)


def test_low_spo2_triggers_verify():
    f = base_features(spo2=92.0)
    result = evaluate_clinical_rules(f)
    assert result.recommended_safety_action == "VERIFY"
    assert any(flag.code == "SPO2_LOW" for flag in result.flags)


def test_hypotension_triggers_urgent_review():
    f = base_features(bp_systolic=85.0)
    result = evaluate_clinical_rules(f)
    assert result.recommended_safety_action == "URGENT_REVIEW"
    assert any(flag.code == "HYPOTENSION" for flag in result.flags)


def test_shock_pattern_tachycardia_and_hypotension():
    f = base_features(heart_rate=115.0, bp_systolic=95.0)
    result = evaluate_clinical_rules(f)
    assert result.recommended_safety_action == "URGENT_REVIEW"
    assert any(flag.code == "SHOCK_PATTERN" for flag in result.flags)


def test_tachypnoea_triggers_verify():
    f = base_features(respiratory_rate=28.0)
    result = evaluate_clinical_rules(f)
    assert result.recommended_safety_action == "VERIFY"
    assert any(flag.code == "TACHYPNOEA" for flag in result.flags)


def test_unresponsive_triggers_urgent_review():
    f = base_features(avpu="Unresponsive")
    result = evaluate_clinical_rules(f)
    assert result.recommended_safety_action == "URGENT_REVIEW"
    assert any(flag.code == "AVPU_UNRESPONSIVE" for flag in result.flags)


def test_responds_to_pain_triggers_verify():
    f = base_features(avpu="Pain")
    result = evaluate_clinical_rules(f)
    assert result.recommended_safety_action == "VERIFY"
    assert any(flag.code == "AVPU_PAIN" for flag in result.flags)


def test_danger_signs_trigger_verify():
    f = base_features(danger_signs=["Breathing difficulty"], none_observed=False)
    result = evaluate_clinical_rules(f)
    assert result.recommended_safety_action == "VERIFY"
    assert any(flag.code == "DANGER_SIGNS" for flag in result.flags)


def test_anticoagulant_plus_trauma():
    f = base_features(on_anticoagulants=True, danger_signs=["Major trauma"], none_observed=False)
    result = evaluate_clinical_rules(f)
    assert any(flag.code == "ANTICOAG_TRAUMA" for flag in result.flags)


def test_pediatric_tachycardia():
    f = base_features(age=3, age_group="PEDIATRIC", heart_rate=145.0)
    result = evaluate_clinical_rules(f)
    assert any(flag.code == "PEDIATRIC_TACHYCARDIA" for flag in result.flags)
    assert "Pediatric pathway active" in result.matched_rules[0] or any(
        "Pediatric" in r for r in result.matched_rules
    )


def test_low_data_completeness_triggers_verify():
    f = base_features(data_completeness=0.4)
    result = evaluate_clinical_rules(f)
    assert result.recommended_safety_action == "VERIFY"
    assert any(flag.code == "LOW_DATA_COMPLETENESS" for flag in result.flags)


def test_zero_history_altered_consciousness():
    """Zero history + altered consciousness must trigger URGENT_REVIEW."""
    f = base_features(history_available=False, avpu="Unresponsive")
    result = evaluate_clinical_rules(f)
    assert result.recommended_safety_action == "URGENT_REVIEW"
    assert any(flag.code == "ZERO_HISTORY_ALTERED_CONSCIOUSNESS" for flag in result.flags)


def test_safety_action_only_escalates():
    """Safety action must never downgrade — test multiple conditions together."""
    # SpO2 critical (URGENT_REVIEW) + tachypnoea (VERIFY) -> must stay URGENT_REVIEW
    f = base_features(spo2=85.0, respiratory_rate=30.0)
    result = evaluate_clinical_rules(f)
    assert result.recommended_safety_action == "URGENT_REVIEW"


def test_matched_rules_not_empty_when_flags_present():
    f = base_features(spo2=88.0)
    result = evaluate_clinical_rules(f)
    assert len(result.matched_rules) > 0
