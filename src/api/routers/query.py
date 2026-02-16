import sqlite3
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel

from ..models import (
    MemoryResponse,
    MemorySearchRequest,
    SearchResponse,
    MemoryStatsResponse,
    MemoryType,
)
from ..dependencies import get_db, get_db_path
from ...query.query_engine import QueryEngine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search_memories(
    request: MemorySearchRequest, conn: sqlite3.Connection = Depends(get_db)
):
    try:
        manager = QueryEngine(str(get_db_path()))

        search_type = "hybrid" if request.hybrid else "keyword"
        results = manager.search(
            query=request.keyword or "",
            search_type=search_type,
            memory_type=request.type.value if request.type else None,
            limit=request.limit,
        )

        total = len(results) if request.offset == 0 else 0

        total_query = "SELECT COUNT(*) FROM memories WHERE 1=1"
        params = []
        if request.type:
            total_query += " AND type = ?"
            params.append(request.type.value)

        if params:
            total = conn.execute(total_query, params).fetchone()[0]

        return SearchResponse(
            results=[dict(r) for r in results],
            total=total,
            limit=request.limit,
            offset=request.offset,
        )
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/related/{memory_type}", response_model=List[MemoryResponse])
def get_related_memories(
    memory_type: str,
    limit: int = Query(default=10, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        manager = QueryEngine(str(get_db_path()))
        results = manager.get_related_memories(memory_type=memory_type, limit=limit)

        return [dict(r) for r in results]
    except Exception as e:
        logger.error(f"Error getting related memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/recent", response_model=List[MemoryResponse])
def get_recent_memories(
    limit: int = Query(default=10, ge=1, le=100),
    memory_type: MemoryType = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        manager = QueryEngine(str(get_db_path()))
        results = manager.get_recent_memories(
            limit=limit, memory_type=memory_type.value if memory_type else None
        )

        return [dict(r) for r in results]
    except Exception as e:
        logger.error(f"Error getting recent memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/statistics", response_model=MemoryStatsResponse)
def get_statistics(conn: sqlite3.Connection = Depends(get_db)):
    try:
        manager = QueryEngine(str(get_db_path()))
        stats = manager.get_statistics()

        recent_query = "SELECT COUNT(*) FROM memories WHERE created_at > datetime('now', '-7 days')"
        recent_count = conn.execute(recent_query).fetchone()[0]

        return MemoryStatsResponse(
            total=stats["total_memories"],
            by_type=stats["by_type"],
            by_category={},
            average_score=stats["average_score"],
            recent_count=recent_count,
        )
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
