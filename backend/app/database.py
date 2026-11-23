"""Database Access Layer for Job Metadata Persistence.

Uses SQLite with Write-Ahead Logging (WAL) for concurrency, parameter binding to prevent
SQL injection, and thread-safe operations.
"""

import json
import sqlite3
import threading
import time
from typing import Optional, List
from pathlib import Path

from backend.app.config import settings
from backend.app.models import JobRecord, JobStatus, PipelineStage, WorkflowType

_lock = threading.Lock()

def get_connection() -> sqlite3.Connection:
    """Returns a SQLite connection configured with Row factory and WAL mode."""
    conn = sqlite3.connect(str(settings.db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db() -> None:
    """Initializes the database schema if it doesn't already exist."""
    with _lock:
        conn = get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id TEXT PRIMARY KEY,
                        upload_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        workflow_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        stage TEXT NOT NULL,
                        config_json TEXT NOT NULL,
                        geometry_analysis_json TEXT,
                        mesh_stats_json TEXT,
                        error_message TEXT,
                        created_at REAL NOT NULL,
                        started_at REAL,
                        completed_at REAL,
                        container_id TEXT,
                        log_file TEXT,
                        archive_file TEXT,
                        case_folder TEXT,
                        hidden_from_history INTEGER NOT NULL DEFAULT 0
                    );
                    """
                )
                columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
                if "case_folder" not in columns:
                    conn.execute("ALTER TABLE jobs ADD COLUMN case_folder TEXT")
                if "hidden_from_history" not in columns:
                    conn.execute("ALTER TABLE jobs ADD COLUMN hidden_from_history INTEGER NOT NULL DEFAULT 0")
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
                    """
                )
        finally:
            conn.close()

def create_job(job: JobRecord) -> None:
    """Inserts a new job record."""
    with _lock:
        conn = get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO jobs (
                        job_id, upload_id, filename, workflow_type, status, stage,
                        config_json, geometry_analysis_json, mesh_stats_json,
                        error_message, created_at, started_at, completed_at,
                        container_id, log_file, archive_file, case_folder
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        job.job_id,
                        job.upload_id,
                        job.filename,
                        job.workflow_type.value,
                        job.status.value,
                        job.stage.value,
                        job.config_json,
                        job.geometry_analysis_json,
                        job.mesh_stats_json,
                        job.error_message,
                        job.created_at,
                        job.started_at,
                        job.completed_at,
                        job.container_id,
                        job.log_file,
                        job.archive_file,
                        job.case_folder,
                    ),
                )
        finally:
            conn.close()

def row_to_job(row: sqlite3.Row) -> JobRecord:
    """Converts a SQLite row to a JobRecord model."""
    return JobRecord(
        job_id=row["job_id"],
        upload_id=row["upload_id"],
        filename=row["filename"],
        workflow_type=WorkflowType(row["workflow_type"]),
        status=JobStatus(row["status"]),
        stage=PipelineStage(row["stage"]),
        config_json=row["config_json"],
        geometry_analysis_json=row["geometry_analysis_json"],
        mesh_stats_json=row["mesh_stats_json"],
        error_message=row["error_message"],
        created_at=row["created_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        container_id=row["container_id"],
        log_file=row["log_file"],
        archive_file=row["archive_file"],
        case_folder=row["case_folder"],
    )

def get_job(job_id: str) -> Optional[JobRecord]:
    """Retrieves a single job by its ID."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT * FROM jobs WHERE job_id = ?;", (job_id,))
        row = cur.fetchone()
        if not row:
            return None
        return row_to_job(row)
    finally:
        conn.close()

def list_jobs(limit: int = 50, offset: int = 0) -> List[JobRecord]:
    """Lists recent jobs ordered by creation timestamp descending."""
    conn = get_connection()
    try:
        cur = conn.execute(
                "SELECT * FROM jobs WHERE hidden_from_history = 0 ORDER BY created_at DESC LIMIT ? OFFSET ?;",
            (limit, offset),
        )
        return [row_to_job(row) for row in cur.fetchall()]
    finally:
        conn.close()

def clear_job_history(job_id: Optional[str] = None) -> int:
    """Hide finished jobs from history while retaining their case data."""
    query = """
        UPDATE jobs SET hidden_from_history = 1
        WHERE hidden_from_history = 0 AND status IN (?, ?, ?)
    """
    params = [JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value]
    if job_id is not None:
        query += " AND job_id = ?"
        params.append(job_id)
    with _lock:
        conn = get_connection()
        try:
            with conn:
                return conn.execute(query, params).rowcount
        finally:
            conn.close()

def update_job_status(
    job_id: str,
    status: JobStatus,
    stage: Optional[PipelineStage] = None,
    error_message: Optional[str] = None,
    started_at: Optional[float] = None,
    completed_at: Optional[float] = None,
    container_id: Optional[str] = None,
    archive_file: Optional[str] = None,
    mesh_stats_json: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """Updates selected fields of an existing job."""
    with _lock:
        conn = get_connection()
        try:
            updates = ["status = ?"]
            params = [status.value]

            if stage is not None:
                updates.append("stage = ?")
                params.append(stage.value)
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)
            if started_at is not None:
                updates.append("started_at = ?")
                params.append(started_at)
            if completed_at is not None:
                updates.append("completed_at = ?")
                params.append(completed_at)
            if container_id is not None:
                updates.append("container_id = ?")
                params.append(container_id)
            if archive_file is not None:
                updates.append("archive_file = ?")
                params.append(archive_file)
            if mesh_stats_json is not None:
                updates.append("mesh_stats_json = ?")
                params.append(mesh_stats_json)
            if log_file is not None:
                updates.append("log_file = ?")
                params.append(log_file)

            params.append(job_id)
            query = f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?;"
            with conn:
                conn.execute(query, tuple(params))
        finally:
            conn.close()

def queue_remesh(job_id: str) -> bool:
    """Queue another attempt while retaining the previous results."""
    with _lock:
        conn = get_connection()
        try:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE jobs
                    SET status = ?, stage = ?, started_at = NULL, completed_at = NULL,
                        error_message = NULL, container_id = NULL, hidden_from_history = 0
                    WHERE job_id = ? AND status IN (?, ?, ?)
                    """,
                    (JobStatus.QUEUED.value, PipelineStage.UPLOAD.value, job_id,
                     JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value),
                )
                return cursor.rowcount == 1
        finally:
            conn.close()

def recover_stale_jobs() -> int:
    """Marks any 'running' or 'queued' jobs as 'failed' upon backend restart.
    
    Prevents jobs from being stuck indefinitely if the backend crashed or was restarted.
    """
    with _lock:
        conn = get_connection()
        try:
            now = time.time()
            with conn:
                cur = conn.execute(
                    """
                    UPDATE jobs
                    SET status = ?,
                        error_message = ?,
                        completed_at = ?
                    WHERE status IN (?, ?);
                    """,
                    (
                        JobStatus.FAILED.value,
                        "Server was restarted while job was queued or in progress.",
                        now,
                        JobStatus.RUNNING.value,
                        JobStatus.QUEUED.value,
                    ),
                )
                return cur.rowcount
        finally:
            conn.close()
