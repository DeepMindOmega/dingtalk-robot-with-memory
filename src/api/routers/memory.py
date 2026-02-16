import sqlite3
import uuid
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

from ..models import (
    MemoryCreate,
    MemoryUpdate,
    MemoryResponse,
    MemoryType,
    SuccessResponse,
)
from ..dependencies import get_db, get_memories_dir, get_db_path

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
def create_memory(memory: MemoryCreate, conn: sqlite3.Connection = Depends(get_db)):
    try:
        now = datetime.now().isoformat()
        expires_at = memory.expires_at.isoformat() if memory.expires_at else None

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO memories (type, title, content, tags, source, created_at, updated_at, expires_at, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0)
            """,
            (
                memory.type.value,
                memory.title,
                memory.content,
                ",".join(memory.tags) if memory.tags else None,
                memory.source or "api",
                now,
                now,
                expires_at,
            ),
        )
        memory_id = cursor.lastrowid
        conn.commit()

        result = conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created memory",
            )

        return dict(result)
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/", response_model=List[MemoryResponse])
def list_memories(
    memory_type: Optional[MemoryType] = None,
    limit: int = 100,
    offset: int = 0,
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        query = "SELECT * FROM memories WHERE 1=1"
        params = []

        if memory_type:
            query += " AND type = ?"
            params.append(memory_type.value)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        results = conn.execute(query, params).fetchall()
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error listing memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{memory_id}", response_model=MemoryResponse)
def get_memory(memory_id: str, conn: sqlite3.Connection = Depends(get_db)):
    try:
        result = conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found"
            )

        return dict(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.put("/{memory_id}", response_model=MemoryResponse)
def update_memory(
    memory_id: str,
    memory_update: MemoryUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        existing = conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found"
            )

        updates = []
        params = []

        if memory_update.title is not None:
            updates.append("title = ?")
            params.append(memory_update.title)

        if memory_update.content is not None:
            updates.append("content = ?")
            params.append(memory_update.content)

        if memory_update.tags is not None:
            updates.append("tags = ?")
            params.append(",".join(memory_update.tags))

        if memory_update.source is not None:
            updates.append("source = ?")
            params.append(memory_update.source)

        if memory_update.expires_at is not None:
            updates.append("expires_at = ?")
            params.append(memory_update.expires_at.isoformat())

        if memory_update.score is not None:
            updates.append("score = ?")
            params.append(memory_update.score)

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())

        params.append(memory_id)

        if updates:
            conn.execute(
                f"UPDATE memories SET {', '.join(updates)} WHERE id = ?", params
            )
            conn.commit()

        result = conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()

        return dict(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete("/{memory_id}", response_model=SuccessResponse)
def delete_memory(memory_id: str, conn: sqlite3.Connection = Depends(get_db)):
    try:
        existing = conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found"
            )

        conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.commit()

        return SuccessResponse(
            success=True, message=f"Memory {memory_id} deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/{memory_id}/score", response_model=MemoryResponse)
def update_memory_score(
    memory_id: str, score: float, conn: sqlite3.Connection = Depends(get_db)
):
    try:
        if not 0.0 <= score <= 1.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Score must be between 0.0 and 1.0",
            )

        existing = conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found"
            )

        conn.execute(
            "UPDATE memories SET score = ?, updated_at = ? WHERE id = ?",
            (score, datetime.now().isoformat(), memory_id),
        )
        conn.commit()

        result = conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()

        return dict(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating memory score: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/cleanup", response_model=SuccessResponse)
def cleanup_expired_memories(conn: sqlite3.Connection = Depends(get_db)):
    try:
        deleted = conn.execute(
            "DELETE FROM memories WHERE expires_at < datetime('now')"
        ).rowcount
        conn.commit()

        return SuccessResponse(
            success=True, message=f"Cleaned up {deleted} expired memories"
        )
    except Exception as e:
        logger.error(f"Error cleaning up memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
