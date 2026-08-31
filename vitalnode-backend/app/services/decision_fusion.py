"""
Decision Fusion Service.
Combines ML prediction output + clinical rules output + data quality
into a unified final recommendation.

Key guarantee: a clinical URGENT_REVIEW safety rule can never be
silently overridden by a low ML confidence score.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from app.ml.interface import MLPrediction
from app.services.clinical_rules import ClinicalRulesOutput

ACUITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3, "PENDING": 4}


@dataclass
class FusedRecommendation:
    acuity: str
    confidence: float
    safety_status: str           # NORMAL | VERIFY | URGENT_REVIEW
    safety_flag: Optional[str]
    key_reasons: List[str]
    clinical_rules: List[str]
    top_factors: List[dict]
    model_version: str
    model_status: str
    is_conservative: bool
    data_completeness: float     # 0-100


def fuse(
    ml_prediction: Optional[MLPrediction],
    rules_output: ClinicalRulesOutput,
    data_completeness_percent: float,
    age_group: str,
) -> FusedRecommendation:
    """
    Combine ML + clinical rules into a single recommendation.

    Safety guarantee:
    - If clinical rules say URGENT_REVIEW, the final safety_status is URGENT_REVIEW
      regardless of ML confidence.
    - If clinical rules flag a higher-severity acuity than ML, take the more conservative.
    """
    key_reasons: List[str] = []
    clinical_rule_list: List[str] = list(rules_output.matched_rules)
    top_factors: List[dict] = []
    model_version = "mock-v1.0"
    model_status = "MOCK"

    # ── Determine acuity ────────────────────────────────────────────────────
    if ml_prediction and ml_prediction.model_status != "UNAVAILABLE":
        ml_acuity = ml_prediction.acuity
        ml_confidence = ml_prediction.confidence
        model_version = ml_prediction.model_version
        model_status = ml_prediction.model_status
        top_factors = ml_prediction.top_features
        key_reasons.extend(
            [f.get("feature", "") + ": " + f.get("value", "") for f in ml_prediction.top_features]
        )
    else:
        # ML unavailable - fall back to rules-based acuity
        ml_acuity = _rules_to_acuity(rules_output)
        ml_confidence = 50.0  # low confidence when ML is unavailable
        model_status = "UNAVAILABLE"
        key_reasons.append("AI model unavailable — clinical rules applied")

    # ── Apply conservative pathway ─────────────────────────────────────────
    is_conservative = False

    # If rules suggest higher acuity, take the more conservative
    rules_acuity = _rules_to_acuity(rules_output)
    if ACUITY_RANK.get(rules_acuity, 4) < ACUITY_RANK.get(ml_acuity, 4):
        final_acuity = rules_acuity
        is_conservative = True
        key_reasons.insert(0, f"Clinical safety rules escalated acuity to {rules_acuity}")
    else:
        final_acuity = ml_acuity

    # Pediatric pathway - apply conservative flag
    if age_group == "PEDIATRIC":
        is_conservative = True
        clinical_rule_list.append("Pediatric pathway — conservative assessment applied")

    # Low data completeness - reduce confidence and apply conservative
    if data_completeness_percent < 60:
        ml_confidence = min(ml_confidence, 55.0)
        is_conservative = True

    # ── Safety status ───────────────────────────────────────────────────────
    # Clinical rules safety action ALWAYS takes precedence
    safety_status = rules_output.recommended_safety_action

    # If ML confidence is very low, ensure at least VERIFY
    if ml_confidence < 50 and safety_status == "NORMAL":
        safety_status = "VERIFY"

    # ── Safety flag message ─────────────────────────────────────────────────
    safety_flag: Optional[str] = None
    if safety_status != "NORMAL":
        critical_flags = [f.message for f in rules_output.flags if f.severity == "CRITICAL"]
        warn_flags = [f.message for f in rules_output.flags if f.severity == "WARN"]
        all_flag_messages = critical_flags + warn_flags
        if all_flag_messages:
            safety_flag = all_flag_messages[0]
        elif safety_status == "VERIFY":
            safety_flag = "Clinical verification recommended"
        else:
            safety_flag = "Urgent clinical review required"

    # Add any missing-reasons fallback
    if not key_reasons:
        key_reasons = ["Stable presentation — no high-risk signals detected"]

    return FusedRecommendation(
        acuity=final_acuity,
        confidence=round(ml_confidence, 1),
        safety_status=safety_status,
        safety_flag=safety_flag,
        key_reasons=key_reasons,
        clinical_rules=clinical_rule_list,
        top_factors=top_factors,
        model_version=model_version,
        model_status=model_status,
        is_conservative=is_conservative,
        data_completeness=data_completeness_percent,
    )


def _rules_to_acuity(rules_output: ClinicalRulesOutput) -> str:
    """Map safety action to a minimum acuity level."""
    action = rules_output.recommended_safety_action
    if action == "URGENT_REVIEW":
        return "HIGH"  # minimum HIGH when urgent review required
    if action == "VERIFY":
        return "MODERATE"
    return "LOW"
