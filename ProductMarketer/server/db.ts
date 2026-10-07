import 'dotenv/config'
import { mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { DatabaseSync, type SQLInputValue } from 'node:sqlite'

const databasePath = resolve(process.env.DATABASE_PATH ?? 'storage/productmarketer.sqlite')
mkdirSync(dirname(databasePath), { recursive: true })

export const db = new DatabaseSync(databasePath)
db.exec('PRAGMA foreign_keys = ON; PRAGMA journal_mode = WAL;')

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    job_title TEXT NOT NULL,
    timezone TEXT NOT NULL,
    bio TEXT NOT NULL,
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS settings (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    ai_generation INTEGER NOT NULL DEFAULT 1,
    background_removal INTEGER NOT NULL DEFAULT 1,
    generation_notifications INTEGER NOT NULL DEFAULT 1,
    experimental_styles INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS uploads (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    url TEXT NOT NULL,
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    tool_id TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL,
    choice TEXT NOT NULL,
    prompt TEXT NOT NULL,
    upload_id TEXT REFERENCES uploads(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS generations (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_generation_id TEXT REFERENCES generations(id) ON DELETE SET NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    status TEXT NOT NULL,
    prompt TEXT NOT NULL,
    input_json TEXT NOT NULL,
    usage_json TEXT,
    estimated_cost_cents INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
  );

  CREATE TABLE IF NOT EXISTS outputs (
    id TEXT PRIMARY KEY,
    generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    kind TEXT NOT NULL,
    url TEXT NOT NULL,
    thumbnail_url TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    status TEXT NOT NULL,
    approved INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS scenes (
    id TEXT PRIMARY KEY,
    generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    script TEXT NOT NULL,
    status TEXT NOT NULL,
    output_id TEXT REFERENCES outputs(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS model_providers (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    label TEXT NOT NULL,
    base_url TEXT NOT NULL,
    api_key_encrypted TEXT,
    api_key_iv TEXT,
    api_key_tag TEXT,
    models_json TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'untested',
    last_tested_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, provider)
  );

  CREATE TABLE IF NOT EXISTS model_routes (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    llm_provider TEXT,
    llm_model TEXT,
    vlm_provider TEXT,
    vlm_model TEXT,
    image_provider TEXT,
    image_model TEXT,
    video_provider TEXT,
    video_model TEXT,
    updated_at TEXT NOT NULL
  );

  CREATE INDEX IF NOT EXISTS idx_projects_user_updated ON projects(user_id, updated_at DESC);
  CREATE INDEX IF NOT EXISTS idx_generations_project_created ON generations(project_id, created_at DESC);
  CREATE INDEX IF NOT EXISTS idx_outputs_generation_position ON outputs(generation_id, position);
`)

export const DEMO_USER_ID = 'user_demo_alex'
const now = new Date().toISOString()

db.prepare(`
  INSERT OR IGNORE INTO users (id, first_name, last_name, email, job_title, timezone, bio, created_at)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?)
`).run(DEMO_USER_ID, 'Alex', 'Morgan', 'alex@kora.co', 'Creative Director', 'Europe/Istanbul', 'Building bold product stories for Kora Coffee.', now)

db.prepare(`
  INSERT OR IGNORE INTO settings (
    user_id, ai_generation, background_removal, generation_notifications, experimental_styles, updated_at
  ) VALUES (?, 1, 1, 1, 0, ?)
`).run(DEMO_USER_ID, now)

db.prepare(`
  INSERT OR IGNORE INTO model_routes (
    user_id, llm_provider, llm_model, vlm_provider, vlm_model,
    image_provider, image_model, video_provider, video_model, updated_at
  ) VALUES (?, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, ?)
`).run(DEMO_USER_ID, now)

export function all<T>(sql: string, ...params: SQLInputValue[]): T[] {
  return db.prepare(sql).all(...params) as T[]
}

export function get<T>(sql: string, ...params: SQLInputValue[]): T | undefined {
  return db.prepare(sql).get(...params) as T | undefined
}
