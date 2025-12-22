"""
Pydantic schemas for Chapters system
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, date


# Chapter schemas
class ChapterBase(BaseModel):
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    chapter_type: str = 'age_based'  # 'age_based', 'year_based', 'life_phase'
    age_start: Optional[int] = None
    age_end: Optional[int] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    dominant_emotion: Optional[str] = None


class ChapterCreate(ChapterBase):
    user_id: int


class ChapterUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    dominant_emotion: Optional[str] = None


class StoryArcSummary(BaseModel):
    """Summary of a story arc for chapter listing"""
    id: int
    title: str
    description: Optional[str] = None
    arc_type: Optional[str] = None
    photo_count: int
    is_ai_detected: bool
    story_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    dominant_emotion: Optional[str] = None
    emotion_percentage: Optional[float] = None

    class Config:
        from_attributes = True


class ChapterResponse(ChapterBase):
    id: int
    user_id: int
    photo_count: int
    sequence_order: int
    cover_image_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChapterWithArcsResponse(ChapterResponse):
    """Chapter with nested story arcs"""
    story_arcs: List[StoryArcSummary] = []

    class Config:
        from_attributes = True


class ChapterGenerationRequest(BaseModel):
    user_id: int
    force_regenerate: bool = False


class ChapterGenerationResponse(BaseModel):
    success: bool
    message: str
    chapters_generated: int
    chapters: List[ChapterWithArcsResponse]


# User birth date update
class UserBirthDateUpdate(BaseModel):
    birth_date: date


class UserBirthDateResponse(BaseModel):
    success: bool
    message: str
    birth_date: Optional[date] = None
    has_birth_date: bool
