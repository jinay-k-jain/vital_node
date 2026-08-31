"""
Safety Gate + Decision Fusion tests.

Key safety guarantees tested:
- ML says LOW but clinical rule says HIGH-RISK → must escalate
- Missing data + low confidence → VERIFY
- ML unavailable → VERIFY minimum
- All-clear → NORMAL
- Danger signs with low acuity → VERIFY
- Pediatric + critical → URGENT_REVIEW
"""
import pytest
from app.services.safety_gate import run_safety_gate
from app.services.decision_fusion import fuse, FusedRecommendation
from app.services.clinical_rules import evaluate_clinical_rules, ClinicalRulesOutput
from app.ml.interface import MLFeatures, MLPrediction
from app.ml.mock_engine import MockMLEngine
from app.schemas.assessment import DataQualityResponse


def make_quality(status="OK", completeness=0.85, missing=None, conflicts=None) -> DataQualityResponse:
    return DataQualityResponse(
        status=status,
        completeness=completeness,
        completeness_percent=int(completeness * 100),
        missing_fields=missing or [],
        invalid_fields=[],
        stale_fields=[],
        conflicting_fields=conflicts or [],
        warnings=[],
    )


def make_ml_prediction(acuity="LOW", confidence=88.0, status="MOCK") -> MLPrediction:
    return MLPrediction(
        acuity=acuity,
        confidence=confidence,
        class_probabilities={acuity: confidence / 100},
        model_version="mock-v1.0",
        model_status=status,
        top_features=[],
    )


def make_rules_output(safety_action="NORMAL", rules=None) -> ClinicalRulesOutput:
    out = ClinicalRulesOutput()
    out.recommended_safety_action = safety_action
    out.matched_rules = rules or []
    return out


# ── Safety Gate Tests ──────────────────────────────────────────────────────

class TestSafetyGate:

    def test_all_clear_returns_normal(self):
        fused = FusedRecommendation(
            acuity="LOW", confidence=88.0, safety_status="NORMAL",
            safety_flag=None, key_reasons=[], clinical_rules=[],
            top_factors=[], model_version="mock-v1.0",
            model_status="MOCK", is_conservative=False, data_completeness=85.0,
        )
        quality = make_quality()
        result = run_safety_gate(fused, quality, has_danger_signs=False, is_pediatric=False)
        assert result.status == "NORMAL"

    def test_clinical_rules_urgent_review_preserved(self):
        """URGENT_REVIEW from clinical rules must survive safety gate."""
        fused = FusedRecommendation(
            acuity="HIGH", confidence=75.0, safety_status="URGENT_REVIEW",
            safety_flag="Hypotension detected", key_reasons=[], clinical_rules=[],
            top_factors=[], model_version="mock-v1.0",
            model_status="MOCK", is_conservative=False, data_completeness=80.0,
        )
        quality = make_quality()
        result = run_safety_gate(fused, quality, has_danger_signs=False, is_pediatric=False)
        assert result.status == "URGENT_REVIEW"

    def test_low_confidence_escalates_to_verify(self):
        """ML confidence < 50% must trigger at least VERIFY."""
        fused = FusedRecommendation(
            acuity="LOW", confidence=42.0, safety_status="NORMAL",
            safety_flag=None, key_reasons=[], clinical_rules=[],
            top_factors=[], model_version="mock-v1.0",
            model_status="MOCK", is_conservative=False, data_completeness=75.0,
        )
        quality = make_quality()
        result = run_safety_gate(fused, quality, has_danger_signs=False, is_pediatric=False)
        assert result.status == "VERIFY"
        assert any("confidence" in r.lower() for r in result.reasons)

    def test_critical_data_quality_escalates_to_verify(self):
        fused = FusedRecommendation(
            acuity="LOW", confidence=80.0, safety_status="NORMAL",
            safety_flag=None, key_reasons=[], clinical_rules=[],
            top_factors=[], model_version="mock-v1.0",
            model_status="MOCK", is_conservative=False, data_completeness=45.0,
        )
        quality = make_quality(status="CRITICAL", completeness=0.45)
        result = run_safety_gate(fused, quality, has_danger_signs=False, is_pediatric=False)
        assert result.status == "VERIFY"

    def test_conflicting_data_escalates_to_verify(self):
        fused = FusedRecommendation(
            acuity="MODERATE", confidence=70.0, safety_status="NORMAL",
            safety_flag=None, key_reasons=[], clinical_rules=[],
            top_factors=[], model_version="mock-v1.0",
            model_status="MOCK", is_conservative=False, data_completeness=80.0,
        )
        quality = make_quality(conflicts=["Blood pressure: diastolic >= systolic"])
        result = run_safety_gate(fused, quality, has_danger_signs=False, is_pediatric=False)
        assert result.status == "VERIFY"

    def test_danger_signs_with_low_acuity_escalates(self):
        """Danger signs + LOW acuity → mismatch → VERIFY."""
        fused = FusedRecommendation(
            acuity="LOW", confidence=85.0, safety_status="NORMAL",
            safety_flag=None, key_reasons=[], clinical_rules=[],
            top_factors=[], model_version="mock-v1.0",
            model_status="MOCK", is_conservative=False, data_completeness=80.0,
        )
        quality = make_quality()
        result = run_safety_gate(fused, quality, has_danger_signs=True, is_pediatric=False)
        assert result.status == "VERIFY"

    def test_pediatric_critical_escalates_to_urgent(self):
        fused = FusedRecommendation(
            acuity="CRITICAL", confidence=90.0, safety_status="VERIFY",
            safety_flag=None, key_reasons=[], clinical_rules=[],
            top_factors=[], model_version="mock-v1.0",
            model_status="MOCK", is_conservative=True, data_completeness=85.0,
        )
        quality = make_quality()
        result = run_safety_gate(fused, quality, has_danger_signs=False, is_pediatric=True)
        assert result.status == "URGENT_REVIEW"

    def test_ml_unavailable_escalates_to_verify(self):
        fused = FusedRecommendation(
            acuity="LOW", confidence=50.0, safety_status="NORMAL",
            safety_flag=None, key_reasons=[], clinical_rules=[],
            top_factors=[], model_version="mock-v1.0",
            model_status="UNAVAILABLE", is_conservative=False, data_completeness=80.0,
        )
        quality = make_quality()
        result = run_safety_gate(fused, quality, has_danger_signs=False, is_pediatric=False)
        assert result.status == "VERIFY"
        assert any("unavailable" in r.lower() for r in result.reasons)

    def test_safety_gate_always_has_reasons(self):
        """Safety gate result must always explain itself."""
        fused = FusedRecommendation(
            acuity="LOW", confidence=90.0, safety_status="NORMAL",
            safety_flag=None, key_reasons=[], clinical_rules=[],
            top_factors=[], model_version="mock-v1.0",
            model_status="MOCK", is_conservative=False, data_completeness=90.0,
        )
        quality = make_quality()
        result = run_safety_gate(fused, quality, has_danger_signs=False, is_pediatric=False)
        assert len(result.reasons) > 0


# ── Decision Fusion Tests ──────────────────────────────────────────────────

class TestDecisionFusion:

    def test_ml_low_but_rules_high_risk_takes_conservative(self):
        """
        CRITICAL safety test: ML says LOW but clinical rules say URGENT_REVIEW.
        Final acuity must be escalated, not left at LOW.
        """
        ml = make_ml_prediction(acuity="LOW", confidence=85.0)
        rules = make_rules_output(safety_action="URGENT_REVIEW", rules=["Hypotension detected"])
        result = fuse(ml, rules, data_completeness_percent=80.0, age_group="ADULT")
        # Clinical rules recommended HIGH minimum due to URGENT_REVIEW
        assert result.safety_status == "URGENT_REVIEW"
        assert result.acuity in ("CRITICAL", "HIGH")  # must be escalated from LOW

    def test_high_confidence_ml_normal_rules_accepted(self):
        ml = make_ml_prediction(acuity="HIGH", confidence=90.0)
        rules = make_rules_output(safety_action="NORMAL")
        result = fuse(ml, rules, data_completeness_percent=85.0, age_group="ADULT")
        assert result.acuity == "HIGH"
        assert result.safety_status == "NORMAL"
        assert result.confidence == 90.0

    def test_ml_unavailable_falls_back_to_rules(self):
        rules = make_rules_output(safety_action="VERIFY", rules=["Low SpO2"])
        result = fuse(None, rules, data_completeness_percent=70.0, age_group="ADULT")
        assert result.model_status == "UNAVAILABLE"
        assert result.safety_status in ("VERIFY", "URGENT_REVIEW")

    def test_low_completeness_reduces_confidence(self):
        ml = make_ml_prediction(acuity="MODERATE", confidence=88.0)
        rules = make_rules_output()
        result = fuse(ml, rules, data_completeness_percent=45.0, age_group="ADULT")
        assert result.confidence <= 55.0
        assert result.is_conservative is True

    def test_pediatric_pathway_sets_conservative(self):
        ml = make_ml_prediction(acuity="LOW", confidence=80.0)
        rules = make_rules_output()
        result = fuse(ml, rules, data_completeness_percent=80.0, age_group="PEDIATRIC")
        assert result.is_conservative is True

    def test_model_version_preserved(self):
        ml = make_ml_prediction(acuity="LOW", confidence=88.0)
        rules = make_rules_output()
        result = fuse(ml, rules, data_completeness_percent=80.0, age_group="ADULT")
        assert result.model_version == "mock-v1.0"


# ── ML Mock Engine Tests ───────────────────────────────────────────────────

class TestMockMLEngine:

    def setup_method(self):
        self.engine = MockMLEngine()

    def test_engine_available(self):
        assert self.engine.is_available() is True

    def test_version_string(self):
        assert "mock" in self.engine.get_version().lower()

    def test_critical_spo2_returns_critical(self):
        features = MLFeatures(age=50, sex="Male", age_group="ADULT",
                              spo2=85.0, heart_rate=80.0, data_completeness=0.85)
        pred = self.engine.predict(features)
        assert pred.acuity == "CRITICAL"
        assert pred.model_status == "MOCK"

    def test_hypotension_returns_critical(self):
        features = MLFeatures(age=50, sex="Male", age_group="ADULT",
                              bp_systolic=82.0, data_completeness=0.85)
        pred = self.engine.predict(features)
        assert pred.acuity == "CRITICAL"

    def test_normal_vitals_returns_low(self):
        features = MLFeatures(age=30, sex="Female", age_group="ADULT",
                              spo2=98.0, heart_rate=75.0, respiratory_rate=16.0,
                              bp_systolic=118.0, bp_diastolic=78.0,
                              temperature=37.0, avpu="Alert",
                              none_observed=True, data_completeness=0.9)
        pred = self.engine.predict(features)
        assert pred.acuity == "LOW"
        assert pred.confidence >= 70

    def test_class_probabilities_sum_near_one(self):
        features = MLFeatures(age=40, sex="Male", age_group="ADULT",
                              spo2=97.0, data_completeness=0.9)
        pred = self.engine.predict(features)
        total = sum(pred.class_probabilities.values())
        assert 0.95 <= total <= 1.05  # allows for rounding

    def test_low_completeness_reduces_confidence(self):
        features = MLFeatures(age=40, sex="Male", age_group="ADULT",
                              data_completeness=0.3)
        pred = self.engine.predict(features)
        assert pred.confidence <= 60.0

    def test_prediction_always_returns_valid_acuity(self):
        valid_acuities = {"CRITICAL", "HIGH", "MODERATE", "LOW"}
        for spo2 in [85.0, 91.0, 96.0, 99.0]:
            features = MLFeatures(age=40, sex="Male", age_group="ADULT",
                                  spo2=spo2, data_completeness=0.8)
            pred = self.engine.predict(features)
            assert pred.acuity in valid_acuities
