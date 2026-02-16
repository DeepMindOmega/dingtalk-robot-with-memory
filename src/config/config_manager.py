"""
Config Manager implementation
"""

import sqlite3
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages agent configuration with version control and hot updates.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize config manager.

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
        self._init_db()
        logger.info(f"ConfigManager initialized with db_path: {self.db_path}")

    def _init_db(self):
        """Initialize database tables if needed."""
        import os

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS config_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                config_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """
        )
        conn.commit()
        conn.close()

    def get_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get latest configuration for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Configuration dict or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT config_data FROM config_history
            WHERE agent_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (agent_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row["config_data"])
        return None

    def update_config(self, agent_id: str, config: Dict[str, Any]) -> int:
        """
        Update agent configuration (creates new version).

        Args:
            agent_id: Agent identifier
            config: Configuration dict

        Returns:
            Config history ID
        """
        now = datetime.now(timezone.utc).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO config_history (agent_id, config_data, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (agent_id, json.dumps(config), now, now),
        )

        config_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Updated config for agent {agent_id}: config_id={config_id}")
        return config_id

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration against rules.

        Args:
            config: Configuration dict to validate

        Returns:
            Validation result with valid flag and errors
        """
        errors = []
        warnings = []

        required_fields = ["agent_id", "model", "temperature", "max_tokens"]

        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        if "temperature" in config:
            temp = config["temperature"]
            if not (0.0 <= temp <= 2.0):
                errors.append(f"Temperature must be between 0.0 and 2.0, got: {temp}")

        if "max_tokens" in config:
            tokens = config["max_tokens"]
            if not (100 <= tokens <= 16000):
                errors.append(
                    f"Max tokens must be between 100 and 16000, got: {tokens}"
                )

        if "model" in config:
            model = config["model"]
            valid_models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"]
            if model not in valid_models:
                errors.append(f"Invalid model: {model}")

        valid = len(errors) == 0

        return {"valid": valid, "errors": errors, "warnings": warnings}

    def rollback_config(self, agent_id: str, version: int) -> bool:
        """
        Rollback to a specific configuration version.

        Args:
            agent_id: Agent identifier
            version: Config history ID to rollback to

        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT config_data, created_at FROM config_history
            WHERE id = ? AND agent_id = ?
            """,
            (version, agent_id),
        )

        row = cursor.fetchone()

        if not row:
            conn.close()
            logger.warning(
                f"Cannot rollback: config version {version} not found for agent {agent_id}"
            )
            return False

        old_config = dict(row)["config_data"]
        old_created_at = row["created_at"]

        now = datetime.now(timezone.utc).isoformat()

        cursor.execute(
            """
            INSERT INTO config_history (agent_id, config_data, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (agent_id, old_config, old_created_at, now),
        )

        conn.commit()
        conn.close()

        logger.info(f"Rolled back agent {agent_id} to version {version}")
        return True

    def get_config_history(
        self, agent_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get configuration history for an agent.

        Args:
            agent_id: Agent identifier
            limit: Maximum history entries to return

        Returns:
            List of config history dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, agent_id, config_data, created_at, updated_at
            FROM config_history
            WHERE agent_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (agent_id, limit),
        )

        results = cursor.fetchall()
        conn.close()

        history = []
        for row in results:
            history.append(
                {
                    "id": row["id"],
                    "agent_id": row["agent_id"],
                    "config": json.loads(row["config_data"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )

        return history

    def apply_config(self, agent_id: str, config: Dict[str, Any]) -> bool:
        """
        Apply configuration to agent (hot update without version control).

        Args:
            agent_id: Agent identifier
            config: Configuration to apply

        Returns:
            True if successful, False otherwise
        """
        now = datetime.now(timezone.utc).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE config_history
            SET config_data = ?, updated_at = ?
            WHERE id = (
                SELECT id FROM config_history
                WHERE agent_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
            )
            """,
            (json.dumps(config), now, agent_id),
        )

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if updated:
            logger.info(f"Applied config to agent {agent_id}")
        else:
            logger.warning(f"Failed to apply config to agent {agent_id}")

        return updated

    def get_all_configs(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all agent configurations.

        Returns:
            Dict mapping agent_id to list of configs
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT agent_id FROM config_history
            """
        )

        agent_ids = [row["agent_id"] for row in cursor.fetchall()]

        all_configs = {}
        for agent_id in agent_ids:
            cursor.execute(
                """
                SELECT config_data, updated_at FROM config_history
                WHERE agent_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (agent_id,),
            )

            row = cursor.fetchone()
            if row:
                all_configs[agent_id] = json.loads(row["config_data"])

        conn.close()

        return all_configs

    def delete_old_configs(self, days: int = 30) -> int:
        """
        Delete old configuration history entries.

        Args:
            days: Delete configs older than this many days

        Returns:
            Number of deleted entries
        """
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM config_history
            WHERE created_at < ?
            AND id NOT IN (
                SELECT id FROM (
                    SELECT id FROM config_history
                    WHERE agent_id = (
                        SELECT DISTINCT agent_id FROM config_history
                    )
                    ORDER BY updated_at DESC
                    LIMIT 1
                )
            )
            """,
            (cutoff_date,),
        )

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Deleted {deleted_count} old config entries")
        return deleted_count
