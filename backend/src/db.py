import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("agent.db")

DB_PATH = Path(__file__).parent.parent / "data" / "memory.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target_path = db_path or DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize SQLite database and user_memory table if not exists."""
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_memory (
                    user_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    language_preference TEXT DEFAULT 'Tenglish',
                    facts TEXT NOT NULL,
                    last_interaction TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS escalations (
                    ref_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    student_name TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    issue_summary TEXT NOT NULL,
                    context_checked TEXT NOT NULL,
                    urgency TEXT DEFAULT 'medium',
                    language TEXT DEFAULT 'Tenglish',
                    follow_up_method TEXT DEFAULT 'Teacher Callback',
                    status TEXT DEFAULT 'open',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        logger.info("Database initialized successfully at %s", db_path or DB_PATH)
    finally:
        conn.close()


def sanitize_summary(text: str) -> str:
    """Scrub sensitive PII (passwords, OTPs, PINs, bank accounts, cards) from summary text."""
    if not text:
        return ""
    import re

    clean = text
    # Mask passwords / secrets (e.g. 'password is 12345', 'secret: abc', 'password=xyz')
    clean = re.sub(
        r"(?i)\b(password|passcode|secret|pin|otp|cvv)\b.*?\b[\w\d@#$%^&*!]{3,}\b",
        r"\1: [REDACTED]",
        clean,
    )
    # Mask credit/debit card numbers (13-19 digits with spaces/dashes)
    clean = re.sub(r"\b(?:\d[ -]*?){13,19}\b", "[REDACTED_CARD]", clean)
    # Mask standalone 4-16 digit numbers (PINs, OTPs, account numbers, Aadhaar)
    clean = re.sub(r"\b\d{4,16}\b", "[REDACTED_NUMBER]", clean)
    return clean


def save_escalation(
    ref_id: str,
    user_id: str,
    student_name: str,
    reason: str,
    issue_summary: str,
    context_checked: str,
    urgency: str = "medium",
    language: str = "Tenglish",
    follow_up_method: str = "Teacher Callback",
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Save a human escalation request to SQLite database."""
    init_db(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    clean_summary = sanitize_summary(issue_summary)
    clean_context = sanitize_summary(context_checked)

    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO escalations (
                    ref_id, user_id, student_name, reason, issue_summary,
                    context_checked, urgency, language, follow_up_method, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
                ON CONFLICT(ref_id) DO UPDATE SET
                    issue_summary = excluded.issue_summary,
                    context_checked = excluded.context_checked,
                    urgency = excluded.urgency,
                    updated_at = excluded.updated_at
                """,
                (
                    ref_id,
                    user_id.strip().lower(),
                    student_name.strip(),
                    reason.strip(),
                    clean_summary,
                    clean_context,
                    urgency.strip().lower(),
                    language.strip(),
                    follow_up_method.strip(),
                    now_iso,
                    now_iso,
                ),
            )
        logger.info("Saved escalation request %s for user %s", ref_id, user_id)
        return {
            "ref_id": ref_id,
            "user_id": user_id,
            "student_name": student_name,
            "reason": reason,
            "issue_summary": clean_summary,
            "context_checked": clean_context,
            "urgency": urgency,
            "language": language,
            "follow_up_method": follow_up_method,
            "status": "open",
            "created_at": now_iso,
            "updated_at": now_iso,
        }
    finally:
        conn.close()


def get_escalations(
    status: Optional[str] = None, db_path: Optional[Path] = None
) -> list[dict[str, Any]]:
    """Retrieve all human escalation requests from SQLite."""
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        if status:
            cursor.execute(
                "SELECT * FROM escalations WHERE LOWER(status) = ? ORDER BY created_at DESC",
                (status.strip().lower(),),
            )
        else:
            cursor.execute("SELECT * FROM escalations ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_escalation_status(
    ref_id: str, status: str, db_path: Optional[Path] = None
) -> bool:
    """Update status of an escalation ticket (e.g. 'open' -> 'in_progress' -> 'resolved')."""
    init_db(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE escalations SET status = ?, updated_at = ? WHERE UPPER(ref_id) = ?",
                (status.strip().lower(), now_iso, ref_id.strip().upper()),
            )
            updated = cursor.rowcount > 0
            if updated:
                logger.info("Updated escalation %s status to %s", ref_id, status)
            return updated
    finally:
        conn.close()


def get_user_memory(
    user_id: str, db_path: Optional[Path] = None
) -> Optional[dict[str, Any]]:
    """Retrieve caller memory from SQLite by user_id."""
    init_db(db_path)
    clean_user_id = user_id.strip().lower()
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, name, language_preference, facts, last_interaction FROM user_memory WHERE LOWER(user_id) = ?",
            (clean_user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        facts = {}
        if row["facts"]:
            try:
                facts = json.loads(row["facts"])
            except Exception as e:
                logger.error("Failed to parse facts JSON for %s: %s", user_id, e)
                facts = {}

        return {
            "user_id": row["user_id"],
            "name": row["name"],
            "language_preference": row["language_preference"],
            "facts": facts,
            "last_interaction": row["last_interaction"],
        }
    finally:
        conn.close()


def save_user_memory(
    user_id: str,
    name: str,
    language_preference: str = "Tenglish",
    facts: Optional[dict[str, Any]] = None,
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Save or update caller memory in SQLite."""
    init_db(db_path)
    clean_user_id = user_id.strip().lower()
    now_iso = datetime.now(timezone.utc).isoformat()
    facts_dict = facts or {}
    facts_json = json.dumps(facts_dict)

    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO user_memory (user_id, name, language_preference, facts, last_interaction)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    name = excluded.name,
                    language_preference = excluded.language_preference,
                    facts = excluded.facts,
                    last_interaction = excluded.last_interaction
                """,
                (clean_user_id, name, language_preference, facts_json, now_iso),
            )
        logger.info("Saved user memory for %s (%s)", name, clean_user_id)
        return {
            "user_id": clean_user_id,
            "name": name,
            "language_preference": language_preference,
            "facts": facts_dict,
            "last_interaction": now_iso,
        }
    finally:
        conn.close()


def delete_user_memory(user_id: str, db_path: Optional[Path] = None) -> bool:
    """Delete caller memory from SQLite ('forget me')."""
    init_db(db_path)
    clean_user_id = user_id.strip().lower()
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_memory WHERE LOWER(user_id) = ?", (clean_user_id,)
            )
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info("Deleted user memory for %s", clean_user_id)
            return deleted
    finally:
        conn.close()
