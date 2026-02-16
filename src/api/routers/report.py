import sqlite3
import logging
import json
from typing import List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel

from ..models import ReportCreate, ReportResponse, SuccessResponse
from ..dependencies import get_db
from ...report.report_generator import ReportGenerator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED
)
def generate_report(report: ReportCreate, conn: sqlite3.Connection = Depends(get_db)):
    try:
        import json

        manager = ReportGenerator(
            str(conn.execute("PRAGMA database_list").fetchone()[2])
        )

        if report.report_type == "daily":
            content_dict = manager.generate_daily_report()
            report_id = f"daily_{content_dict.get('date', 'unknown')}"
        elif report.report_type == "weekly":
            content_dict = manager.generate_weekly_report(
                start_date=report.start_date.isoformat()
                if report.start_date
                else datetime.now().strftime("%Y-%m-%d")
            )
            report_id = (
                f"weekly_{content_dict.get('period', {}).get('start', 'unknown')}"
            )
        elif report.report_type == "monthly":
            content_dict = manager.generate_monthly_report()
            report_id = (
                f"monthly_{content_dict.get('period', {}).get('start', 'unknown')}"
            )
        elif report.report_type == "custom":
            criteria = {}
            if report.start_date:
                criteria["start_date"] = report.start_date.isoformat()
            if report.end_date:
                criteria["end_date"] = report.end_date.isoformat()
            if report.agent_id:
                criteria["agent_id"] = report.agent_id
            content_dict = manager.generate_custom_report(criteria=criteria)
            report_id = (
                f"custom_{content_dict.get('period', {}).get('start', 'unknown')}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid report type: {report.report_type}",
            )

        return ReportResponse(
            id=report_id,
            report_type=report.report_type,
            start_date=report.start_date.isoformat() if report.start_date else "",
            end_date=report.end_date.isoformat() if report.end_date else "",
            content=json.dumps(content_dict, indent=2, ensure_ascii=False),
            created_at=conn.execute("SELECT datetime('now')").fetchone()[0],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/recent", response_model=List[ReportResponse])
def get_recent_reports(
    limit: int = Query(default=10, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        results = conn.execute(
            """
            SELECT * FROM reports
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [
            ReportResponse(
                id=row["id"],
                report_type=row["report_type"],
                start_date=row["start_date"] or "",
                end_date=row["end_date"] or "",
                content=row["content"],
                created_at=row["created_at"],
            )
            for row in results
        ]
    except Exception as e:
        logger.error(f"Error getting recent reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/statistics", response_model=dict)
def get_report_statistics(conn: sqlite3.Connection = Depends(get_db)):
    try:
        manager = ReportGenerator(
            str(conn.execute("PRAGMA database_list").fetchone()[2])
        )
        stats = manager.get_statistics()

        return {
            "total_memories": stats.get("total_memories", 0),
            "by_type": stats.get("by_type", {}),
            "by_category": stats.get("by_category", {}),
            "by_date": stats.get("by_date", {}),
            "total_score": stats.get("total_score", 0.0),
            "average_score": stats.get("average_score", 0.0),
        }
    except Exception as e:
        logger.error(f"Error getting report statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/daily", response_model=ReportResponse)
def generate_daily_report_endpoint(conn: sqlite3.Connection = Depends(get_db)):
    try:
        manager = ReportGenerator(
            str(conn.execute("PRAGMA database_list").fetchone()[2])
        )
        content_dict = manager.generate_daily_report()
        report_date = content_dict.get("date", datetime.now().strftime("%Y-%m-%d"))
        now = conn.execute("SELECT datetime('now')").fetchone()[0]

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reports (report_type, start_date, end_date, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "daily",
                report_date,
                report_date,
                json.dumps(content_dict, indent=2, ensure_ascii=False),
                now,
            ),
        )
        report_id = cursor.lastrowid
        conn.commit()

        return ReportResponse(
            id=report_id,
            report_type="daily",
            start_date=report_date,
            end_date=report_date,
            content=json.dumps(content_dict, indent=2, ensure_ascii=False),
            created_at=now,
        )
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/weekly", response_model=ReportResponse)
def generate_weekly_report_endpoint(conn: sqlite3.Connection = Depends(get_db)):
    try:
        manager = ReportGenerator(
            str(conn.execute("PRAGMA database_list").fetchone()[2])
        )
        start_date = datetime.now().strftime("%Y-%m-%d")
        content_dict = manager.generate_weekly_report(start_date=start_date)
        period = content_dict.get("period", {})
        report_start = period.get("start", start_date)
        report_end = period.get("end", start_date)
        now = conn.execute("SELECT datetime('now')").fetchone()[0]

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reports (report_type, start_date, end_date, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "weekly",
                report_start,
                report_end,
                json.dumps(content_dict, indent=2, ensure_ascii=False),
                now,
            ),
        )
        report_id = cursor.lastrowid
        conn.commit()

        return ReportResponse(
            id=report_id,
            report_type="weekly",
            start_date=report_start,
            end_date=report_end,
            content=json.dumps(content_dict, indent=2, ensure_ascii=False),
            created_at=now,
        )
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/monthly", response_model=ReportResponse)
def generate_monthly_report_endpoint(conn: sqlite3.Connection = Depends(get_db)):
    try:
        manager = ReportGenerator(
            str(conn.execute("PRAGMA database_list").fetchone()[2])
        )
        content_dict = manager.generate_monthly_report()
        period = content_dict.get("period", {})
        report_start = period.get("start", datetime.now().strftime("%Y-%m-01"))
        report_end = period.get("end", datetime.now().strftime("%Y-%m-28"))
        now = conn.execute("SELECT datetime('now')").fetchone()[0]

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reports (report_type, start_date, end_date, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "monthly",
                report_start,
                report_end,
                json.dumps(content_dict, indent=2, ensure_ascii=False),
                now,
            ),
        )
        report_id = cursor.lastrowid
        conn.commit()

        return ReportResponse(
            id=report_id,
            report_type="monthly",
            start_date=report_start,
            end_date=report_end,
            content=json.dumps(content_dict, indent=2, ensure_ascii=False),
            created_at=now,
        )
    except Exception as e:
        logger.error(f"Error generating monthly report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
