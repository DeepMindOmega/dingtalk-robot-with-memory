"""
Report Generator implementation
"""

import sqlite3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates daily, weekly, monthly, and custom reports.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize report generator.

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
        logger.info(f"ReportGenerator initialized with db_path: {self.db_path}")

    def generate_daily_report(self, date: str = None) -> Dict[str, Any]:
        """
        Generate daily report.

        Args:
            date: Date in YYYY-MM-DD format. If None, uses today.

        Returns:
            Daily report dict
        """
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        start_date = f"{date} 00:00:00"
        end_date = f"{date} 23:59:59"

        report = {
            "type": "daily",
            "date": date,
            "period": {
                "start": start_date,
                "end": end_date,
            },
            "summary": self._get_period_summary(start_date, end_date),
            "details": self._get_period_details(start_date, end_date),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Generated daily report for {date}")
        return report

    def generate_weekly_report(
        self, start_date: str, end_date: str = None
    ) -> Dict[str, Any]:
        """
        Generate weekly report.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format. If None, uses end of this week.

        Returns:
            Weekly report dict
        """
        if end_date is None:
            dt = datetime.now(timezone.utc)
            end_date = dt.strftime("%Y-%m-%d")

        report = {
            "type": "weekly",
            "period": {
                "start": start_date,
                "end": end_date,
            },
            "summary": self._get_period_summary(start_date, end_date),
            "details": self._get_period_details(start_date, end_date),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Generated weekly report for {start_date} to {end_date}")
        return report

    def generate_monthly_report(self, month: str = None) -> Dict[str, Any]:
        """
        Generate monthly report.

        Args:
            month: Month in YYYY-MM format. If None, uses current month.

        Returns:
            Monthly report dict
        """
        if month is None:
            month = datetime.now(timezone.utc).strftime("%Y-%m")

        year, month_num = month.split("-")
        if len(year) == 4:
            if month_num == "12":
                start_date = f"{year}-12-01"
                end_date = f"{year}-12-31"
            else:
                next_month = int(month_num) + 1
                next_month_str = f"{year}-{next_month:02d}"
                start_date = f"{month}-01"
                end_date = f"{year}-{next_month_str}-01"
        else:
            start_date = f"{month}-01"
            end_date = f"{month}-31"

        report = {
            "type": "monthly",
            "period": {
                "start": start_date,
                "end": end_date,
            },
            "summary": self._get_period_summary(start_date, end_date),
            "details": self._get_period_details(start_date, end_date),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Generated monthly report for {month}")
        return report

    def generate_custom_report(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate custom report based on criteria.

        Args:
            criteria: Report criteria dict with filters:
                - type: daily, weekly, monthly
                - start_date: YYYY-MM-DD
                - end_date: YYYY-MM-DD
                - agent_id: Filter by agent ID
                - memory_type: Filter by memory type

        Returns:
            Custom report dict
        """
        report_type = criteria.get("type", "daily")
        start_date = criteria.get(
            "start_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )

        if "end_date" in criteria:
            end_date = criteria["end_date"]
        elif report_type == "daily":
            end_date = start_date
        elif report_type == "weekly":
            dt = datetime.fromisoformat(start_date, timezone.utc)
            end_date = (dt + timedelta(days=7)).strftime("%Y-%m-%d")
        elif report_type == "monthly":
            dt = datetime.fromisoformat(start_date, timezone.utc)
            if dt.month == 12:
                end_date = f"{dt.year}-12-31"
            else:
                next_month = dt.month + 1
                end_date = f"{dt.year}-{next_month:02d}-01"

        report = {
            "type": "custom",
            "criteria": criteria,
            "period": {
                "start": start_date,
                "end": end_date,
            },
            "summary": self._get_period_summary(start_date, end_date),
            "details": self._get_period_details(start_date, end_date, criteria),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Generated custom report: {report_type} from {start_date}")
        return report

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics for reports.

        Returns:
            Statistics dict
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM memories")
        total_memories = cursor.fetchone()["count"]

        cursor.execute("SELECT type, COUNT(*) as count FROM memories GROUP BY type")
        by_type = {row["type"]: row["count"] for row in cursor.fetchall()}

        cursor.execute("SELECT source, COUNT(*) as count FROM memories GROUP BY source")
        by_source = {row["source"]: row["count"] for row in cursor.fetchall()}

        cursor.execute("SELECT AVG(score) as avg_score FROM memories")
        avg_score = cursor.fetchone()["avg_score"] or 0.0

        cursor.execute("SELECT COUNT(DISTINCT agent_id) as count FROM config_history")
        total_agents = cursor.fetchone()["count"]

        conn.close()

        stats = {
            "total_memories": total_memories,
            "by_type": by_type,
            "by_source": by_source,
            "average_score": round(avg_score, 2),
            "total_agents": total_agents,
        }

        logger.info(f"Generated statistics: {stats}")
        return stats

    def save_report(self, report: Dict[str, Any], output_dir: str = None) -> str:
        """
        Save report to file.

        Args:
            report: Report dict
            output_dir: Directory to save report. If None, uses default.

        Returns:
            Path to saved report file
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
            output_dir = os.path.abspath(output_dir)

        import os

        os.makedirs(output_dir, exist_ok=True)

        report_type = report["type"]
        date_str = report.get("date", datetime.now(timezone.utc).strftime("%Y%m%d"))
        filename = f"{report_type}_{date_str}.md"
        file_path = os.path.join(output_dir, filename)

        content = f"# {report_type.upper()} Report\n\n"
        content += f"**Date**: {report.get('date', 'N/A')}\n\n"

        period = report.get("period", {})
        content += f"**Period**: {period.get('start', 'N/A')} to {period.get('end', 'N/A')}\n\n"

        summary = report.get("summary", {})
        content += f"## Summary\n\n"

        for key, value in summary.items():
            content += f"- {key}: {value}\n"

        content += "\n## Details\n\n"

        details = report.get("details", [])

        for category, items in details.items():
            content += f"### {category}\n\n"
            for item in items:
                if isinstance(item, dict):
                    content += (
                        f"- {item.get('name', 'Unknown')}: {item.get('value', 'N/A')}\n"
                    )
                else:
                    content += f"- {item}\n"

        content += f"\n**Generated**: {report.get('generated_at', 'N/A')}\n"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Saved report: {file_path}")
        return file_path

    def _get_period_summary(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get period summary statistics."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) as count,
                   SUM(CASE WHEN type = 'success_case' THEN 1 ELSE 0 END) as success_count,
                   SUM(CASE WHEN type = 'failure_lesson' THEN 1 ELSE 0 END) as failure_count
            FROM memories
            WHERE created_at >= ? AND created_at < ?
            """,
            (start_date, end_date),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "total_memories": row["count"],
                "success_cases": row["success_count"],
                "failure_lessons": row["failure_count"],
                "extraction_rate": round(row["success_count"] / row["count"] * 100, 2)
                if row["count"] > 0
                else 0,
            }

        return {
            "total": 0,
            "success_cases": 0,
            "failure_lessons": 0,
            "extraction_rate": 0.0,
        }

    def _get_period_details(
        self, start_date: str, end_date: str, criteria: Dict[str, Any] = None
    ) -> Dict[str, List[Any]]:
        """Get detailed breakdown by category and agent."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query_sql = """
            SELECT type, COUNT(*) as count, AVG(score) as avg_score
            FROM memories
            WHERE created_at >= ? AND created_at < ?
        """

        params = [start_date, end_date]

        if criteria and "agent_id" in criteria:
            query_sql += " AND source = ?"
            params.append(criteria["agent_id"])

        if criteria and "memory_type" in criteria:
            query_sql += " AND type = ?"
            params.append(criteria["memory_type"])

        query_sql += " GROUP BY type ORDER BY count DESC"

        cursor.execute(query_sql, params)
        rows = cursor.fetchall()
        conn.close()

        details = {}

        for row in rows:
            mem_type = row["type"]
            if mem_type not in details:
                details[mem_type] = []

            details[mem_type].append(
                {
                    "name": mem_type,
                    "value": f"{row['count']} memories (avg score: {row['avg_score']:.2f})",
                }
            )

        return details

    def get_recent_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent generated reports.

        Args:
            limit: Maximum reports to return

        Returns:
            List of report summaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT report_type as type, start_date, end_date, created_at as generated_at
            FROM reports
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            ((datetime.now(timezone.utc) - timedelta(days=7)).isoformat(), limit),
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]
