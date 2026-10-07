from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from .config import DATABASE_PATH, PROJECTS_ROOT, ensure_runtime_directories
from .modes import MODES
from .models import ProjectCreate


UPDATABLE_FIELDS = {
    "title",
    "status",
    "stage",
    "progress",
    "error",
    "task_id",
    "output_path",
    "cancel_requested",
    "updated_at",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    ensure_runtime_directories()
    database = sqlite3.connect(DATABASE_PATH, timeout=30)
    database.row_factory = sqlite3.Row
    try:
        yield database
        database.commit()
    finally:
        database.close()


def initialize_database() -> None:
    with connection() as database:
        database.execute("PRAGMA journal_mode=WAL")
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                mode_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                topic TEXT NOT NULL,
                title TEXT NOT NULL,
                language TEXT NOT NULL,
                duration INTEGER NOT NULL,
                scenes INTEGER NOT NULL,
                format TEXT NOT NULL,
                settings_json TEXT NOT NULL,
                status TEXT NOT NULL,
                stage TEXT NOT NULL,
                progress INTEGER NOT NULL,
                error TEXT,
                task_id TEXT,
                output_path TEXT,
                cancel_requested INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        database.execute(
            "CREATE INDEX IF NOT EXISTS projects_created_idx "
            "ON projects(created_at DESC)"
        )
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS schedules (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                run_at TEXT NOT NULL,
                timezone TEXT NOT NULL,
                status TEXT NOT NULL,
                task_id TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
            """
        )
        database.execute(
            "CREATE INDEX IF NOT EXISTS schedules_due_idx "
            "ON schedules(status, run_at)"
        )
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS connections (
                provider TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                account_label TEXT,
                encrypted_tokens TEXT,
                scopes_json TEXT NOT NULL,
                connected_at TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                nodes_json TEXT NOT NULL,
                edges_json TEXT NOT NULL,
                status TEXT NOT NULL,
                last_run_at TEXT,
                last_run_status TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        database.execute(
            "CREATE INDEX IF NOT EXISTS workflows_updated_idx "
            "ON workflows(updated_at DESC)"
        )
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_runs (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                status TEXT NOT NULL,
                project_id TEXT,
                schedule_id TEXT,
                destination TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(workflow_id) REFERENCES workflows(id)
            )
            """
        )
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_provider_credentials (
                provider TEXT PRIMARY KEY,
                encrypted_api_key TEXT NOT NULL,
                key_hint TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_models (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                provider TEXT NOT NULL,
                model_identifier TEXT NOT NULL,
                configuration_json TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                is_default INTEGER NOT NULL DEFAULT 0,
                built_in INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        database.execute(
            "CREATE INDEX IF NOT EXISTS ai_models_updated_idx "
            "ON ai_models(updated_at DESC)"
        )
        now = utc_now()
        database.execute(
            """
            INSERT OR IGNORE INTO ai_models (
                id, name, provider, model_identifier, configuration_json,
                enabled, is_default, built_in, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 1, 1, 1, ?, ?)
            """,
            (
                "preset-flux-schnell",
                "FLUX Schnell",
                "replicate",
                "black-forest-labs/flux-schnell",
                json.dumps(
                    {
                        "aspect_ratio": "9:16",
                        "megapixels": "1",
                        "num_outputs": 1,
                        "output_format": "png",
                        "output_quality": 95,
                        "num_inference_steps": 4,
                    }
                ),
                now,
                now,
            ),
        )
        database.execute(
            """
            INSERT OR IGNORE INTO ai_models (
                id, name, provider, model_identifier, configuration_json,
                enabled, is_default, built_in, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 1, 0, 1, ?, ?)
            """,
            (
                "preset-gemini-25-flash-image",
                "Gemini 2.5 Flash Image",
                "gemini",
                "gemini-2.5-flash-image",
                json.dumps(
                    {
                        "responseModalities": ["IMAGE"],
                        "responseFormat": {
                            "image": {
                                "aspectRatio": "9:16",
                            }
                        },
                    }
                ),
                now,
                now,
            ),
        )
        database.execute(
            """
            INSERT OR IGNORE INTO ai_models (
                id, name, provider, model_identifier, configuration_json,
                enabled, is_default, built_in, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 1, 0, 1, ?, ?)
            """,
            (
                "preset-together-flux-schnell",
                "Together FLUX.1 Schnell",
                "together",
                "black-forest-labs/FLUX.1-schnell",
                json.dumps(
                    {
                        "aspect_ratio": "9:16",
                        "steps": 4,
                        "n": 1,
                        "output_format": "png",
                        "response_format": "url",
                    }
                ),
                now,
                now,
            ),
        )


def project_directory(project_id: str) -> Path:
    return (PROJECTS_ROOT / project_id).resolve()


def project_log_path(project_id: str) -> Path:
    return project_directory(project_id) / "generation.log"


def create_project(payload: ProjectCreate) -> dict[str, Any]:
    initialize_database()
    project_id = uuid4().hex
    now = utc_now()
    mode = MODES[payload.mode_id]
    directory = project_directory(project_id)
    (directory / "outputs").mkdir(parents=True, exist_ok=False)
    values = {
        "id": project_id,
        "mode_id": payload.mode_id,
        "mode": mode.name,
        "topic": payload.topic,
        "title": payload.topic,
        "language": payload.language,
        "duration": payload.duration,
        "scenes": payload.scenes,
        "format": payload.format,
        "settings_json": payload.settings.model_dump_json(),
        "status": "draft",
        "stage": "Ready to generate",
        "progress": 0,
        "error": None,
        "task_id": None,
        "output_path": None,
        "cancel_requested": 0,
        "created_at": now,
        "updated_at": now,
    }
    with connection() as database:
        database.execute(
            """
            INSERT INTO projects (
                id, mode_id, mode, topic, title, language, duration, scenes,
                format, settings_json, status, stage, progress, error, task_id,
                output_path, cancel_requested, created_at, updated_at
            ) VALUES (
                :id, :mode_id, :mode, :topic, :title, :language, :duration,
                :scenes, :format, :settings_json, :status, :stage, :progress,
                :error, :task_id, :output_path, :cancel_requested, :created_at,
                :updated_at
            )
            """,
            values,
        )
    (directory / "project.json").write_text(
        payload.model_dump_json(indent=2),
        encoding="utf-8",
    )
    project = get_project(project_id)
    if project is None:
        raise RuntimeError("Project could not be read after creation.")
    return project


def _row_to_project(row: sqlite3.Row) -> dict[str, Any]:
    project = dict(row)
    project["settings"] = json.loads(project.pop("settings_json"))
    project["cancel_requested"] = bool(project["cancel_requested"])
    output_path = project.pop("output_path")
    project["output_url"] = (
        f"/api/projects/{project['id']}/download" if output_path else None
    )
    return project


def get_project(project_id: str) -> dict[str, Any] | None:
    initialize_database()
    with connection() as database:
        row = database.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    return _row_to_project(row) if row else None


def get_project_output_path(project_id: str) -> Path | None:
    with connection() as database:
        row = database.execute(
            "SELECT output_path FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    if not row or not row["output_path"]:
        return None
    return Path(row["output_path"]).resolve()


def list_projects() -> list[dict[str, Any]]:
    initialize_database()
    with connection() as database:
        rows = database.execute(
            "SELECT * FROM projects ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_project(row) for row in rows]


def update_project(project_id: str, **changes: Any) -> dict[str, Any]:
    unknown_fields = set(changes) - UPDATABLE_FIELDS
    if unknown_fields:
        raise ValueError(f"Unsupported project fields: {sorted(unknown_fields)}")
    changes["updated_at"] = utc_now()
    assignments = ", ".join(f"{field} = :{field}" for field in changes)
    changes["id"] = project_id
    with connection() as database:
        result = database.execute(
            f"UPDATE projects SET {assignments} WHERE id = :id", changes
        )
        if result.rowcount != 1:
            raise KeyError(project_id)
    project = get_project(project_id)
    if project is None:
        raise KeyError(project_id)
    return project


def is_cancel_requested(project_id: str) -> bool:
    with connection() as database:
        row = database.execute(
            "SELECT cancel_requested FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    return bool(row and row["cancel_requested"])


def reset_for_generation(project_id: str) -> dict[str, Any]:
    return update_project(
        project_id,
        status="queued",
        stage="Waiting for a worker",
        progress=2,
        error=None,
        output_path=None,
        cancel_requested=0,
    )


def read_project_logs(project_id: str, limit: int = 200) -> list[str]:
    path = project_log_path(project_id)
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]


SCHEDULE_UPDATABLE_FIELDS = {
    "run_at",
    "status",
    "task_id",
    "error",
    "updated_at",
}


def _row_to_schedule(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def create_schedule(
    project_id: str,
    run_at: datetime,
    timezone: str,
) -> dict[str, Any]:
    initialize_database()
    schedule_id = uuid4().hex
    now = utc_now()
    with connection() as database:
        database.execute(
            """
            INSERT INTO schedules (
                id, project_id, run_at, timezone, status, task_id, error,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'scheduled', NULL, NULL, ?, ?)
            """,
            (schedule_id, project_id, run_at.isoformat(), timezone, now, now),
        )
    schedule = get_schedule(schedule_id)
    if schedule is None:
        raise RuntimeError("Schedule could not be read after creation.")
    return schedule


def get_schedule(schedule_id: str) -> dict[str, Any] | None:
    initialize_database()
    with connection() as database:
        row = database.execute(
            """
            SELECT schedules.*, projects.title AS project_title,
                   projects.mode AS project_mode
            FROM schedules
            JOIN projects ON projects.id = schedules.project_id
            WHERE schedules.id = ?
            """,
            (schedule_id,),
        ).fetchone()
    return _row_to_schedule(row) if row else None


def list_schedules() -> list[dict[str, Any]]:
    initialize_database()
    with connection() as database:
        rows = database.execute(
            """
            SELECT schedules.*, projects.title AS project_title,
                   projects.mode AS project_mode
            FROM schedules
            JOIN projects ON projects.id = schedules.project_id
            ORDER BY schedules.run_at ASC
            """
        ).fetchall()
    return [_row_to_schedule(row) for row in rows]


def update_schedule(schedule_id: str, **changes: Any) -> dict[str, Any]:
    unknown_fields = set(changes) - SCHEDULE_UPDATABLE_FIELDS
    if unknown_fields:
        raise ValueError(f"Unsupported schedule fields: {sorted(unknown_fields)}")
    changes["updated_at"] = utc_now()
    assignments = ", ".join(f"{field} = :{field}" for field in changes)
    changes["id"] = schedule_id
    with connection() as database:
        result = database.execute(
            f"UPDATE schedules SET {assignments} WHERE id = :id", changes
        )
        if result.rowcount != 1:
            raise KeyError(schedule_id)
    schedule = get_schedule(schedule_id)
    if schedule is None:
        raise KeyError(schedule_id)
    return schedule


def claim_due_schedules(limit: int = 20) -> list[dict[str, Any]]:
    initialize_database()
    now = utc_now()
    with connection() as database:
        database.execute("BEGIN IMMEDIATE")
        rows = database.execute(
            """
            SELECT id FROM schedules
            WHERE status = 'scheduled' AND run_at <= ?
            ORDER BY run_at ASC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
        schedule_ids = [row["id"] for row in rows]
        for schedule_id in schedule_ids:
            database.execute(
                """
                UPDATE schedules
                SET status = 'dispatching', updated_at = ?
                WHERE id = ? AND status = 'scheduled'
                """,
                (now, schedule_id),
            )
    return [
        schedule
        for schedule_id in schedule_ids
        if (schedule := get_schedule(schedule_id)) is not None
    ]


def save_oauth_state(provider: str, state: str, expires_at: datetime) -> None:
    initialize_database()
    with connection() as database:
        database.execute(
            "INSERT INTO oauth_states (state, provider, expires_at) VALUES (?, ?, ?)",
            (state, provider, expires_at.isoformat()),
        )


def consume_oauth_state(provider: str, state: str) -> bool:
    initialize_database()
    with connection() as database:
        row = database.execute(
            "SELECT expires_at FROM oauth_states WHERE state = ? AND provider = ?",
            (state, provider),
        ).fetchone()
        database.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
    if not row:
        return False
    return datetime.fromisoformat(row["expires_at"]) > datetime.now(UTC)


def get_connection(provider: str) -> dict[str, Any] | None:
    initialize_database()
    with connection() as database:
        row = database.execute(
            "SELECT * FROM connections WHERE provider = ?", (provider,)
        ).fetchone()
    if not row:
        return None
    value = dict(row)
    value["scopes"] = json.loads(value.pop("scopes_json"))
    return value


def save_connection(
    provider: str,
    *,
    account_label: str,
    encrypted_tokens: str | None,
    scopes: list[str],
) -> dict[str, Any]:
    now = utc_now()
    with connection() as database:
        database.execute(
            """
            INSERT INTO connections (
                provider, status, account_label, encrypted_tokens, scopes_json,
                connected_at, updated_at
            ) VALUES (?, 'connected', ?, ?, ?, ?, ?)
            ON CONFLICT(provider) DO UPDATE SET
                status = 'connected',
                account_label = excluded.account_label,
                encrypted_tokens = excluded.encrypted_tokens,
                scopes_json = excluded.scopes_json,
                connected_at = excluded.connected_at,
                updated_at = excluded.updated_at
            """,
            (
                provider,
                account_label,
                encrypted_tokens,
                json.dumps(scopes),
                now,
                now,
            ),
        )
    connection_value = get_connection(provider)
    if connection_value is None:
        raise RuntimeError("Connection could not be saved.")
    return connection_value


def disconnect_connection(provider: str) -> None:
    initialize_database()
    now = utc_now()
    with connection() as database:
        database.execute(
            """
            INSERT INTO connections (
                provider, status, account_label, encrypted_tokens, scopes_json,
                connected_at, updated_at
            ) VALUES (?, 'disconnected', NULL, NULL, '[]', NULL, ?)
            ON CONFLICT(provider) DO UPDATE SET
                status = 'disconnected',
                account_label = NULL,
                encrypted_tokens = NULL,
                scopes_json = '[]',
                connected_at = NULL,
                updated_at = excluded.updated_at
            """,
            (provider, now),
        )


def get_ai_provider_credential(provider: str) -> dict[str, Any] | None:
    initialize_database()
    with connection() as database:
        row = database.execute(
            "SELECT * FROM ai_provider_credentials WHERE provider = ?",
            (provider,),
        ).fetchone()
    return dict(row) if row else None


def save_ai_provider_credential(
    provider: str,
    *,
    encrypted_api_key: str,
    key_hint: str,
) -> dict[str, Any]:
    initialize_database()
    now = utc_now()
    with connection() as database:
        database.execute(
            """
            INSERT INTO ai_provider_credentials (
                provider, encrypted_api_key, key_hint, updated_at
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(provider) DO UPDATE SET
                encrypted_api_key = excluded.encrypted_api_key,
                key_hint = excluded.key_hint,
                updated_at = excluded.updated_at
            """,
            (provider, encrypted_api_key, key_hint, now),
        )
    stored = get_ai_provider_credential(provider)
    if stored is None:
        raise RuntimeError("AI provider credential could not be saved.")
    return stored


def delete_ai_provider_credential(provider: str) -> bool:
    initialize_database()
    with connection() as database:
        result = database.execute(
            "DELETE FROM ai_provider_credentials WHERE provider = ?",
            (provider,),
        )
    return result.rowcount == 1


def _row_to_ai_model(row: sqlite3.Row) -> dict[str, Any]:
    value = dict(row)
    value["configuration"] = json.loads(value.pop("configuration_json"))
    value["enabled"] = bool(value["enabled"])
    value["is_default"] = bool(value["is_default"])
    value["built_in"] = bool(value["built_in"])
    return value


def get_ai_model(model_id: str) -> dict[str, Any] | None:
    initialize_database()
    with connection() as database:
        row = database.execute(
            "SELECT * FROM ai_models WHERE id = ?",
            (model_id,),
        ).fetchone()
    return _row_to_ai_model(row) if row else None


def list_ai_models(*, enabled_only: bool = False) -> list[dict[str, Any]]:
    initialize_database()
    query = "SELECT * FROM ai_models"
    if enabled_only:
        query += " WHERE enabled = 1"
    query += " ORDER BY is_default DESC, built_in DESC, updated_at DESC"
    with connection() as database:
        rows = database.execute(query).fetchall()
    return [_row_to_ai_model(row) for row in rows]


def create_ai_model(
    *,
    name: str,
    provider: str,
    model_identifier: str,
    configuration: dict[str, Any],
    enabled: bool,
    is_default: bool,
) -> dict[str, Any]:
    initialize_database()
    model_id = uuid4().hex
    now = utc_now()
    with connection() as database:
        if is_default:
            database.execute("UPDATE ai_models SET is_default = 0")
        database.execute(
            """
            INSERT INTO ai_models (
                id, name, provider, model_identifier, configuration_json,
                enabled, is_default, built_in, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                model_id,
                name,
                provider,
                model_identifier,
                json.dumps(configuration),
                int(enabled),
                int(is_default),
                now,
                now,
            ),
        )
    model = get_ai_model(model_id)
    if model is None:
        raise RuntimeError("AI model could not be saved.")
    return model


def update_ai_model(
    model_id: str,
    *,
    name: str,
    provider: str,
    model_identifier: str,
    configuration: dict[str, Any],
    enabled: bool,
    is_default: bool,
) -> dict[str, Any]:
    initialize_database()
    now = utc_now()
    with connection() as database:
        if is_default:
            database.execute(
                "UPDATE ai_models SET is_default = 0 WHERE id != ?",
                (model_id,),
            )
        result = database.execute(
            """
            UPDATE ai_models
            SET name = ?, provider = ?, model_identifier = ?,
                configuration_json = ?, enabled = ?, is_default = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                name,
                provider,
                model_identifier,
                json.dumps(configuration),
                int(enabled),
                int(is_default),
                now,
                model_id,
            ),
        )
        if result.rowcount != 1:
            raise KeyError(model_id)
    model = get_ai_model(model_id)
    if model is None:
        raise KeyError(model_id)
    return model


def delete_ai_model(model_id: str) -> bool:
    initialize_database()
    with connection() as database:
        row = database.execute(
            "SELECT built_in FROM ai_models WHERE id = ?",
            (model_id,),
        ).fetchone()
        if row is None:
            raise KeyError(model_id)
        if bool(row["built_in"]):
            raise ValueError("Built-in model presets cannot be deleted.")
        result = database.execute(
            "DELETE FROM ai_models WHERE id = ?",
            (model_id,),
        )
    return result.rowcount == 1


def _row_to_workflow(row: sqlite3.Row) -> dict[str, Any]:
    value = dict(row)
    value["nodes"] = json.loads(value.pop("nodes_json"))
    value["edges"] = json.loads(value.pop("edges_json"))
    return value


def create_workflow(
    *,
    name: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    status: str,
) -> dict[str, Any]:
    initialize_database()
    workflow_id = uuid4().hex
    now = utc_now()
    with connection() as database:
        database.execute(
            """
            INSERT INTO workflows (
                id, name, nodes_json, edges_json, status, last_run_at,
                last_run_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?)
            """,
            (
                workflow_id,
                name,
                json.dumps(nodes),
                json.dumps(edges),
                status,
                now,
                now,
            ),
        )
    workflow = get_workflow(workflow_id)
    if workflow is None:
        raise RuntimeError("Workflow could not be read after creation.")
    return workflow


def get_workflow(workflow_id: str) -> dict[str, Any] | None:
    initialize_database()
    with connection() as database:
        row = database.execute(
            "SELECT * FROM workflows WHERE id = ?", (workflow_id,)
        ).fetchone()
    return _row_to_workflow(row) if row else None


def list_workflows() -> list[dict[str, Any]]:
    initialize_database()
    with connection() as database:
        rows = database.execute(
            "SELECT * FROM workflows ORDER BY updated_at DESC"
        ).fetchall()
    return [_row_to_workflow(row) for row in rows]


def update_workflow(
    workflow_id: str,
    *,
    name: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    status: str,
) -> dict[str, Any]:
    with connection() as database:
        result = database.execute(
            """
            UPDATE workflows
            SET name = ?, nodes_json = ?, edges_json = ?, status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                name,
                json.dumps(nodes),
                json.dumps(edges),
                status,
                utc_now(),
                workflow_id,
            ),
        )
        if result.rowcount != 1:
            raise KeyError(workflow_id)
    workflow = get_workflow(workflow_id)
    if workflow is None:
        raise KeyError(workflow_id)
    return workflow


def record_workflow_run(
    workflow_id: str,
    *,
    status: str,
    project_id: str | None,
    schedule_id: str | None,
    destination: str | None,
    error: str | None = None,
) -> dict[str, Any]:
    run_id = uuid4().hex
    now = utc_now()
    with connection() as database:
        database.execute(
            """
            INSERT INTO workflow_runs (
                id, workflow_id, status, project_id, schedule_id,
                destination, error, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                workflow_id,
                status,
                project_id,
                schedule_id,
                destination,
                error,
                now,
            ),
        )
        database.execute(
            """
            UPDATE workflows
            SET last_run_at = ?, last_run_status = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, status, now, workflow_id),
        )
    return {
        "id": run_id,
        "workflow_id": workflow_id,
        "status": status,
        "project_id": project_id,
        "schedule_id": schedule_id,
        "destination": destination,
        "error": error,
        "created_at": now,
    }
