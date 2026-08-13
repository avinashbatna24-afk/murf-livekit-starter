import contextlib
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS call_logs (
                    call_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    caller_name TEXT NOT NULL,
                    channel TEXT DEFAULT 'Browser',
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds INTEGER DEFAULT 0,
                    outcome TEXT DEFAULT 'in_progress',
                    failure_reason TEXT DEFAULT '',
                    exercises_completed INTEGER DEFAULT 0,
                    escalation_created INTEGER DEFAULT 0,
                    memory_saved INTEGER DEFAULT 0,
                    graceful_hangup INTEGER DEFAULT 0,
                    topic_discussed TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            with contextlib.suppress(Exception):
                conn.execute(
                    "ALTER TABLE call_logs ADD COLUMN graceful_hangup INTEGER DEFAULT 0"
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


def record_call_start(
    call_id: str,
    user_id: str,
    caller_name: str,
    channel: str = "Browser",
    topic_discussed: str = "",
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Record initial call start record in call_logs."""
    init_db(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    clean_user = sanitize_summary(user_id)
    clean_name = sanitize_summary(caller_name)
    clean_topic = sanitize_summary(topic_discussed)

    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO call_logs (
                    call_id, user_id, caller_name, channel, start_time,
                    outcome, failure_reason, exercises_completed, escalation_created,
                    memory_saved, topic_discussed, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'in_progress', '', 0, 0, 0, ?, ?, ?)
                ON CONFLICT(call_id) DO UPDATE SET
                    caller_name = excluded.caller_name,
                    updated_at = excluded.updated_at
                """,
                (
                    call_id,
                    clean_user,
                    clean_name,
                    channel,
                    now_iso,
                    clean_topic,
                    now_iso,
                    now_iso,
                ),
            )
        logger.info("Call start recorded: %s (%s)", call_id, channel)
        return {"call_id": call_id, "status": "started"}
    finally:
        conn.close()


def update_call_progress(
    call_id: str,
    exercises_inc: int = 0,
    escalation_created: Optional[bool] = None,
    memory_saved: Optional[bool] = None,
    graceful_hangup: Optional[bool] = None,
    topic_discussed: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Update call details during call session (e.g. quiz completed, escalation created)."""
    init_db(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM call_logs WHERE call_id = ?", (call_id,))
            row = cursor.fetchone()
            if not row:
                return

            row_keys = row.keys() if hasattr(row, "keys") else []
            ex_count = row["exercises_completed"] + exercises_inc
            esc = (
                row["escalation_created"]
                if escalation_created is None
                else (1 if escalation_created else 0)
            )
            mem = (
                row["memory_saved"]
                if memory_saved is None
                else (1 if memory_saved else 0)
            )
            h_up = (
                (row["graceful_hangup"] if "graceful_hangup" in row_keys else 0)
                if graceful_hangup is None
                else (1 if graceful_hangup else 0)
            )
            top = (
                row["topic_discussed"]
                if topic_discussed is None
                else sanitize_summary(topic_discussed)
            )

            # Evaluate success criteria
            new_outcome = row["outcome"]
            new_reason = row["failure_reason"] or ""

            is_success = (
                ex_count > 0
                or esc == 1
                or mem == 1
                or h_up == 1
                or (top and top.strip() != "General Practice")
            )
            if is_success:
                new_outcome = "successful"
                new_reason = ""

            cursor.execute(
                """
                UPDATE call_logs SET
                    exercises_completed = ?,
                    escalation_created = ?,
                    memory_saved = ?,
                    graceful_hangup = ?,
                    topic_discussed = ?,
                    outcome = ?,
                    failure_reason = ?,
                    updated_at = ?
                WHERE call_id = ?
                """,
                (
                    ex_count,
                    esc,
                    mem,
                    h_up,
                    top,
                    new_outcome,
                    new_reason,
                    now_iso,
                    call_id,
                ),
            )
    finally:
        conn.close()


def record_call_end(
    call_id: str,
    outcome: Optional[str] = None,
    failure_reason: str = "",
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Finalize call log when session ends. Calculates duration and determines outcome."""
    init_db(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    clean_reason = sanitize_summary(failure_reason)
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM call_logs WHERE call_id = ?", (call_id,))
            row = cursor.fetchone()
            if not row:
                record_call_start(
                    call_id, "student", "Student", "Browser", db_path=db_path
                )
                cursor.execute("SELECT * FROM call_logs WHERE call_id = ?", (call_id,))
                row = cursor.fetchone()

            try:
                start_dt = datetime.fromisoformat(row["start_time"])
                end_dt = datetime.now(timezone.utc)
                duration = max(1, int((end_dt - start_dt).total_seconds()))
            except Exception:
                duration = 30

            row_keys = row.keys() if hasattr(row, "keys") else []
            ex_completed = row["exercises_completed"]
            esc_created = row["escalation_created"]
            mem_saved = row["memory_saved"]
            graceful_hangup = (
                row["graceful_hangup"] if "graceful_hangup" in row_keys else 0
            )
            topic = (row["topic_discussed"] or "").strip()

            final_outcome = outcome
            if not final_outcome or final_outcome in ("in_progress", "failed"):
                # Success conditions:
                # 1. exercises_completed > 0
                # 2. escalation_created == 1
                # 3. memory_saved == 1
                # 4. graceful_hangup == 1 (agent called hang_up tool after goodbye)
                # 5. topic_discussed is a specific concept and duration >= 10s
                is_success = (
                    ex_completed > 0
                    or esc_created == 1
                    or mem_saved == 1
                    or graceful_hangup == 1
                    or (topic and topic != "General Practice" and duration >= 10)
                )

                if is_success:
                    final_outcome = "successful"
                    clean_reason = ""
                else:
                    final_outcome = "failed"
                    if not clean_reason:
                        clean_reason = (
                            "Caller disconnected before completing an exercise or topic"
                        )

            cursor.execute(
                """
                UPDATE call_logs SET
                    end_time = ?,
                    duration_seconds = ?,
                    outcome = ?,
                    failure_reason = ?,
                    updated_at = ?
                WHERE call_id = ?
                """,
                (now_iso, duration, final_outcome, clean_reason, now_iso, call_id),
            )
            logger.info(
                "Call end recorded for %s: outcome=%s duration=%ds",
                call_id,
                final_outcome,
                duration,
            )
            return {
                "call_id": call_id,
                "outcome": final_outcome,
                "duration_seconds": duration,
                "failure_reason": clean_reason,
            }
    finally:
        conn.close()


def get_analytics_summary(db_path: Optional[Path] = None) -> dict[str, Any]:
    """Retrieve full analytics summary for the Call Analytics Dashboard."""
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM call_logs WHERE outcome != 'in_progress' ORDER BY created_at DESC"
        )
        rows = [dict(r) for r in cursor.fetchall()]

        total_calls = len(rows)
        successful_calls = sum(1 for r in rows if r["outcome"] == "successful")
        failed_calls = sum(1 for r in rows if r["outcome"] == "failed")
        success_rate = (
            round((successful_calls / total_calls * 100), 1) if total_calls > 0 else 0.0
        )

        total_duration = sum(
            r["duration_seconds"] for r in rows if r.get("duration_seconds")
        )
        avg_duration = round(total_duration / total_calls) if total_calls > 0 else 0

        failure_breakdown: dict[str, int] = {}
        for r in rows:
            if r["outcome"] == "failed":
                reason = r.get("failure_reason") or "Caller ended call early"
                failure_breakdown[reason] = failure_breakdown.get(reason, 0) + 1

        channel_breakdown: dict[str, int] = {}
        for r in rows:
            ch = r.get("channel") or "Browser"
            channel_breakdown[ch] = channel_breakdown.get(ch, 0) + 1

        recent_calls = []
        for r in rows[:30]:
            recent_calls.append(
                {
                    "call_id": r["call_id"],
                    "user_id": r["user_id"],
                    "caller_name": r["caller_name"],
                    "channel": r["channel"],
                    "start_time": r["start_time"],
                    "end_time": r["end_time"],
                    "duration_seconds": r["duration_seconds"],
                    "outcome": r["outcome"],
                    "failure_reason": r["failure_reason"],
                    "exercises_completed": r["exercises_completed"],
                    "escalation_created": bool(r["escalation_created"]),
                    "memory_saved": bool(r["memory_saved"]),
                    "topic_discussed": r["topic_discussed"] or "General Practice",
                }
            )

        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": success_rate,
            "avg_duration_seconds": avg_duration,
            "failure_breakdown": failure_breakdown,
            "channel_breakdown": channel_breakdown,
            "recent_calls": recent_calls,
        }
    finally:
        conn.close()

