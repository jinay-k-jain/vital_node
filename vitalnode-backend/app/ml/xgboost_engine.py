"""
XGBoost ML Engine v2 — wraps core_engine.process_patient()

ESI 1-5 → Acuity mapping:
  ESI 1 → CRITICAL   (immediate, life-threatening)
  ESI 2 → HIGH       (emergent)
  ESI 3 → MODERATE   (urgent)
  ESI 4 → LOW        (less urgent)
  ESI 5 → LOW        (non-urgent)

sex encoding: Male=1, Female=0, Other/Unknown=0 (conservative)
"""
import uuid
from app.ml.interface import MLEngine, MLFeatures, MLPrediction
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# ESI 1-5 → internal acuity string
ESI_TO_ACUITY = {
    1: "CRITICAL",
    2: "HIGH",
    3: "MODERATE",
    4: "LOW",
    5: "LOW",
}

# sex string → numeric encoding expected by model
SEX_TO_NUMERIC = {
    "male":    1,
    "female":  0,
    "other":   0,   # conservative
    "unknown": 0,   # conservative
}


class XGBoostMLEngine(MLEngine):

    def __init__(self):
        self._available = False
        self._version = "xgboost-not-loaded"
        self._engine = None
        self._load()

    def _load(self):
        try:
            import app.ml.core_engine as ce
            self._engine = ce
            self._available = True
            self._version = f"vitalnode-xgboost-v2-{settings.model_path.split('/')[-1]}"
            logger.info("xgboost_engine_v2_loaded", model_path=settings.model_path)
        except Exception as exc:
            logger.error("xgboost_engine_load_failed", error=str(exc))
            self._available = False

    def get_version(self) -> str:
        return self._version

    def is_available(self) -> bool:
        return self._available and self._engine is not None

    def predict(self, features: MLFeatures) -> MLPrediction:
        if not self.is_available():
            from app.core.exceptions import MLUnavailableError
            raise MLUnavailableError("XGBoost engine not loaded. Check MODEL_PATH in .env")

        # Map sex string → numeric (0/1)
        sex_str = (features.sex or "unknown").lower()
        sex_numeric = SEX_TO_NUMERIC.get(sex_str, 0)

        patient_dict = {
            "age":                  float(features.age) if features.age is not None else 45.0,
            "sex":                  sex_numeric,
            "current_hr":           features.heart_rate,
            "current_rr":           features.respiratory_rate,
            "current_spo2":         features.spo2,
            "current_sys_bp":       features.bp_systolic,
            "current_dia_bp":       features.bp_diastolic,       # NEW v2 feature
            "temp":                 features.temperature,
            # Existing trained feature: elapsed time since arrival.
            "time_in_queue_mins":   features.waiting_time_minutes or 0.0,
            # Existing trained reassessment features, now populated from the
            # actual previous vital rather than fixed at zero.
            "delta_hr":             features.delta_heart_rate or 0.0,
            "delta_spo2":           features.delta_spo2 or 0.0,
            # Extra context is consumed by the clinical NLP prompt. It is not
            # appended to the XGBoost feature vector, which must remain 14-wide
            # unless the model is retrained.
            "minutes_since_previous_vital": features.minutes_since_previous_vital,
            "minutes_since_last_assessment": features.minutes_since_last_assessment,
            "reassessment_count":   features.reassessment_count,
            "complaint":            features.chief_complaint or "",
            "history_available":    1 if features.history_available else 0,
            "history_text":         _build_history_text(features),
            "immediate_danger":     len(features.danger_signs) > 0 and not features.none_observed,
            "use_local_nlp":        features.use_local_nlp,
            "nlp_override":         features.nlp_extraction,
        }

        encounter_id = str(uuid.uuid4())
        result = self._engine.process_patient(encounter_id, patient_dict)

        final_esi = int(result.get("final_fused_esi", 3))   # already 1-5
        acuity = ESI_TO_ACUITY.get(final_esi, "MODERATE")
        confidence = result.get("confidence", 50.0)

        top_features = _build_top_features(result)

        logger.info(
            "xgboost_v2_prediction",
            final_esi=final_esi,
            acuity=acuity,
            confidence=confidence,
            action=result.get("action_path"),
            sex=sex_str,
        )

        return MLPrediction(
            acuity=acuity,
            confidence=confidence,
            class_probabilities=_esi_to_probs(final_esi, confidence),
            model_version=self._version,
            model_status="ACTIVE",
            top_features=top_features,
            nlp_extraction=result.get("_nlp_extraction"),
        )


def _build_history_text(features: MLFeatures) -> str:
    """
    Build history_text for Gemini NLP.
    Uses history_notes (rich text from pre-loaded records) if available,
    otherwise builds from structured fields.
    """
    # history_notes contains the full pre-loaded text — use directly
    if getattr(features, 'history_notes', None):
        return features.history_notes

    if not features.history_available:
        return "No relevant history"

    parts = []
    if features.has_cardiac_history:
        parts.append("Cardiac history")
    if features.has_respiratory_history:
        parts.append("Respiratory history")
    if features.on_anticoagulants:
        parts.append("On anticoagulants")
    return ", ".join(parts) if parts else "No relevant history"


def _build_top_features(result: dict) -> list:
    top = []
    if result.get("extracted_symptom"):
        esi = result.get("final_fused_esi", 3)
        top.append({
            "feature": "Primary Symptom",
            "value": result["extracted_symptom"],
            "impact": "HIGH" if esi <= 2 else "MEDIUM",
            "direction": "INCREASING",
        })
    if result.get("ai_reasoning"):
        top.append({
            "feature": "Clinical Reasoning",
            "value": result["ai_reasoning"],
            "impact": "HIGH",
            "direction": "INCREASING",
        })
    if result.get("action_path") and "Verify" in result.get("action_path", ""):
        top.append({
            "feature": "Action",
            "value": result["action_path"],
            "impact": "MEDIUM",
            "direction": "INCREASING",
        })
    return top


def _esi_to_probs(esi: int, confidence: float) -> dict:
    acuity = ESI_TO_ACUITY.get(esi, "MODERATE")
    main = round(confidence / 100, 3)
    remainder = round(1.0 - main, 3)
    probs = {"CRITICAL": 0.0, "HIGH": 0.0, "MODERATE": 0.0, "LOW": 0.0}
    probs[acuity] = main
    order = ["CRITICAL", "HIGH", "MODERATE", "LOW"]
    idx = order.index(acuity)
    adj = [order[i] for i in [idx - 1, idx + 1] if 0 <= i < len(order)]
    for a in adj:
        probs[a] = round(remainder / len(adj), 3)
    return probs
