import sqlite3
import logging
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel

from ..models import (
    DashboardStatsResponse,
    TrendResponse,
    ChartDataPoint,
    MemoryResponse,
    ReportResponse,
)
from ..dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/overview", response_model=DashboardStatsResponse)
def get_dashboard_overview(
    limit: int = Query(default=5, ge=1, le=20),
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        total_memories = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        total_configs = conn.execute(
            "SELECT COUNT(DISTINCT agent_id) FROM config_history"
        ).fetchone()[0]
        total_reports = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        active_tasks = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'pending'"
        ).fetchone()[0]

        memory_type_distribution = {}
        type_results = conn.execute(
            "SELECT type, COUNT(*) as count FROM memories GROUP BY type"
        ).fetchall()
        for row in type_results:
            memory_type_distribution[row["type"]] = row["count"]

        memory_category_distribution = {}

        recent_memories = conn.execute(
            "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()

        recent_reports = conn.execute(
            "SELECT * FROM reports ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()

        return DashboardStatsResponse(
            total_memories=total_memories,
            total_configs=total_configs,
            total_reports=total_reports,
            active_tasks=active_tasks,
            memory_type_distribution=memory_type_distribution,
            memory_category_distribution=memory_category_distribution,
            recent_memories=[dict(row) for row in recent_memories],
            recent_reports=[
                ReportResponse(
                    id=row["id"],
                    report_type=row["report_type"] or "custom",
                    start_date=row["start_date"] or "",
                    end_date=row["end_date"] or "",
                    content=row["content"],
                    created_at=row["created_at"],
                )
                for row in recent_reports
            ],
        )
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/trends/memories/daily", response_model=TrendResponse)
def get_daily_memory_trend(
    days: int = Query(default=30, ge=1, le=365),
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        query = """
            SELECT date(created_at) as date, COUNT(*) as count
            FROM memories
            WHERE created_at >= date('now', ?)
            GROUP BY date(created_at)
            ORDER BY date
        """

        results = conn.execute(query, (f"-{days} days",)).fetchall()

        data = [
            ChartDataPoint(label=row["date"], value=row["count"]) for row in results
        ]

        total = sum(row["count"] for row in results)

        return TrendResponse(period="daily", data=data, total=total)
    except Exception as e:
        logger.error(f"Error getting daily memory trend: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/trends/memories/weekly", response_model=TrendResponse)
def get_weekly_memory_trend(
    weeks: int = Query(default=12, ge=1, le=52),
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        query = """
            SELECT strftime('%Y-W%W', created_at) as week, COUNT(*) as count
            FROM memories
            WHERE created_at >= date('now', ?)
            GROUP BY week
            ORDER BY week
        """

        results = conn.execute(query, (f"-{weeks * 7} days",)).fetchall()

        data = [
            ChartDataPoint(label=row["week"], value=row["count"]) for row in results
        ]

        total = sum(row["count"] for row in results)

        return TrendResponse(period="weekly", data=data, total=total)
    except Exception as e:
        logger.error(f"Error getting weekly memory trend: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/trends/memories/monthly", response_model=TrendResponse)
def get_monthly_memory_trend(
    months: int = Query(default=12, ge=1, le=60),
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        query = """
            SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
            FROM memories
            WHERE created_at >= date('now', ?)
            GROUP BY month
            ORDER BY month
        """

        results = conn.execute(query, (f"-{months} months",)).fetchall()

        data = [
            ChartDataPoint(label=row["month"], value=row["count"]) for row in results
        ]

        total = sum(row["count"] for row in results)

        return TrendResponse(period="monthly", data=data, total=total)
    except Exception as e:
        logger.error(f"Error getting monthly memory trend: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/trends/scores", response_model=TrendResponse)
def get_score_trend(
    period: str = Query(default="weekly", regex="^(daily|weekly|monthly)$"),
    days: int = Query(default=30, ge=1, le=365),
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        if period == "daily":
            date_format = "date(created_at)"
            interval = f"-{days} days"
        elif period == "weekly":
            date_format = "strftime('%Y-W%W', created_at)"
            interval = f"-{days} days"
        else:
            date_format = "strftime('%Y-%m', created_at)"
            interval = f"-{(days // 30)} months"

        query = f"""
            SELECT {date_format} as label, AVG(score) as value
            FROM memories
            WHERE created_at >= date('now', ?) AND score IS NOT NULL
            GROUP BY label
            ORDER BY label
        """

        results = conn.execute(query, (interval,)).fetchall()

        data = [
            ChartDataPoint(label=row["label"], value=round(row["value"], 2))
            for row in results
        ]

        avg_score = (
            sum(row["value"] for row in results) / len(results) if results else 0.0
        )

        return TrendResponse(period=period, data=data, total=round(avg_score, 2))
    except Exception as e:
        logger.error(f"Error getting score trend: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/top/categories", response_model=list[ChartDataPoint])
def get_top_categories(
    limit: int = Query(default=10, ge=1, le=50),
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        return []
    except Exception as e:
        logger.error(f"Error getting top categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/top/types", response_model=list[ChartDataPoint])
def get_top_types(
    limit: int = Query(default=10, ge=1, le=50),
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        query = """
            SELECT type, COUNT(*) as count
            FROM memories
            GROUP BY type
            ORDER BY count DESC
            LIMIT ?
        """

        results = conn.execute(query, (limit,)).fetchall()

        return [
            ChartDataPoint(label=row["type"], value=row["count"]) for row in results
        ]
    except Exception as e:
        logger.error(f"Error getting top types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
