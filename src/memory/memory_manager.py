"""
Memory Manager implementation
"""

import sqlite3
import json
import os
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages memory storage, retrieval, scoring, deduplication, and cleanup.
    """

    def __init__(self, db_path: str = None, output_dir: str = None):
        """
        Initialize memory manager.

        Args:
            db_path: Path to SQLite database.
            output_dir: Directory for Markdown file storage.
        """
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__), "..", "data", "memory_system.db"
            )
            db_path = os.path.abspath(db_path)

        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "memories")
            output_dir = os.path.abspath(output_dir)

        self.db_path = db_path
        self.output_dir = output_dir

        os.makedirs(self.output_dir, exist_ok=True)
        for category in [
            "success_cases",
            "failure_lessons",
            "skill_growth",
            "user_preferences",
        ]:
            os.makedirs(os.path.join(self.output_dir, category), exist_ok=True)

        self._init_db()
        logger.info(f"MemoryManager initialized with db_path: {self.db_path}")

    def _init_db(self):
        """Initialize database tables if needed."""
        import os

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT,
                score REAL DEFAULT 0.0
            )
        """
        )
        conn.commit()
        conn.close()

    def store_long_term(
        self,
        memory_type: str,
        title: str,
        content: str,
        tags: List[str] = None,
        source: str = "manual",
        ttl_days: int = 30,
    ) -> int:
        """
        Store long-term memory as Markdown file and in database.

        Args:
            memory_type: Type of memory (success_case, failure_lesson, etc.)
            title: Memory title
            content: Memory content
            tags: List of tags
            source: Source of memory
            ttl_days: Time to live in days

        Returns:
            Memory ID
        """
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(days=ttl_days)).isoformat() if ttl_days else None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO memories (type, title, content, tags, source, created_at, updated_at, expires_at, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0)
            """,
            (
                memory_type,
                title,
                content,
                json.dumps(tags) if tags else None,
                source,
                now.isoformat(),
                now.isoformat(),
                expires_at,
            ),
        )

        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self._save_to_file(memory_id, memory_type, title, content, tags, source, now)

        logger.info(f"Stored long-term memory {memory_id}: {title}")
        return memory_id

    def store_short_term(self, content: str, context: Dict[str, Any] = None) -> int:
        """
        Store short-term memory in database only (no file).

        Args:
            content: Memory content
            context: Additional context data

        Returns:
            Memory ID
        """
        now = datetime.now(timezone.utc)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO memories (type, title, content, tags, source, created_at, updated_at, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0.0)
            """,
            (
                "short_term",
                "Short-term Memory",
                content,
                json.dumps(context) if context else None,
                "session",
                now.isoformat(),
                now.isoformat(),
            ),
        )

        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Stored short-term memory {memory_id}")
        return memory_id

    def store_context(
        self, context_data: Dict[str, Any], session_id: str = None
    ) -> int:
        """
        Store session context.

        Args:
            context_data: Context data dict
            session_id: Session identifier

        Returns:
            Memory ID
        """
        now = datetime.now(timezone.utc)
        title = f"Context: {session_id}" if session_id else "Session Context"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO memories (type, title, content, tags, source, created_at, updated_at, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0.0)
            """,
            (
                "context",
                title,
                json.dumps(context_data),
                json.dumps([session_id]) if session_id else None,
                "session",
                now.isoformat(),
                now.isoformat(),
            ),
        )

        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Stored context memory {memory_id}")
        return memory_id

    def retrieve(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            Memory dict or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()

        conn.close()

        return dict(row) if row else None

    def retrieve_by_type(
        self,
        memory_type: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories by type.

        Args:
            memory_type: Type of memory
            limit: Maximum memories to return

        Returns:
            List of memory dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM memories
            WHERE type = ? AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY score DESC, created_at DESC
            LIMIT ?
            """,
            (memory_type, datetime.now(timezone.utc).isoformat(), limit),
        )

        results = cursor.fetchall()
        conn.close()

        return [dict(row) for row in results]

    def search_keyword(
        self, query: str, memory_type: str = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search memories by keyword.

        Args:
            query: Search query
            memory_type: Filter by memory type
            limit: Maximum results

        Returns:
            List of memory dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query_sql = """
            SELECT * FROM memories
            WHERE (title LIKE ? OR content LIKE ? OR tags LIKE ?)
            AND (expires_at IS NULL OR expires_at > ?)
        """
        params = [
            f"%{query}%",
            f"%{query}%",
            f"%{query}%",
            datetime.now(timezone.utc).isoformat(),
        ]

        if memory_type:
            query_sql += " AND type = ?"
            params.append(memory_type)
        else:
            params = [p for p in params]

        query_sql += " ORDER BY score DESC, created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query_sql, params)
        results = cursor.fetchall()
        conn.close()

        return [dict(row) for row in results]

    def deduplicate(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate memories based on content similarity.

        Args:
            memories: List of memory dicts to deduplicate

        Returns:
            Deduplicated list of memory dicts
        """
        seen_contents = set()
        deduped = []

        for memory in memories:
            content = memory.get("content", "")
            content_normalized = re.sub(r"\s+", " ", content.lower()).strip()

            if content_normalized not in seen_contents:
                seen_contents.add(content_normalized)
                deduped.append(memory)

        removed_count = len(memories) - len(deduped)
        if removed_count > 0:
            logger.info(f"Deduplicated {removed_count} memories")

        return deduped

    def update_score(self, memory_id: int, delta: float) -> bool:
        """
        Update memory score.

        Args:
            memory_id: Memory ID
            delta: Score change (positive or negative)

        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE memories SET score = score + ?, updated_at = ? WHERE id = ?",
            (delta, datetime.now(timezone.utc).isoformat(), memory_id),
        )

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if updated:
            logger.info(f"Updated score for memory {memory_id}: +{delta}")

        return updated

    def cleanup_expired(self, days: int = 7) -> int:
        """
        Clean up expired memories.

        Args:
            days: Delete memories older than this many days

        Returns:
            Number of memories deleted
        """
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?",
            (cutoff_date,),
        )

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Cleaned up {deleted_count} expired memories")
        return deleted_count

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get memory statistics.

        Returns:
            Statistics dict
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM memories")
        total = cursor.fetchone()["count"]

        cursor.execute("SELECT type, COUNT(*) as count FROM memories GROUP BY type")
        type_counts = {row["type"]: row["count"] for row in cursor.fetchall()}

        cursor.execute("SELECT AVG(score) as avg_score FROM memories")
        avg_score = cursor.fetchone()["avg_score"] or 0.0

        cursor.execute(
            "SELECT COUNT(*) as count FROM memories WHERE expires_at IS NOT NULL"
        )
        expirable_count = cursor.fetchone()["count"]

        stats = {
            "total_memories": total,
            "by_type": type_counts,
            "average_score": round(avg_score, 2),
            "expirable_count": expirable_count,
        }

        conn.close()

        return stats

    def _save_to_file(
        self,
        memory_id: int,
        memory_type: str,
        title: str,
        content: str,
        tags: List[str],
        source: str,
        created_at: datetime,
    ):
        """Save memory to Markdown file."""
        safe_title = re.sub(r"[^\w\s-]", "", title).strip()
        safe_title = re.sub(r"[-\s]+", "_", safe_title)

        timestamp = created_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{safe_title}.md"

        category_dir = os.path.join(self.output_dir, f"{memory_type}s")
        os.makedirs(category_dir, exist_ok=True)
        file_path = os.path.join(category_dir, filename)

        file_content = f"# {title}\n\n"
        file_content += f"**Type**: {memory_type}\n"
        file_content += f"**Source**: {source}\n"
        file_content += f"**Created**: {created_at.isoformat()}\n"
        file_content += f"**ID**: {memory_id}\n\n"

        if tags:
            file_content += f"**Tags**: {', '.join(tags)}\n\n"

        file_content += "---\n\n"
        file_content += content

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content)
