"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime


# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Image schemas
class ImageBase(BaseModel):
    filename: str


class ImageUploadResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    file_size: Optional[int]
    upload_date: datetime
    capture_date: Optional[datetime]

    class Config:
        from_attributes = True


class ImageDetailResponse(ImageUploadResponse):
    exif_data: Optional[Dict[str, Any]]
    processed: bool
    location: Optional["LocationResponse"]

    class Config:
        from_attributes = True


# Location schemas
class LocationResponse(BaseModel):
    latitude: Optional[float]
    longitude: Optional[float]
    location_name: Optional[str]
    city: Optional[str]
    country: Optional[str]

    class Config:
        from_attributes = True


# Category schemas
class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    color_code: Optional[str]

    class Config:
        from_attributes = True


# Upload response
# Alias for story image responses
ImageResponse = ImageUploadResponse


class UploadResponse(BaseModel):
    success: bool
    uploaded_count: int
    image_ids: list[int]
    message: str


# Classification schemas
class CategoryWithConfidence(BaseModel):
    id: int
    name: str
    confidence: float


class ClassificationResponse(BaseModel):
    image_id: int
    filename: str
    categories: list[CategoryWithConfidence]
    message: str


class CategoryWithConfidenceDetail(CategoryResponse):
    confidence: float


class ImageWithCategoriesResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    file_size: Optional[int]
    upload_date: datetime
    capture_date: Optional[datetime]
    processed: bool
    categories: list[CategoryWithConfidenceDetail]

    class Config:
        from_attributes = True


# Pattern schemas
class PatternBase(BaseModel):
    pattern_type: str  # 'temporal', 'spatial', 'visual'
    frequency: Optional[str]  # 'annual', 'monthly', 'weekly', 'custom'
    description: Optional[str]


class PatternCreate(PatternBase):
    user_id: int
    pattern_metadata: Optional[Dict[str, Any]]
    confidence_score: Optional[float]


class PatternResponse(PatternBase):
    id: int
    user_id: int
    pattern_metadata: Optional[Dict[str, Any]]
    confidence_score: Optional[float]
    detected_date: datetime
    created_at: datetime
    image_count: Optional[int] = 0  # Computed field for number of images

    class Config:
        from_attributes = True


class PatternWithImagesResponse(PatternResponse):
    images: list[ImageUploadResponse]

    class Config:
        from_attributes = True


class PatternDetectionRequest(BaseModel):
    user_id: int
    pattern_types: Optional[list[str]] = ["temporal", "spatial", "visual"]  # Which patterns to detect
    force_redetect: bool = False  # Re-detect even if patterns exist


class PatternDetectionResponse(BaseModel):
    success: bool
    message: str
    patterns_detected: int
    patterns: list[PatternResponse]


# Story Schemas
class StoryBase(BaseModel):
    title: str
    description: Optional[str] = None  # Use description to match existing Story model
    story_metadata: Optional[Dict[str, Any]] = None


class StoryCreate(StoryBase):
    user_id: int
    image_ids: Optional[list[int]] = []


class StoryUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    story_metadata: Optional[Dict[str, Any]] = None


class StoryResponse(StoryBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    image_count: Optional[int] = 0

    class Config:
        from_attributes = True


class StoryWithImagesResponse(StoryResponse):
    images: list[ImageResponse]

    class Config:
        from_attributes = True


class StoryGenerationRequest(BaseModel):
    user_id: int
    pattern_id: Optional[int] = None
    force_regenerate: bool = False


class StoryGenerationResponse(BaseModel):
    success: bool
    message: str
    stories_generated: int
    stories: list[StoryResponse]


# Life Event schemas
class LifeEventBase(BaseModel):
    event_type: str  # 'wedding', 'birth', 'graduation', 'move', 'vacation', 'birthday', 'anniversary', 'custom'
    event_name: str
    event_date: Optional[datetime] = None
    event_location: Optional[str] = None
    description: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None


class LifeEventCreate(LifeEventBase):
    user_id: int
    image_ids: Optional[list[int]] = []  # Images to link to this event


class LifeEventUpdate(BaseModel):
    event_type: Optional[str] = None
    event_name: Optional[str] = None
    event_date: Optional[datetime] = None
    event_location: Optional[str] = None
    description: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None


class LifeEventResponse(LifeEventBase):
    id: int
    user_id: int
    detection_method: str
    confidence_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    image_count: Optional[int] = 0  # Computed field

    class Config:
        from_attributes = True


class LifeEventImageResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    thumbnail_path: Optional[str] = None
    capture_date: Optional[datetime] = None
    sequence_order: Optional[int] = None
    is_cover_image: bool

    class Config:
        from_attributes = True


class LifeEventWithImagesResponse(LifeEventResponse):
    images: list[LifeEventImageResponse]

    class Config:
        from_attributes = True


class LinkImagesToEventRequest(BaseModel):
    image_ids: list[int]
