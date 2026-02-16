import sqlite3
import json
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel

from ..models import (
    ConfigCreate,
    ConfigUpdate,
    ConfigResponse,
    RollbackResponse,
    SuccessResponse,
)
from ..dependencies import get_db, get_db_path
from ...config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
def create_config(config: ConfigCreate, conn: sqlite3.Connection = Depends(get_db)):
    try:
        manager = ConfigManager(str(get_db_path()))
        manager.update_config(
            agent_id=config.agent_id,
            config=config.config_data,
        )

        result = conn.execute(
            "SELECT * FROM config_history WHERE agent_id = ? ORDER BY created_at DESC LIMIT 1",
            (config.agent_id,),
        ).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created config",
            )

        result_dict = dict(result)
        result_dict["config_data"] = json.loads(result_dict["config_data"])
        return result_dict
    except Exception as e:
        logger.error(f"Error creating config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/agents/{agent_id}", response_model=ConfigResponse)
def get_agent_config(agent_id: str, conn: sqlite3.Connection = Depends(get_db)):
    try:
        result = conn.execute(
            "SELECT * FROM config_history WHERE agent_id = ? ORDER BY updated_at DESC LIMIT 1",
            (agent_id,),
        ).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config not found for agent {agent_id}",
            )

        result_dict = dict(result)
        result_dict["config_data"] = json.loads(result_dict["config_data"])
        return result_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.put("/agents/{agent_id}", response_model=ConfigResponse)
def update_agent_config(
    agent_id: str,
    config_update: ConfigUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        manager = ConfigManager(str(conn.execute("PRAGMA database_list").fetchone()[2]))
        manager.update_config(
            agent_id=agent_id,
            config=config_update.config_data,
        )

        result = conn.execute(
            "SELECT * FROM config_history WHERE agent_id = ? ORDER BY created_at DESC LIMIT 1",
            (agent_id,),
        ).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Failed to retrieve updated config",
            )

        result_dict = dict(result)
        result_dict["config_data"] = json.loads(result_dict["config_data"])
        return result_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/agents/{agent_id}/history", response_model=List[ConfigResponse])
def get_config_history(
    agent_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        results = conn.execute(
            """
            SELECT * FROM config_history
            WHERE agent_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (agent_id, limit),
        ).fetchall()

        return [
            {**dict(row), "config_data": json.loads(row["config_data"])}
            for row in results
        ]
    except Exception as e:
        logger.error(f"Error getting config history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/agents/{agent_id}/rollback/{config_id}", response_model=RollbackResponse)
def rollback_config(
    agent_id: str, config_id: str, conn: sqlite3.Connection = Depends(get_db)
):
    try:
        manager = ConfigManager(str(conn.execute("PRAGMA database_list").fetchone()[2]))
        success = manager.rollback_config(agent_id, config_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to rollback config",
            )

        result = conn.execute(
            "SELECT * FROM config_history WHERE agent_id = ? ORDER BY created_at DESC LIMIT 1",
            (agent_id,),
        ).fetchone()

        return RollbackResponse(
            success=True,
            message=f"Successfully rolled back to config {config_id}",
            config_id=dict(result).get("id") if result else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rolling back config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/", response_model=List[ConfigResponse])
def list_all_configs(conn: sqlite3.Connection = Depends(get_db)):
    try:
        results = conn.execute(
            "SELECT DISTINCT agent_id FROM config_history ORDER BY agent_id"
        ).fetchall()

        configs = []
        for row in results:
            agent_id = row["agent_id"]
            latest = conn.execute(
                "SELECT * FROM config_history WHERE agent_id = ? ORDER BY created_at DESC LIMIT 1",
                (agent_id,),
            ).fetchone()

            if latest:
                latest_dict = dict(latest)
                latest_dict["config_data"] = json.loads(latest_dict["config_data"])
                configs.append(latest_dict)

        return configs
    except Exception as e:
        logger.error(f"Error listing configs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete("/agents/{agent_id}/cleanup", response_model=SuccessResponse)
def cleanup_old_configs(
    agent_id: str,
    keep_versions: int = Query(default=10, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        manager = ConfigManager(str(conn.execute("PRAGMA database_list").fetchone()[2]))
        manager.delete_old_entries(agent_id, keep_versions=keep_versions)

        return SuccessResponse(
            success=True,
            message=f"Cleaned up old configs for agent {agent_id}, keeping last {keep_versions} versions",
        )
    except Exception as e:
        logger.error(f"Error cleaning up configs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/validate", response_model=SuccessResponse)
def validate_config(config_data: dict, conn: sqlite3.Connection = Depends(get_db)):
    try:
        manager = ConfigManager(str(conn.execute("PRAGMA database_list").fetchone()[2]))
        is_valid, errors = manager.validate_config(config_data)

        if is_valid:
            return SuccessResponse(
                success=True, message="Configuration is valid", data={"valid": True}
            )
        else:
            return SuccessResponse(
                success=False,
                message="Configuration validation failed",
                data={"valid": False, "errors": errors},
            )
    except Exception as e:
        logger.error(f"Error validating config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
