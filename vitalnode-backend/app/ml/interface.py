"""
ML Engine interface.
The real XGBoost model can be plugged in by implementing this protocol.
The rest of the backend never depends on a specific model implementation.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MLFeatures:
    """
    Normalised feature vector sent to the ML engine.
    All triage-time features only. No future information.
    Missing values represented as None - never imputed here.
    """
    # Demographics
    age: Optional[int] = None
    sex: Optional[str] = None          # "Male" | "Female" | "Other" | "Unknown"
    age_group: Optional[str] = None    # "PEDIATRIC" | "ADULT" | "OLDER_ADULT"
    is_pregnant: Optional[bool] = None

    # Vitals
    spo2: Optional[float] = None
    heart_rate: Optional[float] = None
    respiratory_rate: Optional[float] = None
    bp_systolic: Optional[float] = None
    bp_diastolic: Optional[float] = None
    temperature: Optional[float] = None
    avpu: Optional[str] = None         # "Alert" | "Voice" | "Pain" | "Unresponsive"

    # Complaint and symptoms
    chief_complaint: Optional[str] = None
    symptoms: List[str] = field(default_factory=list)
    danger_signs: List[str] = field(default_factory=list)
    none_observed: bool = False

    # History
    history_available: bool = False
    has_cardiac_history: bool = False
    has_respiratory_history: bool = False
    on_anticoagulants: bool = False

    # Context
    arrival_mode: Optional[str] = None
    data_completeness: float = 0.0

    # Pre-loaded history text (passed directly to Gemini NLP)
    history_notes: Optional[str] = None

    # Demo surge records use a deterministic, local symptom normaliser.  This
    # keeps the surge scenario reproducible and avoids external NLP calls.
    # Normal assessments leave this False and keep the configured NLP flow.
    use_local_nlp: bool = False
    nlp_extraction: Optional[dict] = None

    # ── Timing fields (used by your ML model at reassessment) ────────────────
    # All times are in minutes for easy model consumption

    # How long this patient has been waiting since arrival
    waiting_time_minutes: Optional[float] = None

    # Time since the last vital signs were recorded
    minutes_since_last_vital: Optional[float] = None

    # Time since the last assessment was submitted
    minutes_since_last_assessment: Optional[float] = None

    # How many reassessments have been done so far
    reassessment_count: int = 0

    # Is this an initial assessment (False) or a reassessment (True)
    is_reassessment: bool = False

    # How many minutes until the next scheduled reassessment (negative = overdue)
    minutes_until_reassessment_due: Optional[float] = None

    # Change context for a reassessment. These are None for an initial
    # assessment, because there is no earlier observation to compare.
    minutes_since_previous_vital: Optional[float] = None
    delta_heart_rate: Optional[float] = None
    delta_spo2: Optional[float] = None


@dataclass
class MLPrediction:
    """
    Output of the ML engine.
    model_status = "MOCK" when using the mock engine.
    """
    acuity: str          # "CRITICAL" | "HIGH" | "MODERATE" | "LOW"
    confidence: float    # 0-100
    class_probabilities: dict  # {"CRITICAL": 0.x, "HIGH": 0.x, ...}
    model_version: str
    model_status: str    # "MOCK" | "ACTIVE" | "UNAVAILABLE"
    top_features: List[dict]  # [{feature, importance}]
    nlp_extraction: Optional[dict] = None


class MLEngine(ABC):
    """Abstract ML engine interface."""

    @abstractmethod
    def predict(self, features: MLFeatures) -> MLPrediction:
        """
        Run prediction on a feature vector.
        Must not raise on missing data - handle gracefully.
        """
        ...

    @abstractmethod
    def get_version(self) -> str:
        """Return the model version string."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the model is ready to serve predictions."""
        ...
