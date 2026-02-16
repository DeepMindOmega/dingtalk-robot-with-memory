from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MemoryType(str, Enum):
    LONG_TERM = "long_term"
    SHORT_TERM = "short_term"
    SESSION = "session"


class MemoryCategory(str, Enum):
    SUCCESS_CASE = "success_case"
    FAILURE_LESSON = "failure_lesson"
    SKILL_GROWTH = "skill_growth"
    USER_PREFERENCE = "user_preference"
    GENERAL = "general"


class MemoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    type: MemoryType = MemoryType.LONG_TERM
    tags: List[str] = []
    source: Optional[str] = None
    expires_at: Optional[datetime] = None
    session_id: Optional[str] = None


class MemoryUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    expires_at: Optional[datetime] = None
    score: Optional[float] = Field(None, ge=0.0, le=1.0)


class MemoryResponse(BaseModel):
    id: int
    title: str
    content: str
    type: str
    tags: Optional[str]
    source: Optional[str]
    created_at: str
    updated_at: str
    expires_at: Optional[str]
    score: float

    class Config:
        from_attributes = True


class MemorySearchRequest(BaseModel):
    keyword: Optional[str] = None
    type: Optional[MemoryType] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    hybrid: bool = False


class SearchResponse(BaseModel):
    results: List[MemoryResponse]
    total: int
    limit: int
    offset: int


class MemoryStatsResponse(BaseModel):
    total: int
    by_type: Dict[str, int]
    by_category: Dict[str, int]
    average_score: float
    recent_count: int


class ConfigCreate(BaseModel):
    agent_id: str
    config_data: Dict[str, Any]
    auto_apply: bool = False


class ConfigUpdate(BaseModel):
    config_data: Dict[str, Any]
    auto_apply: bool = False


class ConfigResponse(BaseModel):
    id: int
    agent_id: str
    config_data: Dict[str, Any]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class RollbackResponse(BaseModel):
    success: bool
    message: str
    config_id: Optional[str] = None


class ReportCreate(BaseModel):
    report_type: str = Field(..., pattern="^(daily|weekly|monthly|custom)$")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    agent_id: Optional[str] = None


class ReportResponse(BaseModel):
    id: int
    report_type: str
    start_date: str
    end_date: str
    content: str
    created_at: str

    class Config:
        from_attributes = True


class DashboardStatsResponse(BaseModel):
    total_memories: int
    total_configs: int
    total_reports: int
    active_tasks: int
    memory_type_distribution: Dict[str, int]
    memory_category_distribution: Dict[str, int]
    recent_memories: List[MemoryResponse]
    recent_reports: List[ReportResponse]


class ChartDataPoint(BaseModel):
    label: str
    value: int


class TrendResponse(BaseModel):
    period: str
    data: List[ChartDataPoint]
    total: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
