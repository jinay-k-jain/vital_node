from app.api.v1.utils import ev
"""
Assessment Service - orchestrates the full AI pipeline:

  Data → Validation → Normalization → Clinical Rules → ML Engine
  → Decision Fusion → Safety Gate → Recommendation → Audit

This is the core of the VitalNode backend.
"""
from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.encounter import Encounter, Acuity, SafetyStatus
from app.models.recommendation import AIRecommendation, NurseDecision, ModelStatus
from app.ml.interface import MLFeatures
from app.ml.mock_engine import MockMLEngine
from app.ml.xgboost_engine import XGBoostMLEngine
from app.services.data_quality_service import compute_data_quality
from app.services.clinical_rules import evaluate_clinical_rules
from app.services.decision_fusion import fuse
from app.services.safety_gate import run_safety_gate
from app.services.vital_service import get_latest_vital, get_vital_history
from app.services.patient_service import update_encounter_priority, set_reassessment_due
from app.services.audit_service import record_audit_event
from app.schemas.assessment import NurseDecisionCreate
from app.core.config import get_settings
from app.core.exceptions import MLUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Set to None — will be loaded fresh on first prediction request
# If you change ML_ENGINE in .env, restart the server to reload
_ml_engine_instance = None


def reset_ml_engine():
    """Call this to force the ML engine to reload (useful after config changes)."""
    global _ml_engine_instance
    _ml_engine_instance = None

def _get_ml_engine():
    """Return singleton ML engine instance. Loads once at first call."""
    global _ml_engine_instance
    if _ml_engine_instance is not None:
        return _ml_engine_instance

    if settings.ml_engine == "xgboost":
        try:
            engine = XGBoostMLEngine()
            if engine.is_available():
                _ml_engine_instance = engine
                logger.info("ml_engine_active", version=engine.get_version())
                return _ml_engine_instance
            else:
                logger.error(
                    "xgboost_engine_not_available",
                    hint="Check MODEL_PATH in .env and that the file exists",
                    model_path=settings.model_path,
                )
        except Exception as exc:
            logger.error("xgboost_engine_exception", error=str(exc))

        logger.warning("falling_back_to_mock_engine")

    _ml_engine_instance = MockMLEngine()
    logger.info("using_mock_ml_engine")
    return _ml_engine_instance


def _enum_val(v) -> str:
    """Return the string value of an enum or pass through a plain string."""
    return v.value if hasattr(v, 'value') else str(v)


def _build_features(assessment, encounter, latest_vital, completeness: float, previous_vital=None) -> MLFeatures:
    """Build the normalised MLFeatures vector from DB objects."""
    from datetime import timezone as _tz
    now = datetime.now(timezone.utc)

    # Detect history clues
    conditions = assessment.history_conditions or []
    medications = assessment.history_medications or []

    cardiac_keywords = {"hypertension", "heart", "ischaemic", "cardiac", "cad", "mi", "angina"}
    resp_keywords = {"asthma", "copd", "respiratory", "lung"}
    anticoag_keywords = {"warfarin", "rivaroxaban", "apixaban", "heparin", "anticoagulant"}

    has_cardiac = any(any(kw in c.lower() for kw in cardiac_keywords) for c in conditions)
    has_resp = any(any(kw in c.lower() for kw in resp_keywords) for c in conditions)
    on_anticoag = any(any(kw in m.lower() for kw in anticoag_keywords) for m in medications)

    # Extract avpu string — may be enum or plain string
    avpu_str = None
    if latest_vital and latest_vital.avpu:
        avpu_str = _enum_val(latest_vital.avpu)

    # ── Compute timing fields ──────────────────────────────────────────────
    def to_minutes(dt) -> Optional[float]:
        """Convert a datetime to minutes-ago. Returns None if dt is None."""
        if dt is None:
            return None
        aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return round((now - aware).total_seconds() / 60, 2)

    # How long patient has been waiting (arrival → now)
    waiting_time_minutes = to_minutes(encounter.arrival_time)

    # Age of the newly submitted vital (normally near zero).
    minutes_since_last_vital = to_minutes(latest_vital.measured_at) if latest_vital else None

    # Reassessment interval and changes compared with the immediately prior
    # vital.  These are intentionally absent for a first assessment.
    minutes_since_previous_vital = None
    delta_heart_rate = None
    delta_spo2 = None
    if latest_vital and previous_vital:
        current_time = latest_vital.measured_at
        previous_time = previous_vital.measured_at
        if current_time and previous_time:
            current_aware = current_time if current_time.tzinfo else current_time.replace(tzinfo=timezone.utc)
            previous_aware = previous_time if previous_time.tzinfo else previous_time.replace(tzinfo=timezone.utc)
            minutes_since_previous_vital = round((current_aware - previous_aware).total_seconds() / 60, 2)
        if latest_vital.heart_rate is not None and previous_vital.heart_rate is not None:
            delta_heart_rate = latest_vital.heart_rate - previous_vital.heart_rate
        if latest_vital.spo2 is not None and previous_vital.spo2 is not None:
            delta_spo2 = latest_vital.spo2 - previous_vital.spo2

    # How long ago the assessment was submitted
    minutes_since_last_assessment = to_minutes(assessment.submitted_at)

    # Minutes until/since reassessment due (negative = overdue)
    minutes_until_reassessment_due = None
    if encounter.reassessment_due:
        rd = encounter.reassessment_due
        aware_rd = rd if rd.tzinfo else rd.replace(tzinfo=timezone.utc)
        minutes_until_reassessment_due = round((aware_rd - now).total_seconds() / 60, 2)

    # Is this a reassessment?
    is_reassessment = (encounter.reassessment_count or 0) > 0

    return MLFeatures(
        age=encounter.patient.age if encounter.patient else None,
        # .sex and .age_group may be enum instances OR plain strings — handle both
        sex=_enum_val(encounter.patient.sex) if encounter.patient else None,
        age_group=_enum_val(encounter.patient.age_group) if encounter.patient else None,
        is_pregnant=encounter.is_pregnant,
        spo2=latest_vital.spo2 if latest_vital else None,
        heart_rate=latest_vital.heart_rate if latest_vital else None,
        respiratory_rate=latest_vital.respiratory_rate if latest_vital else None,
        bp_systolic=latest_vital.bp_systolic if latest_vital else None,
        bp_diastolic=latest_vital.bp_diastolic if latest_vital else None,
        temperature=latest_vital.temperature if latest_vital else None,
        avpu=avpu_str,
        chief_complaint=assessment.confirmed_complaint or assessment.chief_complaint,
        symptoms=assessment.symptoms or [],
        danger_signs=assessment.danger_signs or [],
        none_observed=assessment.none_observed,
        history_available=_enum_val(assessment.history_status) == "AVAILABLE",
        has_cardiac_history=has_cardiac,
        has_respiratory_history=has_resp,
        on_anticoagulants=on_anticoag,
        arrival_mode=_enum_val(encounter.arrival_mode) if encounter.arrival_mode else None,
        data_completeness=completeness / 100,
        history_notes=assessment.history_notes,  # rich pre-loaded text for Gemini
        use_local_nlp=encounter.is_surge_patient,
        nlp_extraction=(assessment.raw_extracted_symptoms
                        if isinstance(assessment.raw_extracted_symptoms, dict) else None),
        # ── Timing ────────────────────────────────────────────────────────
        waiting_time_minutes=waiting_time_minutes,
        minutes_since_last_vital=minutes_since_last_vital,
        minutes_since_last_assessment=minutes_since_last_assessment,
        reassessment_count=encounter.reassessment_count or 0,
        is_reassessment=is_reassessment,
        minutes_until_reassessment_due=minutes_until_reassessment_due,
        minutes_since_previous_vital=minutes_since_previous_vital,
        delta_heart_rate=delta_heart_rate,
        delta_spo2=delta_spo2,
    )


async def run_ai_assessment(
    db: AsyncSession,
    assessment: Assessment,
    encounter: Encounter,
    submitted_by_user_id: Optional[uuid.UUID] = None,
    submitted_by_staff_id: Optional[str] = None,
    submitted_by_name: Optional[str] = None,
    submitted_by_role: Optional[str] = None,
) -> AIRecommendation:
    """
    Full AI pipeline for an assessment.
    Stores the recommendation. A recommendation is not a queue admission:
    encounter priority changes only after the nurse accepts or overrides it.
    """
    now = datetime.now(timezone.utc)

    # 1. Query rather than trusting a relationship that may have been loaded
    # before a reassessment vital was inserted in this request.
    vital_history = await get_vital_history(db, encounter.id, limit=2)
    latest_vital = vital_history[0] if vital_history else None
    previous_vital = vital_history[1] if len(vital_history) > 1 else None

    # 2. Data quality
    data_quality = compute_data_quality(assessment, latest_vital)

    # 3. Build features
    age_group = ev(encounter.patient.age_group) if encounter.patient else "ADULT"
    features = _build_features(
        assessment, encounter, latest_vital, data_quality.completeness_percent,
        previous_vital=previous_vital,
    )

    # 4. Clinical rules (pre-ML)
    rules_output = evaluate_clinical_rules(features)

    # 5. ML prediction
    ml_prediction = None
    try:
        engine = _get_ml_engine()
        ml_prediction = engine.predict(features)
    except (MLUnavailableError, NotImplementedError) as exc:
        logger.warning("ml_prediction_failed", reason=str(exc))
        # ml_prediction stays None; decision_fusion handles this

    # Persist the original extraction so a reassessment with unchanged text can
    # reuse it instead of making another external NLP request.
    if ml_prediction and ml_prediction.nlp_extraction:
        assessment.raw_extracted_symptoms = ml_prediction.nlp_extraction

    # 6. Decision fusion
    fused = fuse(
        ml_prediction=ml_prediction,
        rules_output=rules_output,
        data_completeness_percent=data_quality.completeness_percent,
        age_group=age_group,
    )

    # 7. Safety gate
    has_danger = bool(assessment.danger_signs) and not assessment.none_observed
    is_pediatric = age_group == "PEDIATRIC"
    gate_result = run_safety_gate(fused, data_quality, has_danger, is_pediatric)

    # 8. Build top_factors for frontend
    top_factors = [
        {
            "feature": f.get("feature", ""),
            "value": f.get("value", ""),
            "impact": f.get("impact", "MEDIUM"),
            "direction": f.get("direction", "INCREASING"),
        }
        for f in fused.top_factors
    ]

    model_status_enum = ModelStatus.MOCK if fused.model_status == "MOCK" else (
        ModelStatus.UNAVAILABLE if fused.model_status == "UNAVAILABLE" else ModelStatus.ACTIVE
    )

    # 9. Persist recommendation
    recommendation = AIRecommendation(
        assessment_id=assessment.id,
        encounter_id=encounter.id,
        acuity=Acuity(fused.acuity),
        confidence=fused.confidence,
        data_completeness=fused.data_completeness,
        safety_status=SafetyStatus(gate_result.status),
        safety_flag=fused.safety_flag,
        key_reasons=fused.key_reasons,
        clinical_rules=fused.clinical_rules,
        top_factors=top_factors,
        model_version=fused.model_version,
        model_status=model_status_enum,
        clinical_rule_version=rules_output.rule_version,
        is_conservative=fused.is_conservative,
        recommended_at=now,
    )
    db.add(recommendation)
    await db.flush()
    # Keep the in-session object graph current for callers that immediately
    # record a decision (the synthetic surge flow does this after scoring).
    assessment.ai_recommendation = recommendation

    # 10. Audit. Do not alter queue acuity/status until a nurse decision.
    await record_audit_event(
        db=db,
        event_type="AI_PREDICTION",
        user_id=submitted_by_user_id,
        user_staff_id=submitted_by_staff_id,
        user_name=submitted_by_name,
        user_role=submitted_by_role,
        patient_id=encounter.patient_id,
        patient_display_id=encounter.patient.display_id if encounter.patient else None,
        encounter_id=encounter.id,
        assessment_id=assessment.id,
        ai_recommendation=fused.acuity,
        ai_confidence=fused.confidence,
        safety_flag=fused.safety_flag,
        model_version=fused.model_version,
    )

    logger.info(
        "ai_assessment_complete",
        acuity=fused.acuity,
        confidence=fused.confidence,
        safety=gate_result.status,
    )
    return recommendation


async def record_nurse_decision(
    db: AsyncSession,
    assessment: Assessment,
    encounter: Encounter,
    decision: NurseDecisionCreate,
    nurse_user_id: uuid.UUID,
    nurse_staff_id: str,
    nurse_name: str,
    nurse_role: str,
) -> NurseDecision:
    """
    Store the nurse's final decision (ACCEPT | OVERRIDE | REASSESS_REQUESTED).
    AI recommendation is NEVER deleted or modified.
    """
    now = datetime.now(timezone.utc)

    nurse_decision = NurseDecision(
        assessment_id=assessment.id,
        nurse_id=nurse_user_id,
        action=decision.action,
        final_acuity=Acuity(decision.final_acuity),
        override_reason=decision.override_reason,
        override_note=decision.override_note,
        decided_at=now,
    )
    db.add(nurse_decision)
    await db.flush()

    # Update encounter acuity to nurse-confirmed value and start/restart its timer.
    safety = assessment.ai_recommendation.safety_status if assessment.ai_recommendation else encounter.safety_status
    await update_encounter_priority(db, encounter, Acuity(decision.final_acuity), safety)
    await set_reassessment_due(db, encounter, decision.final_acuity)

    # Audit
    await record_audit_event(
        db=db,
        event_type=decision.action,
        user_id=nurse_user_id,
        user_staff_id=nurse_staff_id,
        user_name=nurse_name,
        user_role=nurse_role,
        patient_id=encounter.patient_id,
        patient_display_id=encounter.patient.display_id if encounter.patient else None,
        encounter_id=encounter.id,
        assessment_id=assessment.id,
        ai_recommendation=ev(assessment.ai_recommendation.acuity) if assessment.ai_recommendation else None,
        ai_confidence=assessment.ai_recommendation.confidence if assessment.ai_recommendation else None,
        nurse_action=decision.action,
        final_acuity=decision.final_acuity,
        override_reason=decision.override_reason,
        model_version=assessment.ai_recommendation.model_version if assessment.ai_recommendation else None,
        notes=decision.override_note,
    )

    return nurse_decision
