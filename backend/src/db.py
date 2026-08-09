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
        logger.info("Database initialized successfully at %s", db_path or DB_PATH)
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
