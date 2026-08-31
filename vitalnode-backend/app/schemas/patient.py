"""
Patient + Encounter schemas.
Shapes mirror the frontend Patient type so the API response can be consumed directly.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


# ── Patient ────────────────────────────────────────────────────────────────

class PatientCreate(BaseModel):
    name: Optional[str] = None
    age: int = Field(..., ge=0, le=130)
    sex: str  # "Male" | "Female" | "Other" | "Unknown"
    is_simulation: bool = True

    model_config = {"json_schema_extra": {"example": {"age": 45, "sex": "Male"}}}


class PatientResponse(BaseModel):
    id: str
    display_id: str
    name: Optional[str]
    age: int
    sex: str
    age_group: str
    is_simulation: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PatientSearchResult(BaseModel):
    id: str
    display_id: str
    name: Optional[str]
    age: int
    sex: str
    age_group: str
    encounter_count: int = 0


# ── Vitals (nested in Patient response) ────────────────────────────────────

class VitalsResponse(BaseModel):
    spo2: Optional[float] = None
    heart_rate: Optional[float] = None         # -> heartRate in frontend
    respiratory_rate: Optional[float] = None   # -> respiratoryRate
    bp_systolic: Optional[float] = None        # -> bpSystolic
    bp_diastolic: Optional[float] = None       # -> bpDiastolic
    temperature: Optional[float] = None
    avpu: Optional[str] = None
    timestamp: Optional[datetime] = None
    source: Optional[str] = None
    device_id: Optional[str] = None

    model_config = {"from_attributes": True}


# ── PatientHistory (nested) ────────────────────────────────────────────────

class PatientHistoryResponse(BaseModel):
    available: bool
    conditions: Optional[List[str]] = None
    medications: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    notes: Optional[str] = None


# ── FeatureContribution (nested in AIRecommendation) ───────────────────────

class FeatureContributionResponse(BaseModel):
    feature: str
    value: str
    impact: str   # "HIGH" | "MEDIUM" | "LOW"
    direction: str  # "INCREASING" | "DECREASING"


# ── AIRecommendation (nested) ──────────────────────────────────────────────

class AIRecommendationResponse(BaseModel):
    acuity: str
    confidence: float
    safety_status: str            # -> safetyStatus
    safety_flag: Optional[str]    # -> safetyFlag
    data_completeness: float      # -> dataCompleteness
    key_reasons: List[str]        # -> keyReasons
    clinical_rules: List[str]     # -> clinicalRules
    top_factors: List[FeatureContributionResponse]  # -> topFactors
    model_version: str            # -> modelVersion
    timestamp: datetime
    is_conservative: bool         # -> isConservative


# ── NurseDecision (nested) ─────────────────────────────────────────────────

class NurseDecisionResponse(BaseModel):
    action: str
    final_acuity: str             # -> finalAcuity
    override_reason: Optional[str] = None  # -> overrideReason
    override_note: Optional[str] = None    # -> overrideNote
    nurse_id: str                 # -> nurseId
    nurse_name: str               # -> nurseName
    timestamp: datetime


# ── Full Patient shape (mirrors frontend Patient type) ─────────────────────

class FullPatientResponse(BaseModel):
    """
    The canonical patient shape returned to the frontend.
    Field names use camelCase aliases to match the existing frontend contract.
    """
    id: str
    display_id: str = Field(alias="displayId")
    name: Optional[str] = None
    age: int
    sex: str
    age_group: str = Field(alias="ageGroup")
    arrival_mode: str = Field(alias="arrivalMode")
    arrival_time: datetime = Field(alias="arrivalTime")
    is_pregnant: Optional[bool] = Field(None, alias="isPregnant")
    chief_complaint: str = Field(alias="chiefComplaint")
    symptoms: List[str] = []
    danger_signs: List[str] = Field([], alias="dangerSigns")
    vitals: VitalsResponse
    history: PatientHistoryResponse
    current_acuity: str = Field(alias="currentAcuity")
    ai_recommendation: Optional[AIRecommendationResponse] = Field(None, alias="aiRecommendation")
    safety_status: str = Field(alias="safetyStatus")
    status: str
    waiting_time: int = Field(alias="waitingTime")  # seconds
    reassessment_due: Optional[datetime] = Field(None, alias="reassessmentDue")
    reassessment_count: int = Field(alias="reassessmentCount")
    last_updated: datetime = Field(alias="lastUpdated")
    nurse_decision: Optional[NurseDecisionResponse] = Field(None, alias="nurseDecision")
    is_simulation: bool = Field(alias="isSimulation")
    device_connected: bool = Field(alias="deviceConnected")

    model_config = {"populate_by_name": True, "from_attributes": True}
