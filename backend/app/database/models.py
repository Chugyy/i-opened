"""SQLAlchemy models (documentation + migration reference)."""

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Index, Integer, JSONB, SmallInteger, String, Text, Time, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True)
    email = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    notifications_enabled = Column(Boolean, nullable=False)
    timezone = Column(String(50), nullable=False, server_default="Europe/Paris")
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class Calendar(Base):
    __tablename__ = "calendars"

    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    description = Column(Text)
    slot_duration = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive', 'incomplete')", name="ck_calendars_status"),
        CheckConstraint("slot_duration > 0", name="ck_calendars_slot_duration"),
    )


class Availabilitie(Base):
    __tablename__ = "availabilities"

    id = Column(UUID, primary_key=True)
    calendar_id = Column(UUID, nullable=False)
    day_of_week = Column(SmallInteger, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    lunch_start = Column(Time)
    lunch_end = Column(Time)
    is_active = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_availabilities_day_of_week"),
        CheckConstraint("end_time > start_time", name="ck_availabilities_end_after_start"),
        CheckConstraint("(lunch_start IS NULL AND lunch_end IS NULL) OR (lunch_start IS NOT NULL AND lunch_end IS NOT NULL)", name="ck_availabilities_lunch_both_or_none"),
        CheckConstraint("lunch_end IS NULL OR lunch_end > lunch_start", name="ck_availabilities_lunch_after"),
    )


class BlockedEvent(Base):
    __tablename__ = "blocked_events"

    id = Column(UUID, primary_key=True)
    calendar_id = Column(UUID, nullable=False)
    google_event_id = Column(String(255), nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_blocked_events_ends_after_starts"),
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID, primary_key=True)
    calendar_id = Column(UUID, nullable=False)
    label = Column(String(500), nullable=False)
    type = Column(String(20), nullable=False)
    options = Column(JSONB)
    position = Column(Integer, nullable=False)
    required = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("type IN ('text', 'single_choice', 'multiple_choice', 'number')", name="ck_questions_type"),
        CheckConstraint("position >= 1", name="ck_questions_position"),
    )


class QualificationRule(Base):
    __tablename__ = "qualification_rules"

    id = Column(UUID, primary_key=True)
    calendar_id = Column(UUID, nullable=False)
    question_id = Column(UUID, nullable=False)
    operator = Column(String(20), nullable=False)
    threshold_value = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("operator IN ('=', '!=', '<', '>', '<=', '>=', 'contient', 'ne_contient_pas')", name="ck_qualification_rules_operator"),
    )


class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID, primary_key=True)
    calendar_id = Column(UUID, nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    answers = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('nouveau', 'qualifie', 'non_qualifie', 'booke', 'no_show')", name="ck_leads_status"),
    )


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID, primary_key=True)
    lead_id = Column(UUID, nullable=False)
    calendar_id = Column(UUID, nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False)
    gcal_event_id = Column(String(255))
    cancel_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('confirmed', 'cancelled', 'no_show')", name="ck_bookings_status"),
        CheckConstraint("ends_at > starts_at", name="ck_bookings_ends_after_starts"),
    )


class Automation(Base):
    __tablename__ = "automations"

    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, nullable=False)
    calendar_id = Column(UUID)
    name = Column(String(255), nullable=False)
    trigger = Column(String(30), nullable=False)
    is_active = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("trigger IN ('avant_rdv', 'apres_rdv', 'qualifie_sans_booking', 'coordonnees_sans_booking')", name="ck_automations_trigger"),
    )


class AutomationStep(Base):
    __tablename__ = "automation_steps"

    id = Column(UUID, primary_key=True)
    automation_id = Column(UUID, nullable=False)
    channel = Column(String(20), nullable=False)
    delay_value = Column(Integer, nullable=False)
    delay_unit = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("channel IN ('email', 'whatsapp')", name="ck_automation_steps_channel"),
        CheckConstraint("delay_unit IN ('hours', 'days')", name="ck_automation_steps_delay_unit"),
        CheckConstraint("delay_value >= 1", name="ck_automation_steps_delay_value"),
        CheckConstraint("position >= 0", name="ck_automation_steps_position"),
    )


class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id = Column(UUID, primary_key=True)
    automation_id = Column(UUID, nullable=False)
    automation_step_id = Column(UUID, nullable=False)
    lead_id = Column(UUID, nullable=False)
    trigger = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    sent_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'sent', 'failed', 'cancelled')", name="ck_automation_logs_status"),
        CheckConstraint("trigger IN ('avant_rdv', 'apres_rdv', 'qualifie_sans_booking', 'coordonnees_sans_booking')", name="ck_automation_logs_trigger"),
    )


class CalendarSync(Base):
    __tablename__ = "calendar_syncs"

    id = Column(UUID, primary_key=True)
    calendar_id = Column(UUID, nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expiry = Column(DateTime(timezone=True), nullable=False)
    sync_token = Column(Text)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('connected', 'disconnected', 'error')", name="ck_calendar_syncs_status"),
    )
