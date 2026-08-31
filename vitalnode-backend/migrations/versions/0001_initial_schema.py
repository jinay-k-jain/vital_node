"""Initial schema - all VitalNode tables

Revision ID: 0001
Revises:
Create Date: 2026-08-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enum(name: str) -> sa.Enum:
    """
    Return an Enum type that references an ALREADY-EXISTING PostgreSQL enum.
    create_constraint=False + schema=None prevents SQLAlchemy from trying
    to CREATE the type again when building tables.
    """
    return sa.Enum(name=name, create_constraint=False, native_enum=True)


def upgrade() -> None:
    conn = op.get_bind()

    # ── Create all ENUMs safely (check existence before creating) ──────────
    def create_enum(name: str, values: list) -> None:
        vals = ", ".join(f"'{v}'" for v in values)
        conn.execute(sa.text(
            f"DO $$ BEGIN "
            f"IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{name}') THEN "
            f"CREATE TYPE {name} AS ENUM ({vals}); "
            f"END IF; "
            f"END $$;"
        ))

    create_enum("userrole",       ["Triage Nurse", "Clinician", "Administrator"])
    create_enum("sex",            ["Male", "Female", "Other", "Unknown"])
    create_enum("agegroup",       ["PEDIATRIC", "ADULT", "OLDER_ADULT"])
    create_enum("arrivalmode",    ["walk-in", "ambulance", "referral", "transfer", "other"])
    create_enum("patientstatus",  ["WAITING", "IN_PROGRESS", "DISCHARGED", "ADMITTED"])
    create_enum("acuity",         ["CRITICAL", "HIGH", "MODERATE", "LOW", "PENDING"])
    create_enum("safetystatus",   ["NORMAL", "VERIFY", "URGENT_REVIEW"])
    create_enum("assessmenttype", ["INITIAL", "REASSESSMENT"])
    create_enum("historystatus",  ["AVAILABLE", "UNAVAILABLE", "PARTIAL"])
    create_enum("vitalsource",    ["Manual Entry", "Connected Device", "Imported"])
    create_enum("avpu",           ["Alert", "Voice", "Pain", "Unresponsive"])
    create_enum("modelstatus",    ["MOCK", "ACTIVE", "UNAVAILABLE"])
    create_enum("notificationtype", ["REASSESSMENT_DUE", "VITAL_RECEIVED", "PRIORITY_CHANGED",
                                     "VERIFICATION_REQUIRED", "DEVICE_DISCONNECTED", "SYSTEM_ERROR"])
    create_enum("devicestatus",   ["CONNECTED", "DISCONNECTED", "ERROR", "SIMULATED"])

    # ── TABLES ─────────────────────────────────────────────────────────────
    # All enum columns use sa.Text() here — the actual PostgreSQL column type
    # is set via server_default / explicit casting in raw SQL above.
    # We cast to the correct type using postgresql.ENUM with create_type=False.

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("staff_id", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=True, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", postgresql.ENUM(name="userrole", create_type=False), nullable=False),
        sa.Column("department", sa.String(100), nullable=False, server_default="Emergency"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_staff_id", "users", ["staff_id"])

    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("display_id", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("sex", postgresql.ENUM(name="sex", create_type=False), nullable=False),
        sa.Column("age_group", postgresql.ENUM(name="agegroup", create_type=False), nullable=False),
        sa.Column("is_simulation", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_patients_display_id", "patients", ["display_id"])

    op.create_table(
        "encounters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("arrival_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("arrival_mode", postgresql.ENUM(name="arrivalmode", create_type=False), nullable=False),
        sa.Column("is_pregnant", sa.Boolean(), nullable=True),
        sa.Column("status", postgresql.ENUM(name="patientstatus", create_type=False), nullable=False, server_default="WAITING"),
        sa.Column("current_acuity", postgresql.ENUM(name="acuity", create_type=False), nullable=False, server_default="PENDING"),
        sa.Column("safety_status", postgresql.ENUM(name="safetystatus", create_type=False), nullable=False, server_default="NORMAL"),
        sa.Column("waiting_time_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reassessment_due", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reassessment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_connected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_surge_patient", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_encounters_patient_id", "encounters", ["patient_id"])
    op.create_index("ix_encounters_status", "encounters", ["status"])
    op.create_index("ix_encounters_current_acuity", "encounters", ["current_acuity"])

    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("device_code", sa.String(50), nullable=False, unique=True),
        sa.Column("device_name", sa.String(100), nullable=False),
        sa.Column("status", postgresql.ENUM(name="devicestatus", create_type=False), nullable=False, server_default="SIMULATED"),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessment_type", postgresql.ENUM(name="assessmenttype", create_type=False), nullable=False, server_default="INITIAL"),
        sa.Column("chief_complaint", sa.Text(), nullable=True),
        sa.Column("voice_transcript", sa.Text(), nullable=True),
        sa.Column("confirmed_complaint", sa.Text(), nullable=True),
        sa.Column("symptoms", postgresql.JSONB(), nullable=True),
        sa.Column("raw_extracted_symptoms", postgresql.JSONB(), nullable=True),
        sa.Column("danger_signs", postgresql.JSONB(), nullable=True),
        sa.Column("none_observed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("history_status", postgresql.ENUM(name="historystatus", create_type=False), nullable=False, server_default="UNAVAILABLE"),
        sa.Column("history_conditions", postgresql.JSONB(), nullable=True),
        sa.Column("history_medications", postgresql.JSONB(), nullable=True),
        sa.Column("history_allergies", postgresql.JSONB(), nullable=True),
        sa.Column("history_notes", sa.Text(), nullable=True),
        sa.Column("submitted_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_assessments_encounter_id", "assessments", ["encounter_id"])

    op.create_table(
        "vitals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("spo2", sa.Float(), nullable=True),
        sa.Column("heart_rate", sa.Float(), nullable=True),
        sa.Column("respiratory_rate", sa.Float(), nullable=True),
        sa.Column("bp_systolic", sa.Float(), nullable=True),
        sa.Column("bp_diastolic", sa.Float(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("avpu", postgresql.ENUM(name="avpu", create_type=False), nullable=True),
        sa.Column("source", postgresql.ENUM(name="vitalsource", create_type=False), nullable=False, server_default="Manual Entry"),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_vitals_encounter_id", "vitals", ["encounter_id"])

    op.create_table(
        "ai_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("acuity", postgresql.ENUM(name="acuity", create_type=False), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("data_completeness", sa.Float(), nullable=False),
        sa.Column("safety_status", postgresql.ENUM(name="safetystatus", create_type=False), nullable=False),
        sa.Column("safety_flag", sa.Text(), nullable=True),
        sa.Column("key_reasons", postgresql.JSONB(), nullable=True),
        sa.Column("clinical_rules", postgresql.JSONB(), nullable=True),
        sa.Column("top_factors", postgresql.JSONB(), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("model_status", postgresql.ENUM(name="modelstatus", create_type=False), nullable=False, server_default="MOCK"),
        sa.Column("clinical_rule_version", sa.String(50), nullable=False, server_default="prototype-v1.0"),
        sa.Column("is_conservative", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("recommended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ai_recommendations_encounter_id", "ai_recommendations", ["encounter_id"])

    op.create_table(
        "nurse_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("nurse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("final_acuity", postgresql.ENUM(name="acuity", create_type=False), nullable=False),
        sa.Column("override_reason", sa.String(200), nullable=True),
        sa.Column("override_note", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "queue_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("priority_score", sa.Float(), nullable=False, server_default="999.0"),
        sa.Column("acuity_rank", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("reassessment_overdue", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_safety_flag", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_priority_update", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_queue_entries_priority_score", "queue_entries", ["priority_score"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("type", postgresql.ENUM(name="notificationtype", create_type=False), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_urgent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=True),
        sa.Column("patient_display_id", sa.String(20), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_notifications_encounter_id", "notifications", ["encounter_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_staff_id", sa.String(50), nullable=True),
        sa.Column("user_name", sa.String(200), nullable=True),
        sa.Column("user_role", sa.String(100), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("patient_display_id", sa.String(20), nullable=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ai_recommendation", sa.String(20), nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("safety_flag", sa.Text(), nullable=True),
        sa.Column("nurse_action", sa.String(50), nullable=True),
        sa.Column("final_acuity", sa.String(20), nullable=True),
        sa.Column("override_reason", sa.String(200), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("event_metadata", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"])
    op.create_index("ix_audit_events_patient_id", "audit_events", ["patient_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_patient_timestamp", "audit_events", ["patient_id", "timestamp"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("notifications")
    op.drop_table("queue_entries")
    op.drop_table("nurse_decisions")
    op.drop_table("ai_recommendations")
    op.drop_table("vitals")
    op.drop_table("assessments")
    op.drop_table("devices")
    op.drop_table("encounters")
    op.drop_table("patients")
    op.drop_table("users")
    # Drop all enums
    conn = op.get_bind()
    for t in ["userrole","sex","agegroup","arrivalmode","patientstatus","acuity",
              "safetystatus","assessmenttype","historystatus","vitalsource","avpu",
              "modelstatus","notificationtype","devicestatus"]:
        conn.execute(sa.text(f"DROP TYPE IF EXISTS {t} CASCADE"))
