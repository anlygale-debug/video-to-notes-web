CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS access_grants (
  id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  code_lookup TEXT NOT NULL UNIQUE,
  code_hash TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  transcription_seconds_limit INTEGER,
  note_generation_limit INTEGER,
  max_video_seconds INTEGER NOT NULL DEFAULT 1200,
  expires_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS access_usage (
  id TEXT PRIMARY KEY,
  access_id TEXT NOT NULL REFERENCES access_grants(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  reference_id TEXT NOT NULL,
  amount INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(access_id, kind, reference_id)
);

CREATE INDEX IF NOT EXISTS access_usage_by_grant
  ON access_usage(access_id, kind, created_at DESC);

CREATE TABLE IF NOT EXISTS access_grant_adjustments (
  id TEXT PRIMARY KEY,
  access_id TEXT NOT NULL REFERENCES access_grants(id) ON DELETE CASCADE,
  previous_json TEXT NOT NULL,
  next_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS access_grant_adjustments_by_grant
  ON access_grant_adjustments(access_id, created_at DESC);

CREATE TABLE IF NOT EXISTS parser_tasks (
  id TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
  quota_access_id TEXT REFERENCES access_grants(id) ON DELETE SET NULL,
  source_url TEXT NOT NULL,
  platform_hint TEXT NOT NULL DEFAULT 'other',
  state TEXT NOT NULL,
  progress_json TEXT NOT NULL DEFAULT '{}',
  error_code TEXT,
  error_message TEXT,
  error_retryable INTEGER,
  retry_count INTEGER NOT NULL DEFAULT 0,
  record_id TEXT,
  operation TEXT NOT NULL DEFAULT 'full_parse',
  transcription_provider TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS parser_records (
  id TEXT PRIMARY KEY,
  device_id TEXT NOT NULL DEFAULT '',
  access_id TEXT REFERENCES access_grants(id) ON DELETE SET NULL,
  source_url TEXT NOT NULL,
  platform TEXT NOT NULL,
  title TEXT NOT NULL,
  creator TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  duration_seconds INTEGER NOT NULL DEFAULT 0,
  thumbnail_url TEXT NOT NULL DEFAULT '',
  transcript_text TEXT NOT NULL DEFAULT '',
  transcript_format_version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS note_tasks (
  id TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
  quota_access_id TEXT REFERENCES access_grants(id) ON DELETE SET NULL,
  state TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_name TEXT NOT NULL DEFAULT '',
  source_snapshot_json TEXT NOT NULL DEFAULT '{}',
  basis_transcript TEXT NOT NULL,
  transcript_revision INTEGER NOT NULL DEFAULT 1,
  request_text TEXT NOT NULL DEFAULT '',
  llm_profile_id TEXT,
  generation_route TEXT NOT NULL DEFAULT 'paid',
  proposed_title TEXT NOT NULL DEFAULT '',
  recommendation_json TEXT,
  recommendation_revision INTEGER,
  final_settings_json TEXT,
  outline_json TEXT,
  outline_feedback TEXT,
  progress_json TEXT NOT NULL DEFAULT '{}',
  error_code TEXT,
  error_message TEXT,
  note_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS note_chapters (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES note_tasks(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  content_md TEXT NOT NULL DEFAULT '',
  context_summary TEXT NOT NULL DEFAULT '',
  attempt_count INTEGER NOT NULL DEFAULT 0,
  UNIQUE(task_id, position)
);

CREATE TABLE IF NOT EXISTS notes (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL UNIQUE REFERENCES note_tasks(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  current_markdown TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  integrity_json TEXT NOT NULL DEFAULT '{"status":"ok"}',
  source_snapshot_json TEXT NOT NULL DEFAULT '{}',
  basis_transcript TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS note_versions (
  id TEXT PRIMARY KEY,
  note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  markdown TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS one_ai_initial_per_note
  ON note_versions(note_id) WHERE kind = 'ai_initial';

CREATE TABLE IF NOT EXISTS chapter_candidates (
  id TEXT PRIMARY KEY,
  note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  chapter_id TEXT NOT NULL,
  current_chapter_markdown TEXT NOT NULL,
  candidate_markdown TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS one_pending_candidate_per_chapter
  ON chapter_candidates(note_id, chapter_id) WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS parse_note_links (
  parse_record_id TEXT NOT NULL REFERENCES parser_records(id) ON DELETE CASCADE,
  note_task_id TEXT NOT NULL REFERENCES note_tasks(id) ON DELETE CASCADE,
  PRIMARY KEY(parse_record_id, note_task_id)
);

CREATE TABLE IF NOT EXISTS workflow_events (
  workflow_type TEXT NOT NULL,
  task_id TEXT NOT NULL,
  seq INTEGER NOT NULL,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY(workflow_type, task_id, seq)
);

CREATE INDEX IF NOT EXISTS parser_records_cursor
  ON parser_records(access_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS note_tasks_device_cursor
  ON note_tasks(device_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS notes_cursor
  ON notes(created_at DESC, id DESC);
