"""
Safety Gate Service.
Final check before a recommendation is issued to the nurse.
Inputs: fused recommendation + data quality + context.
Output: final safety_status with full explanation.

The safety gate is the LAST line of defense before the AI recommendation
reaches the nurse. It can only escalate, never downgrade safety status.
"""
from dataclasses import dataclass, field
from typing import List

from app.services.decision_fusion import FusedRecommendation
from app.services.data_quality_service import DataQualityResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SafetyGateResult:
    status: str               # NORMAL | VERIFY | URGENT_REVIEW
    reasons: List[str] = field(default_factory=list)
    triggered_by: List[str] = field(default_factory=list)


SAFETY_ORDER = {"NORMAL": 0, "VERIFY": 1, "URGENT_REVIEW": 2}


def run_safety_gate(
    fused: FusedRecommendation,
    data_quality: DataQualityResponse,
    has_danger_signs: bool,
    is_pediatric: bool,
) -> SafetyGateResult:
    """
    Run the safety gate on the fused recommendation.
    Returns SafetyGateResult with final safety status and explanations.
    Can only escalate the status from the fused recommendation.
    """
    result = SafetyGateResult(status=fused.safety_status)

    # ── Pass through clinical rules safety status ───────────────────────────
    if fused.safety_status == "URGENT_REVIEW":
        result.reasons.append("Clinical safety rules require urgent review")
        result.triggered_by.append("clinical_rules")

    # ── Escalate on very low confidence ────────────────────────────────────
    if fused.confidence < 50 and _safety_rank(result.status) < _safety_rank("VERIFY"):
        result.status = "VERIFY"
        result.reasons.append(f"Model confidence is low ({fused.confidence}%) — verification recommended")
        result.triggered_by.append("low_confidence")

    # ── Escalate on poor data quality ──────────────────────────────────────
    if data_quality.status == "CRITICAL" and _safety_rank(result.status) < _safety_rank("VERIFY"):
        result.status = "VERIFY"
        result.reasons.append("Critical data quality issues — important information missing")
        result.triggered_by.append("data_quality")

    # ── Conflicting data always triggers VERIFY ─────────────────────────────
    if data_quality.conflicting_fields and _safety_rank(result.status) < _safety_rank("VERIFY"):
        result.status = "VERIFY"
        result.reasons.append(
            f"Conflicting data detected: {', '.join(data_quality.conflicting_fields)}"
        )
        result.triggered_by.append("conflicting_data")

    # ── Danger signs with low acuity — escalate ────────────────────────────
    if has_danger_signs and fused.acuity in ("LOW", "MODERATE") and _safety_rank(result.status) < _safety_rank("VERIFY"):
        result.status = "VERIFY"
        result.reasons.append("Danger signs present — verification recommended despite lower acuity estimate")
        result.triggered_by.append("danger_signs_mismatch")

    # ── Pediatric + URGENT_REVIEW ──────────────────────────────────────────
    if is_pediatric and fused.acuity == "CRITICAL":
        _maybe_escalate(result, "URGENT_REVIEW")
        result.reasons.append("Pediatric patient with critical acuity — urgent review required")
        result.triggered_by.append("pediatric_critical")

    # ── Model unavailable ──────────────────────────────────────────────────
    if fused.model_status == "UNAVAILABLE":
        _maybe_escalate(result, "VERIFY")
        result.reasons.append("AI model unavailable — manual clinical assessment required")
        result.triggered_by.append("model_unavailable")

    # If no reasons added (all clear)
    if not result.reasons:
        result.reasons.append("No safety gate triggers activated")

    logger.info(
        "safety_gate_result",
        status=result.status,
        triggers=result.triggered_by,
        acuity=fused.acuity,
    )
    return result


def _safety_rank(status: str) -> int:
    return SAFETY_ORDER.get(status, 0)


def _maybe_escalate(result: SafetyGateResult, new_status: str) -> None:
    if _safety_rank(new_status) > _safety_rank(result.status):
        result.status = new_status
