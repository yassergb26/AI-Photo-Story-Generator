"""
SQLAlchemy database models
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, DECIMAL, JSON, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    birth_date = Column(Date)  # NEW: For age-based chapter grouping
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    images = relationship("Image", back_populates="user", cascade="all, delete-orphan")


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    thumbnail_path = Column(Text)  # NEW: Path to thumbnail image
    file_size = Column(Integer)
    file_hash = Column(String(64), unique=True)  # NEW: SHA-256 hash for duplicate detection
    upload_date = Column(TIMESTAMP, server_default=func.now())
    capture_date = Column(TIMESTAMP)
    exif_data = Column(JSON)
    processed = Column(Boolean, default=False)
    embedding_cached = Column(Boolean, default=False)  # NEW: Track if CLIP embedding is in Redis
    is_duplicate = Column(Boolean, default=False)  # NEW: Flag for duplicate images
    original_image_id = Column(Integer, ForeignKey("images.id"))  # NEW: Reference to original if duplicate
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="images")
    location = relationship("Location", back_populates="image", uselist=False, cascade="all, delete-orphan")
    image_categories = relationship("ImageCategory", back_populates="image", cascade="all, delete-orphan")
    image_emotions = relationship("ImageEmotion", back_populates="image", cascade="all, delete-orphan")
    life_event_images = relationship("LifeEventImage", back_populates="image", cascade="all, delete-orphan")
    original_image = relationship("Image", remote_side=[id], foreign_keys=[original_image_id])


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id", ondelete="CASCADE"), unique=True, nullable=False)
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    location_name = Column(String(255))
    city = Column(String(100))
    country = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    image = relationship("Image", back_populates="location")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    color_code = Column(String(7))
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    image_categories = relationship("ImageCategory", back_populates="category", cascade="all, delete-orphan")


class ImageCategory(Base):
    __tablename__ = "image_categories"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    confidence_score = Column(DECIMAL(5, 4), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    image = relationship("Image", back_populates="image_categories")
    category = relationship("Category", back_populates="image_categories")


class Story(Base):
    """
    Story Arcs table - individual stories/events within a chapter
    e.g., "The Wedding", "First Apartment", "Yosemite Trip 2022"
    """
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"))  # NEW: Parent chapter
    title = Column(String(255), nullable=False)
    description = Column(Text)  # AI-generated narrative/summary
    narrative_tone = Column(String(50))  # 'joyful', 'nostalgic', 'celebratory'
    story_type = Column(String(50))  # 'wedding', 'trip', 'birthday', 'graduation', etc.
    arc_type = Column(String(50))  # NEW: 'event', 'trip', 'milestone', 'tradition'
    cover_image_id = Column(Integer, ForeignKey("images.id", ondelete="SET NULL"))
    parent_story_id = Column(Integer, ForeignKey("stories.id", ondelete="CASCADE"))  # For hierarchical story arcs
    sequence_order = Column(Integer, default=0)  # Order within chapter
    start_date = Column(TIMESTAMP)  # Timeline start
    end_date = Column(TIMESTAMP)  # Timeline end
    status = Column(String(20), default='draft')  # 'draft', 'active', 'published', 'archived'
    auto_generated = Column(Boolean, default=True)  # AI-created or manual
    is_ai_detected = Column(Boolean, default=False)  # NEW: Detected from LifeEvents or patterns
    photo_count = Column(Integer, default=0)  # NEW: Count of photos in this arc
    generation_source = Column(String(50))  # 'time_cluster', 'ai_chapter_analysis', 'life_event', 'trip_cluster'
    story_metadata = Column(JSON)  # Story-specific data (life_event_id, location, etc.)
    view_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="stories")
    chapter = relationship("Chapter", back_populates="story_arcs")  # NEW
    cover_image = relationship("Image", foreign_keys=[cover_image_id])
    parent_story = relationship("Story", remote_side=[id], backref="child_stories")
    story_images = relationship("StoryImage", back_populates="story", cascade="all, delete-orphan")
    story_sections = relationship("StorySection", back_populates="story", cascade="all, delete-orphan")
    emotions = relationship("StoryEmotion", back_populates="story", cascade="all, delete-orphan")


class StoryImage(Base):
    """
    Junction table for many-to-many relationship between stories and images
    One photo can appear in multiple chapters (e.g., wedding photo in "2024 Highlights" and "The Wedding")
    """
    __tablename__ = "story_images"

    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    image_id = Column(Integer, ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    sequence_order = Column(Integer, default=0)  # Order within the story
    is_cover = Column(Boolean, default=False)  # Is this the cover image?
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    story = relationship("Story", back_populates="story_images")
    image = relationship("Image", backref="story_images")


class Chapter(Base):
    """
    Chapters table - high-level grouping of photos into life phases
    Groups photos by age ranges (e.g., "Building a Family" ages 28-30)
    or years (e.g., "Life in 2019") when no birth date is available
    """
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)  # e.g., "City Dreams", "Building a Family"
    subtitle = Column(Text)  # One-sentence summary
    description = Column(Text)  # Rich AI narrative (2-3 sentences)
    chapter_type = Column(String(50), default='age_based')  # 'age_based', 'year_based', 'life_phase'

    # Age-based fields (when user has birth_date)
    age_start = Column(Integer)  # e.g., 23
    age_end = Column(Integer)    # e.g., 30

    # Year-based fields (fallback when no birth_date)
    year_start = Column(Integer)  # e.g., 2018
    year_end = Column(Integer)    # e.g., 2019

    # Metadata
    photo_count = Column(Integer, default=0)
    dominant_emotion = Column(String(50))  # 'Joy', 'Excitement', 'Love'
    cover_image_id = Column(Integer, ForeignKey("images.id", ondelete="SET NULL"))
    sequence_order = Column(Integer, default=0)  # Order in user's life story

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="chapters")
    cover_image = relationship("Image", foreign_keys=[cover_image_id])
    story_arcs = relationship("Story", back_populates="chapter", cascade="all, delete-orphan")


class LifeEvent(Base):
    """
    Life Events table - stores detected major life events
    Auto-detects weddings, births, relocations, vacations, festivals, celebrations
    """
    __tablename__ = "life_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)  # 'wedding', 'birth', 'graduation', 'move', 'vacation', 'custom'
    event_name = Column(String(255), nullable=False)
    event_date = Column(TIMESTAMP)  # Single event date (or use start_date/end_date)
    event_location = Column(String(255))
    description = Column(Text)
    detection_method = Column(String(20), default='manual')  # 'manual', 'ai_detected', 'pattern_based'
    confidence_score = Column(DECIMAL(5, 4))  # Detection confidence
    event_metadata = Column(JSON)  # Event-specific data
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="life_events")
    life_event_images = relationship("LifeEventImage", back_populates="life_event", cascade="all, delete-orphan")


class LifeEventImage(Base):
    """
    Life Event Images junction table - many-to-many relationship
    """
    __tablename__ = "life_event_images"

    id = Column(Integer, primary_key=True, index=True)
    life_event_id = Column(Integer, ForeignKey("life_events.id", ondelete="CASCADE"), nullable=False)
    image_id = Column(Integer, ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    sequence_order = Column(Integer)
    is_cover_image = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    life_event = relationship("LifeEvent", back_populates="life_event_images")
    image = relationship("Image", back_populates="life_event_images")


class Emotion(Base):
    """
    Emotions table - predefined emotion types
    """
    __tablename__ = "emotions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # 'happy', 'excited', 'love', 'joy', etc.
    description = Column(Text)
    color_code = Column(String(7))  # For UI display
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    image_emotions = relationship("ImageEmotion", back_populates="emotion", cascade="all, delete-orphan")
    story_emotions = relationship("StoryEmotion", back_populates="emotion", cascade="all, delete-orphan")


class ImageEmotion(Base):
    """
    Image Emotions junction table - many-to-many with confidence scores
    """
    __tablename__ = "image_emotions"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    emotion_id = Column(Integer, ForeignKey("emotions.id", ondelete="CASCADE"), nullable=False)
    confidence_score = Column(DECIMAL(5, 4), nullable=False)
    face_count = Column(Integer, default=1)
    dominant_emotion = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    image = relationship("Image", back_populates="image_emotions")
    emotion = relationship("Emotion", back_populates="image_emotions")


class StoryEmotion(Base):
    """
    Story Emotions aggregation table - dominant emotions per story
    """
    __tablename__ = "story_emotions"

    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    emotion_id = Column(Integer, ForeignKey("emotions.id", ondelete="CASCADE"), nullable=False)
    percentage = Column(DECIMAL(5, 2), nullable=False)  # 0-100
    image_count = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    story = relationship("Story", back_populates="emotions")
    emotion = relationship("Emotion", back_populates="story_emotions")


class Pattern(Base):
    """
    Patterns table - stores detected recurring patterns
    Temporal (annual birthdays), Spatial (frequent locations), Visual (similar photos)
    """
    __tablename__ = "patterns"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pattern_type = Column(String(50), nullable=False)  # 'temporal', 'spatial', 'visual'
    frequency = Column(String(20))  # 'annual', 'monthly', 'weekly', 'custom'
    description = Column(Text)
    pattern_metadata = Column(JSON)  # Pattern-specific data (dates, locations, cluster_id)
    confidence_score = Column(DECIMAL(5, 4))
    detected_date = Column(TIMESTAMP, server_default=func.now())
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship("User", backref="patterns")
    pattern_images = relationship("PatternImage", back_populates="pattern", cascade="all, delete-orphan")


class PatternImage(Base):
    """
    Junction table linking patterns to their associated images
    """
    __tablename__ = "pattern_images"

    pattern_id = Column(Integer, ForeignKey("patterns.id", ondelete="CASCADE"), primary_key=True)
    image_id = Column(Integer, ForeignKey("images.id", ondelete="CASCADE"), primary_key=True)

    # Relationships
    pattern = relationship("Pattern", back_populates="pattern_images")
    image = relationship("Image", backref="pattern_images")


class StorySection(Base):
    """
    Story sections table - for multi-paragraph narratives
    Allows stories to be broken into introduction, body, and conclusion
    """
    __tablename__ = "story_sections"

    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    section_order = Column(Integer, nullable=False)
    section_title = Column(String(255))
    section_content = Column(Text, nullable=False)
    section_type = Column(String(50))  # 'intro', 'body', 'conclusion'
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    story = relationship("Story", back_populates="story_sections")


class BackgroundTask(Base):
    """
    Background tasks table - tracks async job status
    """
    __tablename__ = "background_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_type = Column(String(50), nullable=False)  # 'classification', 'pattern_detection', 'story_generation'
    task_id = Column(String(255), unique=True, nullable=False)  # Celery task ID
    status = Column(String(20), default='pending')  # 'pending', 'running', 'completed', 'failed'
    progress = Column(Integer, default=0)  # 0-100
    result = Column(JSON)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="background_tasks")
