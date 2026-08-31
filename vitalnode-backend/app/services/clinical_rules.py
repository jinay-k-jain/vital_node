"""
Clinical Rules Service.
Operates INDEPENDENTLY from the ML model.
Applied both before and after ML prediction.
Flags high-risk patterns that require clinical verification or escalation.

IMPORTANT DISCLAIMER:
These rules are illustrative for the prototype.
They are NOT WHO-certified, NOT clinically validated, and NOT a substitute
for clinical judgment. Production rules must be defined and validated
by qualified clinical staff before deployment.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from app.ml.interface import MLFeatures

RULE_VERSION = "prototype-v1.0"


@dataclass
class ClinicalFlag:
    code: str
    message: str
    severity: str  # "INFO" | "WARN" | "CRITICAL"


@dataclass
class ClinicalRulesOutput:
    flags: List[ClinicalFlag] = field(default_factory=list)
    recommended_safety_action: str = "NORMAL"  # NORMAL | VERIFY | URGENT_REVIEW
    matched_rules: List[str] = field(default_factory=list)
    rule_version: str = RULE_VERSION

    def escalate(self, action: str) -> None:
        """Escalate safety action if new action is more severe."""
        order = {"NORMAL": 0, "VERIFY": 1, "URGENT_REVIEW": 2}
        if order.get(action, 0) > order.get(self.recommended_safety_action, 0):
            self.recommended_safety_action = action


def evaluate_clinical_rules(features: MLFeatures) -> ClinicalRulesOutput:
    """
    Evaluate clinical safety rules against the patient feature set.
    Returns ClinicalRulesOutput with any flags and the safety recommendation.
    """
    out = ClinicalRulesOutput()

    # ── Oxygenation ────────────────────────────────────────────────────────
    if features.spo2 is not None:
        if features.spo2 < 90:
            out.flags.append(ClinicalFlag(
                code="SPO2_CRITICAL",
                message=f"SpO₂ {features.spo2}% — critically low",
                severity="CRITICAL",
            ))
            out.matched_rules.append("Critical oxygenation threshold (<90%)")
            out.escalate("URGENT_REVIEW")
        elif features.spo2 < 94:
            out.flags.append(ClinicalFlag(
                code="SPO2_LOW",
                message=f"SpO₂ {features.spo2}% — below safe threshold",
                severity="WARN",
            ))
            out.matched_rules.append("Low oxygenation warning (<94%)")
            out.escalate("VERIFY")

    # ── Haemodynamic instability ───────────────────────────────────────────
    if features.bp_systolic is not None and features.bp_systolic < 90:
        out.flags.append(ClinicalFlag(
            code="HYPOTENSION",
            message=f"Systolic BP {features.bp_systolic} mmHg — hypotension",
            severity="CRITICAL",
        ))
        out.matched_rules.append("Hypotension detected (systolic <90 mmHg)")
        out.escalate("URGENT_REVIEW")

    if (features.heart_rate is not None and features.bp_systolic is not None
            and features.heart_rate > 110 and features.bp_systolic < 100):
        out.flags.append(ClinicalFlag(
            code="SHOCK_PATTERN",
            message="Tachycardia + hypotension — possible haemodynamic instability",
            severity="CRITICAL",
        ))
        out.matched_rules.append("Haemodynamic instability pattern (HR↑ + BP↓)")
        out.escalate("URGENT_REVIEW")

    # ── Respiratory distress ───────────────────────────────────────────────
    if features.respiratory_rate is not None and features.respiratory_rate > 25:
        out.flags.append(ClinicalFlag(
            code="TACHYPNOEA",
            message=f"Respiratory rate {features.respiratory_rate}/min — elevated",
            severity="WARN",
        ))
        out.matched_rules.append("Tachypnoea (>25/min)")
        out.escalate("VERIFY")

    # ── Altered consciousness ──────────────────────────────────────────────
    if features.avpu:
        if features.avpu == "Unresponsive":
            out.flags.append(ClinicalFlag(
                code="AVPU_UNRESPONSIVE",
                message="Patient unresponsive (AVPU: U)",
                severity="CRITICAL",
            ))
            out.matched_rules.append("Altered consciousness — unresponsive")
            out.escalate("URGENT_REVIEW")
        elif features.avpu == "Pain":
            out.flags.append(ClinicalFlag(
                code="AVPU_PAIN",
                message="Patient responds only to pain (AVPU: P)",
                severity="WARN",
            ))
            out.matched_rules.append("Altered consciousness — responds to pain only")
            out.escalate("VERIFY")
        elif features.avpu == "Voice":
            out.flags.append(ClinicalFlag(
                code="AVPU_VOICE",
                message="Patient responds to voice (AVPU: V)",
                severity="INFO",
            ))
            out.escalate("VERIFY")

    # ── Danger signs ───────────────────────────────────────────────────────
    if features.danger_signs and not features.none_observed:
        dangerous = set(features.danger_signs) - {"none_observed"}
        if dangerous:
            out.flags.append(ClinicalFlag(
                code="DANGER_SIGNS",
                message=f"Danger signs observed: {', '.join(dangerous)}",
                severity="WARN",
            ))
            out.matched_rules.append("Immediate danger signs present")
            out.escalate("VERIFY")

    # ── Anticoagulant + trauma ─────────────────────────────────────────────
    if features.on_anticoagulants and "Major trauma" in features.danger_signs:
        out.flags.append(ClinicalFlag(
            code="ANTICOAG_TRAUMA",
            message="Anticoagulant medication + trauma — elevated bleeding risk",
            severity="WARN",
        ))
        out.matched_rules.append("Anticoagulant + trauma → elevated risk")
        out.escalate("VERIFY")

    # ── Pediatric pathway ──────────────────────────────────────────────────
    if features.age_group == "PEDIATRIC":
        out.matched_rules.append("Pediatric pathway active — age-specific assessment applied")
        # Pediatric HR thresholds are different; flag for conservative treatment
        if features.heart_rate is not None and features.heart_rate > 140:
            out.flags.append(ClinicalFlag(
                code="PEDIATRIC_TACHYCARDIA",
                message=f"HR {features.heart_rate} bpm — elevated by pediatric thresholds",
                severity="WARN",
            ))
            out.escalate("VERIFY")

    # ── Ambiguous presentation + low confidence ────────────────────────────
    if features.data_completeness < 0.6:
        out.flags.append(ClinicalFlag(
            code="LOW_DATA_COMPLETENESS",
            message=f"Data completeness {int(features.data_completeness*100)}% — AI confidence reduced",
            severity="WARN",
        ))
        out.matched_rules.append("Low data completeness → conservative pathway")
        out.escalate("VERIFY")

    # ── Zero history + altered consciousness ──────────────────────────────
    if not features.history_available and features.avpu in ["Pain", "Unresponsive"]:
        out.flags.append(ClinicalFlag(
            code="ZERO_HISTORY_ALTERED_CONSCIOUSNESS",
            message="No history available + altered consciousness — conservative pathway",
            severity="WARN",
        ))
        out.matched_rules.append("Zero-history + altered consciousness → conservative")
        out.escalate("URGENT_REVIEW")

    return out
