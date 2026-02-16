"""
Agent Enhancer implementation
"""

import json
import logging
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AgentEnhancer:
    """
    Analyzes agent performance metrics and suggests configuration improvements.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize agent enhancer.

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
        logger.info(f"AgentEnhancer initialized with db_path: {self.db_path}")

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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                accuracy REAL DEFAULT 0.0,
                response_time REAL DEFAULT 0.0,
                tasks_completed INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL
            )
        """
        )
        conn.commit()
        conn.close()

    def analyze_performance(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Analyze agent performance based on metrics.

        Args:
            agent_id: Agent identifier

        Returns:
            Performance analysis dict or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT accuracy, response_time, tasks_completed, timestamp
            FROM agent_metrics
            WHERE agent_id = ?
            ORDER BY timestamp DESC
            LIMIT 100
        """,
            (agent_id,),
        )
        metrics = cursor.fetchall()
        conn.close()

        if not metrics:
            logger.warning(f"No metrics found for agent: {agent_id}")
            return None

        total_tasks = sum(m["tasks_completed"] for m in metrics)
        avg_accuracy = sum(m["accuracy"] for m in metrics) / len(metrics)
        avg_response_time = sum(m["response_time"] for m in metrics) / len(metrics)

        recent_accuracy = metrics[0]["accuracy"] if metrics else 0
        previous_accuracy = (
            metrics[-1]["accuracy"] if len(metrics) > 1 else recent_accuracy
        )
        accuracy_trend = recent_accuracy - previous_accuracy

        analysis = {
            "agent_id": agent_id,
            "total_tasks": total_tasks,
            "avg_accuracy": avg_accuracy,
            "avg_response_time": avg_response_time,
            "recent_accuracy": recent_accuracy,
            "accuracy_trend": accuracy_trend,
            "sample_size": len(metrics),
        }

        logger.info(f"Performance analysis for {agent_id}: {analysis}")
        return analysis

    def suggest_model_config(self, task_type: str) -> Dict[str, Any]:
        """
        Suggest optimal model configuration for a task type.

        Args:
            task_type: Type of task (e.g., "extraction", "analysis", "generation")

        Returns:
            Configuration suggestions dict
        """
        config_suggestions = {
            "extraction": {
                "model": "gpt-4o-mini",
                "temperature": 0.1,
                "max_tokens": 1000,
                "reasoning": "none",
            },
            "analysis": {
                "model": "gpt-4o-mini",
                "temperature": 0.3,
                "max_tokens": 2000,
                "reasoning": "low",
            },
            "generation": {
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 3000,
                "reasoning": "medium",
            },
        }

        suggestion = config_suggestions.get(task_type, config_suggestions["analysis"])
        logger.info(f"Model config suggestion for {task_type}: {suggestion}")
        return suggestion

    def optimize_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """
        Generate optimized prompt based on task and context.

        Args:
            task: Task description
            context: Additional context (user preferences, past experiences)

        Returns:
            Optimized prompt string
        """
        base_prompt = f"""You are an intelligent assistant helping with: {task}

Context:
{json.dumps(context, indent=2)}

Requirements:
1. Be concise and direct
2. Focus on the specific task at hand
3. Use the provided context effectively
4. If unsure, ask for clarification
"""

        optimized_prompt = self._apply_user_preferences(base_prompt, context)
        logger.info(f"Generated optimized prompt for task: {task[:50]}...")
        return optimized_prompt

    def _apply_user_preferences(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Apply user preferences to prompt.

        Args:
            prompt: Base prompt
            context: User context with preferences

        Returns:
            Modified prompt
        """
        preferences = context.get("user_preferences", {})

        if preferences.get("communication_style") == "terse":
            prompt += "\n\n5. Keep responses extremely brief and to the point"
        elif preferences.get("communication_style") == "detailed":
            prompt += "\n\n5. Provide comprehensive, detailed responses"

        if preferences.get("language") == "zh":
            prompt = prompt.replace("You are", "你是")
            prompt = prompt.replace("Context:", "上下文:")
            prompt = prompt.replace("Requirements:", "要求:")

        return prompt

    def update_agent_config(self, agent_id: str, config: Dict[str, Any]) -> bool:
        """
        Update agent configuration in database.

        Args:
            agent_id: Agent identifier
            config: New configuration dict

        Returns:
            True if successful, False otherwise
        """
        now = datetime.now(timezone.utc).isoformat()

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO config_history (agent_id, config_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (agent_id, json.dumps(config), now, now),
            )

            conn.commit()
            conn.close()

            logger.info(f"Updated config for agent {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update config for {agent_id}: {e}")
            return False

    def cost_optimization(self, usage_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide cost optimization suggestions based on usage statistics.

        Args:
            usage_stats: Dictionary with usage metrics

        Returns:
            Optimization suggestions dict
        """
        suggestions = []

        if usage_stats.get("avg_tokens_per_request", 0) > 2000:
            suggestions.append(
                {
                    "type": "reduce_tokens",
                    "message": "Average tokens per request is high. Consider summarizing or breaking down tasks.",
                    "potential_savings": "20-30%",
                }
            )

        if usage_stats.get("model_usage", {}).get("gpt-4o", 0) > 1000:
            suggestions.append(
                {
                    "type": "model_downgrade",
                    "message": "High usage of gpt-4o. Consider using gpt-4o-mini for routine tasks.",
                    "potential_savings": "50-70%",
                }
            )

        if usage_stats.get("cache_hit_rate", 0) < 0.5:
            suggestions.append(
                {
                    "type": "enable_caching",
                    "message": "Cache hit rate is low. Enable response caching for repeated queries.",
                    "potential_savings": "10-20%",
                }
            )

        optimization_report = {
            "usage_stats": usage_stats,
            "suggestions": suggestions,
            "priority": len(suggestions) > 2,
        }

        logger.info(f"Cost optimization report: {len(suggestions)} suggestions")
        return optimization_report

    def trigger_upgrade_check(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Trigger an automatic upgrade check for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Upgrade recommendations or None if no upgrade needed
        """
        analysis = self.analyze_performance(agent_id)

        if not analysis:
            return None

        recommendations = []

        if analysis["accuracy_trend"] < -0.1:
            recommendations.append(
                {
                    "type": "accuracy_decline",
                    "severity": "high",
                    "message": "Accuracy declining significantly. Review recent changes or model configuration.",
                    "action": "investigate_logs",
                }
            )

        if analysis["avg_response_time"] > 5.0:
            recommendations.append(
                {
                    "type": "slow_response",
                    "severity": "medium",
                    "message": "Average response time is high. Consider optimizing prompts or using faster models.",
                    "action": "optimize_config",
                }
            )

        if analysis["sample_size"] < 10:
            return None

        return {
            "agent_id": agent_id,
            "analysis": analysis,
            "recommendations": recommendations,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
