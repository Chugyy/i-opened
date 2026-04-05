-- Migration 001: Initial Schema
-- Generated: 2026-04-04T10:52:55.117238

CREATE TABLE IF NOT EXISTS users (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_users_email UNIQUE (email)

);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);


CREATE TABLE IF NOT EXISTS calendars (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,
    slot_duration INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'incomplete',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_calendars_slug UNIQUE (slug),
    CONSTRAINT ck_calendars_status CHECK (status IN ('active', 'inactive', 'incomplete')),
    CONSTRAINT ck_calendars_slot_duration CHECK (slot_duration > 0)

);

CREATE INDEX IF NOT EXISTS idx_calendars_user_id ON calendars(user_id);

CREATE INDEX IF NOT EXISTS idx_calendars_slug ON calendars(slug);

CREATE INDEX IF NOT EXISTS idx_calendars_status ON calendars(status);


CREATE TABLE IF NOT EXISTS availabilities (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calendar_id UUID NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
    day_of_week SMALLINT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    lunch_start TIME,
    lunch_end TIME,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_availabilities_calendar_day UNIQUE (calendar_id, day_of_week),
    CONSTRAINT ck_availabilities_day_of_week CHECK (day_of_week BETWEEN 0 AND 6),
    CONSTRAINT ck_availabilities_end_after_start CHECK (end_time > start_time),
    CONSTRAINT ck_availabilities_lunch_both_or_none CHECK ((lunch_start IS NULL AND lunch_end IS NULL) OR (lunch_start IS NOT NULL AND lunch_end IS NOT NULL)),
    CONSTRAINT ck_availabilities_lunch_after CHECK (lunch_end IS NULL OR lunch_end > lunch_start)

);

CREATE INDEX IF NOT EXISTS idx_availabilities_calendar_id ON availabilities(calendar_id);


CREATE TABLE IF NOT EXISTS blocked_events (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calendar_id UUID NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
    google_event_id VARCHAR(255) NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_blocked_events_google_id UNIQUE (google_event_id),
    CONSTRAINT ck_blocked_events_ends_after_starts CHECK (ends_at > starts_at)

);

CREATE INDEX IF NOT EXISTS idx_blocked_events_calendar_id ON blocked_events(calendar_id);

CREATE INDEX IF NOT EXISTS idx_blocked_events_starts_at ON blocked_events(starts_at);

CREATE INDEX IF NOT EXISTS idx_blocked_events_google_event_id ON blocked_events(google_event_id);


CREATE TABLE IF NOT EXISTS questions (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calendar_id UUID NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
    label VARCHAR(500) NOT NULL,
    type VARCHAR(20) NOT NULL,
    options JSONB,
    position INTEGER NOT NULL,
    required BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_questions_type CHECK (type IN ('text', 'single_choice', 'multiple_choice', 'number')),
    CONSTRAINT ck_questions_position CHECK (position >= 1)

);

CREATE INDEX IF NOT EXISTS idx_questions_calendar_id ON questions(calendar_id);

CREATE INDEX IF NOT EXISTS idx_questions_calendar_position ON questions(calendar_id, position);


CREATE TABLE IF NOT EXISTS qualification_rules (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calendar_id UUID NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    operator VARCHAR(20) NOT NULL,
    threshold_value TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_qualification_rules_operator CHECK (operator IN ('=', '!=', '<', '>', '<=', '>=', 'contient', 'ne_contient_pas'))

);

CREATE INDEX IF NOT EXISTS idx_qualification_rules_calendar_id ON qualification_rules(calendar_id);

CREATE INDEX IF NOT EXISTS idx_qualification_rules_question_id ON qualification_rules(question_id);


CREATE TABLE IF NOT EXISTS leads (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calendar_id UUID NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    answers JSONB NOT NULL DEFAULT '[]',
    status VARCHAR(20) NOT NULL DEFAULT 'nouveau',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_leads_email_calendar UNIQUE (email, calendar_id),
    CONSTRAINT ck_leads_status CHECK (status IN ('nouveau', 'qualifie', 'non_qualifie', 'booke', 'no_show'))

);

CREATE INDEX IF NOT EXISTS idx_leads_calendar_id ON leads(calendar_id);

CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);

CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);

CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_leads_calendar_status ON leads(calendar_id, status);


CREATE TABLE IF NOT EXISTS bookings (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    calendar_id UUID NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'confirmed',
    gcal_event_id VARCHAR(255),
    cancel_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_bookings_status CHECK (status IN ('confirmed', 'cancelled', 'no_show')),
    CONSTRAINT ck_bookings_ends_after_starts CHECK (ends_at > starts_at)

);

CREATE INDEX IF NOT EXISTS idx_bookings_lead_id ON bookings(lead_id);

CREATE INDEX IF NOT EXISTS idx_bookings_calendar_id ON bookings(calendar_id);

CREATE INDEX IF NOT EXISTS idx_bookings_starts_at ON bookings(starts_at);

CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);

CREATE INDEX IF NOT EXISTS idx_bookings_calendar_status_starts ON bookings(calendar_id, status, starts_at);


CREATE TABLE IF NOT EXISTS automations (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    calendar_id UUID REFERENCES calendars(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    trigger VARCHAR(30) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_automations_trigger CHECK (trigger IN ('avant_rdv', 'apres_rdv', 'qualifie_sans_booking', 'coordonnees_sans_booking'))

);

CREATE INDEX IF NOT EXISTS idx_automations_user_id ON automations(user_id);

CREATE INDEX IF NOT EXISTS idx_automations_calendar_id ON automations(calendar_id);

CREATE INDEX IF NOT EXISTS idx_automations_trigger ON automations(trigger);

CREATE INDEX IF NOT EXISTS idx_automations_is_active ON automations(is_active);

CREATE INDEX IF NOT EXISTS idx_automations_calendar_trigger ON automations(calendar_id, trigger, is_active);


CREATE TABLE IF NOT EXISTS automation_steps (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_id UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
    channel VARCHAR(20) NOT NULL,
    delay_value INTEGER NOT NULL,
    delay_unit VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    position INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_automation_steps_channel CHECK (channel IN ('email', 'whatsapp')),
    CONSTRAINT ck_automation_steps_delay_unit CHECK (delay_unit IN ('hours', 'days')),
    CONSTRAINT ck_automation_steps_delay_value CHECK (delay_value >= 1),
    CONSTRAINT ck_automation_steps_position CHECK (position >= 0)

);

CREATE INDEX IF NOT EXISTS idx_automation_steps_automation_id ON automation_steps(automation_id);

CREATE INDEX IF NOT EXISTS idx_automation_steps_automation_position ON automation_steps(automation_id, position);


CREATE TABLE IF NOT EXISTS automation_logs (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_id UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
    automation_step_id UUID NOT NULL REFERENCES automation_steps(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    trigger VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    scheduled_at TIMESTAMPTZ NOT NULL,
    sent_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_automation_logs_status CHECK (status IN ('pending', 'sent', 'failed', 'cancelled')),
    CONSTRAINT ck_automation_logs_trigger CHECK (trigger IN ('avant_rdv', 'apres_rdv', 'qualifie_sans_booking', 'coordonnees_sans_booking'))

);

CREATE INDEX IF NOT EXISTS idx_automation_logs_automation_id ON automation_logs(automation_id);

CREATE INDEX IF NOT EXISTS idx_automation_logs_lead_id ON automation_logs(lead_id);

CREATE INDEX IF NOT EXISTS idx_automation_logs_status ON automation_logs(status);

CREATE INDEX IF NOT EXISTS idx_automation_logs_scheduled_at ON automation_logs(scheduled_at);

CREATE INDEX IF NOT EXISTS idx_automation_logs_pending_scheduled ON automation_logs(scheduled_at);


CREATE TABLE IF NOT EXISTS calendar_syncs (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calendar_id UUID NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expiry TIMESTAMPTZ NOT NULL,
    sync_token TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'connected',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_calendar_syncs_calendar_id UNIQUE (calendar_id),
    CONSTRAINT ck_calendar_syncs_status CHECK (status IN ('connected', 'disconnected', 'error'))

);

CREATE INDEX IF NOT EXISTS idx_calendar_syncs_calendar_id ON calendar_syncs(calendar_id);

CREATE INDEX IF NOT EXISTS idx_calendar_syncs_status ON calendar_syncs(status);

