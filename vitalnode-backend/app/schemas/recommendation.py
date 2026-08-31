"""Recommendation and safety gate response schemas."""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class FeatureContribution(BaseModel):
    feature: str
    value: str
    impact: str   # HIGH | MEDIUM | LOW
    direction: str  # INCREASING | DECREASING


class RecommendationResponse(BaseModel):
    """Full AI pipeline output - matches frontend AcuityRecommendation type."""
    recommendation_id: str
    assessment_id: str
    encounter_id: str
    acuity: str
    confidence: float
    data_completeness: float
    safety_status: str
    safety_flag: Optional[str]
    key_reasons: List[str]
    clinical_rules: List[str]
    top_factors: List[FeatureContribution]
    model_version: str
    model_status: str
    is_conservative: bool
    recommended_at: datetime


class SafetyGateOutput(BaseModel):
    status: str  # NORMAL | VERIFY | URGENT_REVIEW
    reasons: List[str]
    triggered_by: List[str]  # which rules/conditions triggered it


class NurseDecisionResponse(BaseModel):
    decision_id: str
    assessment_id: str
    action: str
    final_acuity: str
    override_reason: Optional[str]
    override_note: Optional[str]
    nurse_id: str
    nurse_name: str
    decided_at: datetime


class AuditEntryResponse(BaseModel):
    """Matches the frontend AuditEntry type."""
    id: str
    timestamp: datetime
    patient_id: str
    patient_display_id: str
    event_type: str
    ai_recommendation: Optional[str]
    ai_confidence: Optional[float]
    safety_flag: Optional[str]
    nurse_action: Optional[str]
    final_acuity: Optional[str]
    override_reason: Optional[str]
    model_version: Optional[str]
    nurse_id: Optional[str]
    nurse_name: Optional[str]
    notes: Optional[str]


class NotificationResponse(BaseModel):
    """Matches the frontend Notification type."""
    id: str
    type: str
    message: str
    patient_id: Optional[str]
    patient_display_id: Optional[str]
    timestamp: datetime
    read: bool
    urgent: bool


class TimelineEventResponse(BaseModel):
    """Matches the frontend TimelineEvent type."""
    id: str
    timestamp: datetime
    type: str
    title: str
    description: str
    acuity: Optional[str] = None
    confidence: Optional[float] = None
