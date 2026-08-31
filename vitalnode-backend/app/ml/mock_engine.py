"""
Mock ML Engine - used for development and demo mode.
Uses deterministic rule-based logic to simulate model predictions.
All results are clearly labeled MODEL_STATUS=MOCK.
Never used in production with real patients.
"""
from typing import List
from app.ml.interface import MLEngine, MLFeatures, MLPrediction

MODEL_VERSION = "mock-v1.0"


class MockMLEngine(MLEngine):
    """
    Deterministic mock engine.
    Simulates XGBoost output for demo/development.
    Clearly labeled MOCK in every response.
    """

    def get_version(self) -> str:
        return MODEL_VERSION

    def is_available(self) -> bool:
        return True

    def predict(self, features: MLFeatures) -> MLPrediction:
        acuity, confidence, reasons = self._evaluate(features)
        probs = self._class_probs(acuity, confidence)
        top_features = self._top_features(features, acuity)

        return MLPrediction(
            acuity=acuity,
            confidence=confidence,
            class_probabilities=probs,
            model_version=MODEL_VERSION,
            model_status="MOCK",
            top_features=top_features,
        )

    # ── Internal helpers ────────────────────────────────────────────────────

    def _evaluate(self, f: MLFeatures) -> tuple[str, float, List[str]]:
        """
        Deterministic acuity estimation based on vital thresholds.
        Note: These are NOT clinical rules - they are mock model logic.
        The ClinicalRulesService handles the actual rule evaluation.
        """
        acuity = "LOW"
        confidence = 88.0
        reasons: List[str] = []

        # Danger signs push to HIGH
        if f.danger_signs and not f.none_observed:
            acuity = "HIGH"
            confidence = 85.0
            reasons.append("Danger signs observed")

        # Vital-driven escalation
        if f.spo2 is not None:
            if f.spo2 < 90:
                acuity = "CRITICAL"
                confidence = 92.0
                reasons.append(f"SpO₂ critically low ({f.spo2}%)")
            elif f.spo2 < 94 and self._acuity_rank(acuity) > 1:
                acuity = "HIGH"
                confidence = 82.0
                reasons.append(f"SpO₂ low ({f.spo2}%)")

        if f.bp_systolic is not None and f.bp_systolic < 90:
            acuity = "CRITICAL"
            confidence = min(confidence, 90.0)
            reasons.append(f"Hypotension ({f.bp_systolic} mmHg)")

        if f.heart_rate is not None:
            if f.heart_rate > 130 or f.heart_rate < 45:
                if self._acuity_rank(acuity) > 1:
                    acuity = "HIGH"
                    reasons.append(f"Abnormal heart rate ({f.heart_rate} bpm)")

        if f.respiratory_rate is not None and f.respiratory_rate > 26:
            if self._acuity_rank(acuity) > 1:
                acuity = "HIGH"
                reasons.append(f"Elevated respiratory rate ({f.respiratory_rate}/min)")

        if f.avpu:
            if f.avpu == "Unresponsive":
                acuity = "CRITICAL"
                reasons.append("Unresponsive (AVPU: U)")
            elif f.avpu == "Pain" and self._acuity_rank(acuity) > 1:
                acuity = "HIGH"
                reasons.append("Responds only to pain")

        # Pediatric pathway - apply conservative flag
        if f.age_group == "PEDIATRIC":
            reasons.append("Pediatric pathway applied")

        # Low completeness reduces confidence
        if f.data_completeness < 0.6:
            confidence = min(confidence, 60.0)
            reasons.append(f"Data completeness low ({int(f.data_completeness*100)}%)")
        elif f.data_completeness < 0.8:
            confidence = min(confidence, 75.0)

        # If nothing triggered, give a reason
        if not reasons:
            reasons.append("Stable vital signs")
            reasons.append("No danger signs detected")

        return acuity, round(confidence, 1), reasons

    def _acuity_rank(self, acuity: str) -> int:
        return {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3, "PENDING": 4}.get(acuity, 4)

    def _class_probs(self, acuity: str, confidence: float) -> dict:
        """Generate plausible class probability distribution."""
        main_prob = confidence / 100
        remainder = 1.0 - main_prob
        others = {"CRITICAL": 0.0, "HIGH": 0.0, "MODERATE": 0.0, "LOW": 0.0}
        others[acuity] = main_prob
        # Distribute remainder across adjacent classes
        order = ["CRITICAL", "HIGH", "MODERATE", "LOW"]
        idx = order.index(acuity)
        adjacent = [order[i] for i in [idx - 1, idx + 1] if 0 <= i < len(order)]
        for a in adjacent:
            others[a] = round(remainder / len(adjacent), 3)
        return others

    def _top_features(self, f: MLFeatures, acuity: str) -> List[dict]:
        """Return a mock SHAP-style feature importance list."""
        features = []
        if f.spo2 is not None:
            impact = "HIGH" if f.spo2 < 92 else ("MEDIUM" if f.spo2 < 96 else "LOW")
            direction = "INCREASING" if f.spo2 < 94 else "DECREASING"
            features.append({"feature": "SpO₂", "value": f"{f.spo2}%", "impact": impact, "direction": direction})
        if f.heart_rate is not None:
            impact = "HIGH" if (f.heart_rate > 120 or f.heart_rate < 50) else "LOW"
            features.append({"feature": "Heart Rate", "value": f"{f.heart_rate} bpm", "impact": impact, "direction": "INCREASING"})
        if f.bp_systolic is not None:
            impact = "HIGH" if f.bp_systolic < 90 else "LOW"
            features.append({"feature": "Systolic BP", "value": f"{f.bp_systolic} mmHg", "impact": impact, "direction": "INCREASING"})
        if f.respiratory_rate is not None:
            impact = "HIGH" if f.respiratory_rate > 25 else "LOW"
            features.append({"feature": "Respiratory Rate", "value": f"{f.respiratory_rate}/min", "impact": impact, "direction": "INCREASING"})
        if f.danger_signs:
            features.append({"feature": "Danger Signs", "value": ", ".join(f.danger_signs[:2]), "impact": "HIGH", "direction": "INCREASING"})
        return features[:4]  # Top 4 max
