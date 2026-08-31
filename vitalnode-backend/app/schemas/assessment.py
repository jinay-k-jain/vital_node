"""
Assessment + Vitals input/output schemas.
All vital fields are Optional - missing data is supported by design.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, model_validator


# ── Vitals input ───────────────────────────────────────────────────────────

class VitalsCreate(BaseModel):
    spo2: Optional[float] = Field(None, ge=0, le=100, description="SpO2 %")
    heart_rate: Optional[float] = Field(None, ge=0, le=500, description="Heart rate bpm")
    respiratory_rate: Optional[float] = Field(None, ge=0, le=100, description="Respiratory rate /min")
    bp_systolic: Optional[float] = Field(None, ge=0, le=400, description="Systolic BP mmHg")
    bp_diastolic: Optional[float] = Field(None, ge=0, le=300, description="Diastolic BP mmHg")
    temperature: Optional[float] = Field(None, ge=25.0, le=45.0, description="Temperature °C")
    avpu: Optional[Literal["Alert", "Voice", "Pain", "Unresponsive"]] = None
    source: Literal["Manual Entry", "Connected Device", "Imported"] = "Manual Entry"
    device_id: Optional[str] = None
    measured_at: Optional[datetime] = None  # defaults to now if omitted


# ── PatientHistory input ───────────────────────────────────────────────────

class PatientHistoryCreate(BaseModel):
    available: bool = True
    conditions: Optional[List[str]] = None
    medications: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    notes: Optional[str] = None


# ── Assessment create (mirrors NewAssessmentScreen form) ───────────────────

class AssessmentCreate(BaseModel):
    """Full assessment submission matching all fields in NewAssessmentScreen."""

    # Patient demographics (for initial encounter)
    age: int = Field(..., ge=0, le=130)
    sex: Literal["Male", "Female", "Other", "Unknown"]
    name: Optional[str] = None
    # When supplied, this submission is a reassessment of the existing
    # encounter, not a new patient arrival.
    reassessment_encounter_id: Optional[str] = None
    arrival_mode: Literal["walk-in", "ambulance", "referral", "transfer", "other"] = "walk-in"
    is_pregnant: Optional[bool] = None

    # Danger signs
    danger_signs: List[str] = Field(default_factory=list)
    none_observed: bool = False

    # Vitals
    vitals: VitalsCreate

    # Chief complaint
    chief_complaint: Optional[str] = None
    voice_transcript: Optional[str] = None

    # Symptoms (nurse-confirmed)
    symptoms: List[str] = Field(default_factory=list)

    # History
    history: PatientHistoryCreate = Field(default_factory=PatientHistoryCreate)

    @model_validator(mode="after")
    def validate_danger_signs(self):
        """none_observed and any danger sign are mutually exclusive."""
        if self.none_observed and self.danger_signs:
            raise ValueError(
                "none_observed cannot be True when danger_signs are selected. "
                "Clear danger signs before selecting 'None observed'."
            )
        return self


# ── Nurse decision input ────────────────────────────────────────────────────

OVERRIDE_REASONS = [
    "Clinical deterioration",
    "Additional observation",
    "AI recommendation inconsistent with presentation",
    "Missing information",
    "Other",
]


class NurseDecisionCreate(BaseModel):
    action: Literal["ACCEPTED", "OVERRIDE", "REASSESS_REQUESTED"]
    final_acuity: Literal["CRITICAL", "HIGH", "MODERATE", "LOW"]
    override_reason: Optional[str] = None
    override_note: Optional[str] = None

    @model_validator(mode="after")
    def validate_override_fields(self):
        if self.action == "OVERRIDE":
            if not self.override_reason:
                raise ValueError("override_reason is required when action is OVERRIDE")
            if self.override_reason not in OVERRIDE_REASONS:
                raise ValueError(f"override_reason must be one of: {OVERRIDE_REASONS}")
        return self


# ── Data quality response ──────────────────────────────────────────────────

class DataQualityResponse(BaseModel):
    status: Literal["OK", "WARNING", "CRITICAL"]
    completeness: float  # 0.0 - 1.0
    completeness_percent: int
    missing_fields: List[str]
    invalid_fields: List[str]
    stale_fields: List[str]
    conflicting_fields: List[str]
    warnings: List[str]
