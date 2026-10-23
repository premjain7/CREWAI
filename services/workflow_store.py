"""Workflow store service for stateful multi-step interactions (e.g. Project 10 Approval Report)."""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from services.file_storage import BASE_OUTPUT_DIR

SESSIONS_DIR = BASE_OUTPUT_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class WorkflowStore:
    """Thread-safe store for multi-turn human-in-the-loop workflows.

    Note on persistence limitations:
    Active sessions are cached in memory for high performance and snapshotted
    to `outputs/sessions/<session_id>.json`. In cloud container environments
    (such as Render free tier without persistent disks), sessions may reset upon
    dyno restart or container redeployment.
    """

    _lock = threading.RLock()
    _sessions: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def create_session(
        cls,
        session_id: str,
        topic: str,
        audience: str = "General audience",
        research: str = "",
        draft: str = "",
        max_revisions: int = 2,
    ) -> Dict[str, Any]:
        """Initializes a new approval session."""
        now = datetime.now(timezone.utc).isoformat()
        session_data = {
            "session_id": session_id,
            "topic": topic,
            "audience": audience,
            "research": research,
            "draft": draft,
            "feedback": "",
            "decision": "pending",
            "status": "pending_review",
            "revision_count": 0,
            "max_revisions": max_revisions,
            "final_path": None,
            "audit_record_path": None,
            "created_at": now,
            "updated_at": now,
        }

        with cls._lock:
            cls._sessions[session_id] = session_data
            cls._persist_to_disk(session_id, session_data)

        return session_data

    @classmethod
    def get_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves session state from memory or disk snapshot."""
        with cls._lock:
            if session_id in cls._sessions:
                return cls._sessions[session_id]

            # Try loading from disk snapshot
            session_file = SESSIONS_DIR / f"{session_id}.json"
            if session_file.exists():
                try:
                    data = json.loads(session_file.read_text(encoding="utf-8"))
                    cls._sessions[session_id] = data
                    return data
                except Exception:
                    return None
            return None

    @classmethod
    def update_session(cls, session_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Applies updates to an existing session."""
        with cls._lock:
            session = cls.get_session(session_id)
            if not session:
                return None

            session.update(updates)
            session["updated_at"] = datetime.now(timezone.utc).isoformat()
            cls._sessions[session_id] = session
            cls._persist_to_disk(session_id, session)
            return session

    @classmethod
    def _persist_to_disk(cls, session_id: str, data: Dict[str, Any]):
        """Snapshots session state to JSON on disk."""
        try:
            target = SESSIONS_DIR / f"{session_id}.json"
            target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
