"""
Data Quality Service.
Evaluates completeness and flags issues with the assessment data.
IMPORTANT: data completeness is NOT the same as clinical safety.
A 100%-complete record can still indicate a critically ill patient.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from app.models.vital import Vital
from app.models.assessment import Assessment
from app.schemas.assessment import DataQualityResponse


# Fields considered "critical" for high-quality assessment
CRITICAL_VITAL_FIELDS = ["spo2", "heart_rate", "respiratory_rate", "bp_systolic", "bp_diastolic", "temperature"]
IMPORTANT_FIELDS = ["avpu"]
CONTEXT_FIELDS = ["chief_complaint", "symptoms", "danger_signs"]

STALE_MINUTES = 30


def compute_data_quality(
    assessment: Assessment,
    latest_vital: Optional[Vital],
) -> DataQualityResponse:
    """
    Produce a DataQualityResponse describing the completeness and integrity
    of the current assessment.
    """
    missing: List[str] = []
    invalid: List[str] = []
    stale: List[str] = []
    conflicts: List[str] = []
    warnings: List[str] = []

    total_fields = len(CRITICAL_VITAL_FIELDS) + len(IMPORTANT_FIELDS) + len(CONTEXT_FIELDS)
    present = 0

    # ── Vital presence ─────────────────────────────────────────────────────
    if not latest_vital:
        missing.extend(CRITICAL_VITAL_FIELDS)
        warnings.append("No vital signs recorded")
    else:
        for field in CRITICAL_VITAL_FIELDS:
            val = getattr(latest_vital, field, None)
            if val is None:
                missing.append(field.replace("_", " ").title())
            else:
                present += 1

        for field in IMPORTANT_FIELDS:
            val = getattr(latest_vital, field, None)
            if val is None:
                missing.append(field.upper())
            else:
                present += 1

        # Staleness check
        if latest_vital.measured_at:
            measured = latest_vital.measured_at
            if measured.tzinfo is None:
                measured = measured.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - measured
            if age > timedelta(minutes=STALE_MINUTES):
                stale.append("Vital signs")
                warnings.append(f"Vital signs are {int(age.total_seconds() // 60)} minutes old")

        # BP conflict check
        if latest_vital.bp_systolic is not None and latest_vital.bp_diastolic is not None:
            if latest_vital.bp_diastolic >= latest_vital.bp_systolic:
                conflicts.append("Blood pressure: diastolic >= systolic")
                invalid.append("Blood pressure")

    # ── Context fields ─────────────────────────────────────────────────────
    if not assessment.confirmed_complaint and not assessment.chief_complaint:
        missing.append("Chief complaint")
    else:
        present += 1

    if not assessment.symptoms or len(assessment.symptoms) == 0:
        missing.append("Symptoms")
    else:
        present += 1

    danger_recorded = (
        assessment.none_observed or
        (assessment.danger_signs and len(assessment.danger_signs) > 0)
    )
    if not danger_recorded:
        missing.append("Danger signs assessment")
    else:
        present += 1

    # ── Compute completeness ──────────────────────────────────────────────
    completeness = present / total_fields if total_fields > 0 else 0.0
    completeness_pct = int(completeness * 100)

    if completeness_pct >= 80:
        status = "OK"
    elif completeness_pct >= 50:
        status = "WARNING"
        warnings.append("Important clinical information is missing")
    else:
        status = "CRITICAL"
        warnings.append("Significant information missing — AI confidence will be reduced")

    if conflicts:
        status = "WARNING" if status == "OK" else status
        warnings.append("Conflicting data detected — review required")

    return DataQualityResponse(
        status=status,
        completeness=round(completeness, 3),
        completeness_percent=completeness_pct,
        missing_fields=missing,
        invalid_fields=invalid,
        stale_fields=stale,
        conflicting_fields=conflicts,
        warnings=warnings,
    )
