"""
Query Engine implementation
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Multi-dimensional query engine with semantic, keyword, and hybrid search.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize query engine.

        Args:
            db_path: Path to SQLite database.
        """
        if db_path is None:
            import os

            db_path = os.path.join(
                os.path.dirname(__file__), "..", "data", "memory_system.db"
            )
            db_path = os.path.abspath(db_path)

        self.db_path = db_path
        logger.info(f"QueryEngine initialized with db_path: {self.db_path}")

    def search(
        self,
        query: str,
        search_type: str = "hybrid",
        memory_type: str = None,
        source: str = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search memories with specified criteria.

        Args:
            query: Search query string
            search_type: Search type ('semantic', 'keyword', 'hybrid')
            memory_type: Filter by memory type
            source: Filter by source
            limit: Maximum results to return

        Returns:
            List of memory dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query_sql = "SELECT * FROM memories WHERE 1=1"
        params = []

        if memory_type:
            query_sql += " AND type = ?"
            params.append(memory_type)

        if source:
            query_sql += " AND source = ?"
            params.append(source)

        if search_type == "keyword":
            results = self._search_keyword(cursor, query_sql, query, params, limit)
        elif search_type == "semantic":
            results = self._search_semantic(cursor, query_sql, query, params, limit)
        else:
            results = self._search_hybrid(cursor, query_sql, query, params, limit)

        conn.close()

        return [dict(row) for row in results]

    def _search_keyword(
        self,
        cursor: sqlite3.Cursor,
        query_sql: str,
        query: str,
        params: List,
        limit: int,
    ) -> List[sqlite3.Row]:
        """Keyword search implementation."""
        search_sql = query_sql + " AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)"
        search_params = params + [f"%{query}%", f"%{query}%", f"%{query}%"]

        search_sql += " ORDER BY score DESC, created_at DESC LIMIT ?"
        search_params.append(limit)

        cursor.execute(search_sql, search_params)
        return cursor.fetchall()

    def _search_semantic(
        self,
        cursor: sqlite3.Cursor,
        query_sql: str,
        query: str,
        params: List,
        limit: int,
    ) -> List[sqlite3.Row]:
        """Semantic search implementation (simplified for MVP without embeddings)."""
        logger.warning(
            "Semantic search not fully implemented without embeddings. Falling back to keyword search."
        )
        return self._search_keyword(cursor, query_sql, query, params, limit)

    def _search_hybrid(
        self,
        cursor: sqlite3.Cursor,
        query_sql: str,
        query: str,
        params: List,
        limit: int,
    ) -> List[sqlite3.Row]:
        """Hybrid search combining keyword and scoring."""
        search_sql = query_sql + " AND (title LIKE ? OR content LIKE ?)"
        search_params = params + [f"%{query}%", f"%{query}%"]

        search_sql += " ORDER BY score DESC, created_at DESC LIMIT ?"
        search_params.append(limit)

        cursor.execute(search_sql, search_params)
        return cursor.fetchall()

    def retrieve_context(self, query_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve context for a specific query.

        Args:
            query_id: Query/memory ID

        Returns:
            Memory dict or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM memories WHERE id = ?", (query_id,))
        row = cursor.fetchone()

        conn.close()

        return dict(row) if row else None

    def rank_results(
        self,
        results: List[Dict[str, Any]],
        query: str,
    ) -> List[Dict[str, Any]]:
        """
        Rank and sort search results.

        Args:
            results: List of memory dicts
            query: Original query string

        Returns:
            Sorted list of memory dicts
        """
        query_lower = query.lower()

        for result in results:
            score = result.get("score", 0.0)

            title = result.get("title", "").lower()
            content = result.get("content", "").lower()

            title_match = query_lower in title
            content_match = query_lower in content

            if title_match:
                score += 0.3
            if content_match:
                score += 0.2

            result["relevance_score"] = score

        return sorted(
            results, key=lambda x: x.get("relevance_score", 0.0), reverse=True
        )

    def get_related_memories(
        self,
        memory_id: int,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get related memories based on ID.

        Args:
            memory_id: Reference memory ID
            limit: Maximum related memories to return

        Returns:
            List of related memory dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        reference_memory = cursor.fetchone()

        if not reference_memory:
            conn.close()
            return []

        ref_type = reference_memory["type"]
        ref_tags = dict(reference_memory).get("tags", "")

        cursor.execute(
            """
            SELECT * FROM memories
            WHERE id != ? AND type = ?
            ORDER BY score DESC, created_at DESC
            LIMIT ?
            """,
            (memory_id, ref_type, limit),
        )

        results = cursor.fetchall()
        conn.close()

        return [dict(row) for row in results]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics.

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

        cursor.execute("SELECT source, COUNT(*) as count FROM memories GROUP BY source")
        source_counts = {row["source"]: row["count"] for row in cursor.fetchall()}

        cursor.execute("SELECT AVG(score) as avg_score FROM memories")
        avg_score = cursor.fetchone()["avg_score"] or 0.0

        stats = {
            "total_memories": total,
            "by_type": type_counts,
            "by_source": source_counts,
            "average_score": round(avg_score, 2),
        }

        conn.close()

        return stats

    def get_recent_memories(
        self,
        memory_type: str = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get recent memories.

        Args:
            memory_type: Filter by memory type
            limit: Maximum memories to return

        Returns:
            List of recent memory dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query_sql = "SELECT * FROM memories"
        params = []

        if memory_type:
            query_sql += " WHERE type = ?"
            params.append(memory_type)

        query_sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query_sql, params)
        results = cursor.fetchall()
        conn.close()

        return [dict(row) for row in results]
