"""
Persistent SQLite Context Store.

Enforces deterministic versioning behavior:
1. First version  -> accept and store
2. Same version   -> idempotent no-op (accept without modifying)
3. Higher version -> atomically replace old version
4. Lower version  -> reject as stale
"""

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.config import DATABASE_PATH


class ContextStore:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize database schema with WAL mode and appropriate indexes."""
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS contexts (
                        scope TEXT NOT NULL CHECK(scope IN ('category', 'merchant', 'customer', 'trigger')),
                        context_id TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        payload TEXT NOT NULL,
                        delivered_at TEXT NOT NULL,
                        stored_at TEXT NOT NULL,
                        PRIMARY KEY (scope, context_id)
                    );
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_contexts_scope ON contexts(scope);
                """)
                # Migration safeguard: Verify suppressions has composite primary key
                cursor.execute("PRAGMA table_info(suppressions);")
                columns = cursor.fetchall()
                if columns:
                    pk_count = sum(1 for col in columns if col["pk"] > 0)
                    if pk_count < 2:
                        cursor.execute("DROP TABLE suppressions;")

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS suppressions (
                        suppression_key TEXT NOT NULL,
                        merchant_id TEXT NOT NULL,
                        trigger_id TEXT NOT NULL,
                        sent_at TEXT NOT NULL,
                        PRIMARY KEY (suppression_key, merchant_id)
                    );
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_suppressions_lookup ON suppressions(suppression_key, merchant_id);
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        conversation_id TEXT PRIMARY KEY,
                        merchant_id TEXT NOT NULL,
                        customer_id TEXT,
                        trigger_id TEXT,
                        suppression_key TEXT,
                        category_slug TEXT,
                        current_state TEXT NOT NULL,
                        current_turn INTEGER NOT NULL,
                        auto_reply_count INTEGER NOT NULL DEFAULT 0,
                        last_action TEXT,
                        last_body TEXT,
                        last_rationale TEXT,
                        last_cta TEXT,
                        last_wait_seconds INTEGER,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_merchant ON conversations(merchant_id);
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_turns (
                        conversation_id TEXT NOT NULL,
                        turn_number INTEGER NOT NULL,
                        from_role TEXT NOT NULL,
                        message TEXT NOT NULL,
                        intent TEXT,
                        state_after TEXT NOT NULL,
                        action TEXT NOT NULL,
                        body TEXT,
                        rationale TEXT NOT NULL,
                        cta TEXT,
                        wait_seconds INTEGER,
                        timestamp TEXT NOT NULL,
                        PRIMARY KEY (conversation_id, turn_number)
                    );
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_turns_lookup ON conversation_turns(conversation_id, turn_number);
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS debug_traces (
                        trace_id TEXT PRIMARY KEY,
                        request_type TEXT NOT NULL,
                        merchant_id TEXT,
                        trigger_id TEXT,
                        conversation_id TEXT,
                        timestamp TEXT NOT NULL,
                        trace_payload TEXT NOT NULL
                    );
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_debug_traces_timestamp ON debug_traces(timestamp);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_debug_traces_req ON debug_traces(request_type, merchant_id);
                """)
                conn.commit()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def save_context(
        self,
        scope: str,
        context_id: str,
        version: int,
        payload: Dict[str, Any],
        delivered_at: str,
    ) -> Tuple[bool, int, str]:
        """
        Save or update context payload with version checking.

        Returns:
            Tuple of (accepted: bool, current_version: int, stored_at: str)
            - (True, version, stored_at) if inserted or updated or duplicate no-op
            - (False, current_version, stored_at) if stale version (lower version)
        """
        payload_json = json.dumps(payload, ensure_ascii=False)

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT version, stored_at FROM contexts WHERE scope = ? AND context_id = ?",
                    (scope, context_id),
                )
                row = cursor.fetchone()

                if row is None:
                    # First version -> Insert
                    stored_at = self._now_iso()
                    cursor.execute(
                        """
                        INSERT INTO contexts (scope, context_id, version, payload, delivered_at, stored_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (scope, context_id, version, payload_json, delivered_at, stored_at),
                    )
                    conn.commit()
                    return True, version, stored_at

                current_version = int(row["version"])
                existing_stored_at = str(row["stored_at"])

                if version == current_version:
                    # Duplicate version -> Idempotent no-op
                    return True, current_version, existing_stored_at

                if version > current_version:
                    # Higher version -> Atomically replace
                    stored_at = self._now_iso()
                    cursor.execute(
                        """
                        UPDATE contexts
                        SET version = ?, payload = ?, delivered_at = ?, stored_at = ?
                        WHERE scope = ? AND context_id = ?
                        """,
                        (version, payload_json, delivered_at, stored_at, scope, context_id),
                    )
                    conn.commit()
                    return True, version, stored_at

                # Stale version (version < current_version) -> Reject
                return False, current_version, existing_stored_at

    def get_context(self, scope: str, context_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single context entity by scope and context_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT scope, context_id, version, payload, delivered_at, stored_at FROM contexts WHERE scope = ? AND context_id = ?",
                (scope, context_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "scope": row["scope"],
                "context_id": row["context_id"],
                "version": row["version"],
                "payload": json.loads(row["payload"]),
                "delivered_at": row["delivered_at"],
                "stored_at": row["stored_at"],
            }

    def list_contexts_by_scope(self, scope: str) -> List[Dict[str, Any]]:
        """List all contexts belonging to a specific scope."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT scope, context_id, version, payload, delivered_at, stored_at FROM contexts WHERE scope = ? ORDER BY context_id",
                (scope,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "scope": r["scope"],
                    "context_id": r["context_id"],
                    "version": r["version"],
                    "payload": json.loads(r["payload"]),
                    "delivered_at": r["delivered_at"],
                    "stored_at": r["stored_at"],
                }
                for r in rows
            ]

    def get_counts(self) -> Dict[str, int]:
        """Return counts of loaded contexts for each of the four scopes."""
        counts = {
            "category": 0,
            "merchant": 0,
            "customer": 0,
            "trigger": 0,
        }
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT scope, COUNT(*) as count FROM contexts GROUP BY scope")
            for row in cursor.fetchall():
                scope_name = row["scope"]
                if scope_name in counts:
                    counts[scope_name] = int(row["count"])
        return counts

    def is_suppressed(self, suppression_key: str, merchant_id: str) -> bool:
        """Check if a message with this suppression_key has already been recorded for this specific merchant."""
        if not suppression_key or not merchant_id:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM suppressions WHERE suppression_key = ? AND merchant_id = ?",
                (suppression_key, merchant_id),
            )
            return cursor.fetchone() is not None

    def record_suppression(
        self,
        suppression_key: str,
        merchant_id: str,
        trigger_id: str,
        sent_at: Optional[str] = None,
    ) -> None:
        """Record a sent message's suppression_key for a specific merchant."""
        if not suppression_key or not merchant_id:
            return
        ts = sent_at or self._now_iso()
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO suppressions (suppression_key, merchant_id, trigger_id, sent_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (suppression_key, merchant_id, trigger_id, ts),
                )
                conn.commit()

    def save_conversation(
        self,
        conversation_id: str,
        merchant_id: str,
        customer_id: Optional[str] = None,
        trigger_id: Optional[str] = None,
        suppression_key: Optional[str] = None,
        category_slug: Optional[str] = None,
        current_state: str = "AWAITING_REPLY",
        current_turn: int = 1,
        auto_reply_count: int = 0,
        last_action: Optional[str] = None,
        last_body: Optional[str] = None,
        last_rationale: Optional[str] = None,
        last_cta: Optional[str] = None,
        last_wait_seconds: Optional[int] = None,
        created_at: Optional[str] = None,
    ) -> None:
        """Create or update conversation state atomically."""
        now = self._now_iso()
        ts_created = created_at or now
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO conversations (
                        conversation_id, merchant_id, customer_id, trigger_id,
                        suppression_key, category_slug, current_state, current_turn,
                        auto_reply_count, last_action, last_body, last_rationale,
                        last_cta, last_wait_seconds, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(conversation_id) DO UPDATE SET
                        current_state = excluded.current_state,
                        current_turn = excluded.current_turn,
                        auto_reply_count = excluded.auto_reply_count,
                        last_action = excluded.last_action,
                        last_body = excluded.last_body,
                        last_rationale = excluded.last_rationale,
                        last_cta = excluded.last_cta,
                        last_wait_seconds = excluded.last_wait_seconds,
                        updated_at = excluded.updated_at
                    """,
                    (
                        conversation_id, merchant_id, customer_id, trigger_id,
                        suppression_key, category_slug, current_state, current_turn,
                        auto_reply_count, last_action, last_body, last_rationale,
                        last_cta, last_wait_seconds, ts_created, now
                    ),
                )
                conn.commit()

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve conversation record by conversation_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT conversation_id, merchant_id, customer_id, trigger_id,
                       suppression_key, category_slug, current_state, current_turn,
                       auto_reply_count, last_action, last_body, last_rationale,
                       last_cta, last_wait_seconds, created_at, updated_at
                FROM conversations WHERE conversation_id = ?
                """,
                (conversation_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def record_turn(
        self,
        conversation_id: str,
        turn_number: int,
        from_role: str,
        message: str,
        intent: Optional[str],
        state_after: str,
        action: str,
        body: Optional[str],
        rationale: str,
        cta: Optional[str] = None,
        wait_seconds: Optional[int] = None,
        timestamp: Optional[str] = None,
    ) -> None:
        """Record a single turn in the conversation_turns table."""
        ts = timestamp or self._now_iso()
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO conversation_turns (
                        conversation_id, turn_number, from_role, message, intent,
                        state_after, action, body, rationale, cta, wait_seconds, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        conversation_id, turn_number, from_role, message, intent,
                        state_after, action, body, rationale, cta, wait_seconds, ts
                    ),
                )
                conn.commit()

    def get_turn(self, conversation_id: str, turn_number: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific turn for idempotency and replay checks."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT conversation_id, turn_number, from_role, message, intent,
                       state_after, action, body, rationale, cta, wait_seconds, timestamp
                FROM conversation_turns
                WHERE conversation_id = ? AND turn_number = ?
                """,
                (conversation_id, turn_number),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def save_trace(self, trace: Any) -> None:
        """Persist a PipelineDecisionTrace safely in debug_traces table."""
        trace_dict = trace.model_dump() if hasattr(trace, "model_dump") else dict(trace)
        trace_json = json.dumps(trace_dict, ensure_ascii=False)
        ts = trace_dict.get("timestamp") or self._now_iso()

        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO debug_traces (
                        trace_id, request_type, merchant_id, trigger_id, conversation_id, timestamp, trace_payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trace_dict.get("trace_id"),
                        trace_dict.get("request_type"),
                        trace_dict.get("merchant_id"),
                        trace_dict.get("trigger_id"),
                        trace_dict.get("conversation_id"),
                        ts,
                        trace_json,
                    ),
                )
                conn.commit()

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stored PipelineDecisionTrace by trace_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT trace_payload FROM debug_traces WHERE trace_id = ?",
                (trace_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            try:
                return json.loads(row["trace_payload"])
            except Exception:
                return None

    def list_traces(
        self,
        request_type: Optional[str] = None,
        merchant_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List stored debug traces ordered by newest first."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT trace_payload FROM debug_traces"
            params: List[Any] = []
            conditions: List[str] = []

            if request_type:
                conditions.append("request_type = ?")
                params.append(request_type)
            if merchant_id:
                conditions.append("merchant_id = ?")
                params.append(merchant_id)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            traces = []
            for r in rows:
                try:
                    traces.append(json.loads(r["trace_payload"]))
                except Exception:
                    continue
            return traces

    def clear(self) -> None:
        """Clear all stored contexts, suppressions, conversations, turns, and debug traces."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM contexts")
                conn.execute("DELETE FROM suppressions")
                conn.execute("DELETE FROM conversations")
                conn.execute("DELETE FROM conversation_turns")
                conn.execute("DELETE FROM debug_traces")
                conn.commit()


# Global Singleton Store Instance
_store_instance: Optional[ContextStore] = None
_store_lock = threading.Lock()


def get_context_store() -> ContextStore:
    global _store_instance
    if _store_instance is None:
        with _store_lock:
            if _store_instance is None:
                _store_instance = ContextStore()
    return _store_instance

