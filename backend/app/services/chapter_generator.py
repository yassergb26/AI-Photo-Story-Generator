"""
Chapter Generation Service
Generates age-based or year-based chapters from user photos
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models import User, Image, Chapter, Story, LifeEvent, Emotion, ImageEmotion
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import logging

logger = logging.getLogger(__name__)


# Life phase definitions based on age ranges
LIFE_PHASES = {
    (0, 5): "Early Childhood",
    (6, 12): "Childhood Wonder",
    (13, 17): "Teenage Years",
    (18, 22): "College & Discovery",
    (23, 28): "Young Adulthood",
    (29, 35): "Building a Life",
    (36, 45): "Family & Career",
    (46, 55): "Prime Years",
    (56, 65): "Wisdom Years",
    (66, 100): "Golden Years"
}


def get_life_phase(age: int) -> str:
    """Map age to life phase name"""
    for (start, end), phase in LIFE_PHASES.items():
        if start <= age <= end:
            return phase
    return "Life Journey"


def calculate_age(birth_date: date, at_date: datetime) -> int:
    """Calculate age at a specific date"""
    return at_date.year - birth_date.year - (
        (at_date.month, at_date.day) < (birth_date.month, birth_date.day)
    )


def group_photos_by_age(photos: List[Image], birth_date: date) -> Dict[int, List[Image]]:
    """Group photos by user's age when photo was taken"""
    age_groups = {}

    for photo in photos:
        if not photo.capture_date:
            continue

        age = calculate_age(birth_date, photo.capture_date)
        if age not in age_groups:
            age_groups[age] = []
        age_groups[age].append(photo)

    return age_groups


def group_photos_by_year(photos: List[Image]) -> Dict[int, List[Image]]:
    """Group photos by year (fallback when no birth date)"""
    year_groups = {}

    for photo in photos:
        if not photo.capture_date:
            continue

        year = photo.capture_date.year
        if year not in year_groups:
            year_groups[year] = []
        year_groups[year].append(photo)

    return year_groups


def merge_adjacent_groups(groups: Dict[int, List[Image]], max_gap: int = 1) -> List[Tuple[int, int, List[Image]]]:
    """
    Merge adjacent age/year groups into chapters
    Returns list of (start, end, photos)
    """
    if not groups:
        return []

    sorted_keys = sorted(groups.keys())
    chapters = []
    current_start = sorted_keys[0]
    current_end = sorted_keys[0]
    current_photos = groups[sorted_keys[0]].copy()

    for i in range(1, len(sorted_keys)):
        key = sorted_keys[i]
        prev_key = sorted_keys[i-1]

        # Check if we should merge with previous group
        if key - prev_key <= max_gap:
            current_end = key
            current_photos.extend(groups[key])
        else:
            # Save current chapter and start new one
            chapters.append((current_start, current_end, current_photos))
            current_start = key
            current_end = key
            current_photos = groups[key].copy()

    # Add final chapter
    chapters.append((current_start, current_end, current_photos))

    return chapters


def get_dominant_emotion(photos: List[Image], db: Session) -> Optional[str]:
    """Get the most common emotion from photos"""
    photo_ids = [p.id for p in photos]

    if not photo_ids:
        return None

    # Query emotion counts
    emotion_counts = db.query(
        Emotion.name,
        func.count(ImageEmotion.id).label('count')
    ).join(
        ImageEmotion, ImageEmotion.emotion_id == Emotion.id
    ).filter(
        ImageEmotion.image_id.in_(photo_ids)
    ).group_by(
        Emotion.name
    ).order_by(
        func.count(ImageEmotion.id).desc()
    ).first()

    return emotion_counts[0] if emotion_counts else None


def generate_age_based_chapters(user: User, photos: List[Image], db: Session) -> List[Chapter]:
    """Generate chapters based on user's age"""
    if not user.birth_date:
        return []

    logger.info(f"Generating age-based chapters for user {user.id}")

    # Group photos by age
    age_groups = group_photos_by_age(photos, user.birth_date)

    if not age_groups:
        logger.warning(f"No photos with capture dates for user {user.id}")
        return []

    # Group ages into life phases instead of merging adjacent ages
    # This creates proper chapters like: 0-5, 6-12, 13-17, 18-22, etc.
    life_phase_groups = {}

    for age, age_photos in age_groups.items():
        # Find which life phase this age belongs to
        phase_key = None
        for (start, end), phase_name in LIFE_PHASES.items():
            if start <= age <= end:
                phase_key = (start, end)
                break

        if phase_key:
            if phase_key not in life_phase_groups:
                life_phase_groups[phase_key] = []
            life_phase_groups[phase_key].extend(age_photos)

    # Convert to list of (start, end, photos) tuples sorted by age
    merged_chapters = [
        (start, end, photos)
        for (start, end), photos in sorted(life_phase_groups.items())
    ]

    chapters = []
    for sequence, (age_start, age_end, chapter_photos) in enumerate(merged_chapters):
        # Get life phase name
        life_phase = get_life_phase(age_start)

        # Calculate years
        year_start = user.birth_date.year + age_start
        year_end = user.birth_date.year + age_end

        # Get dominant emotion
        dominant_emotion = get_dominant_emotion(chapter_photos, db)

        # Create age range string for title
        if age_start == age_end:
            age_str = f"Age {age_start}"
        else:
            age_str = f"Ages {age_start}-{age_end}"

        # Create chapter
        chapter = Chapter(
            user_id=user.id,
            title=life_phase,  # Will be enhanced with AI later
            subtitle=f"{age_str} ({year_start}-{year_end})",
            chapter_type='age_based',
            age_start=age_start,
            age_end=age_end,
            year_start=year_start,
            year_end=year_end,
            photo_count=len(chapter_photos),
            dominant_emotion=dominant_emotion,
            sequence_order=sequence,
            cover_image_id=chapter_photos[0].id if chapter_photos else None
        )

        chapters.append(chapter)
        logger.info(f"Created chapter: {chapter.title} ({age_str}, {len(chapter_photos)} photos)")

    return chapters


def generate_year_based_chapters(user: User, photos: List[Image], db: Session) -> List[Chapter]:
    """Generate chapters based on years (fallback when no birth date)"""
    logger.info(f"Generating year-based chapters for user {user.id}")

    # Group photos by year
    year_groups = group_photos_by_year(photos)

    if not year_groups:
        logger.warning(f"No photos with capture dates for user {user.id}")
        return []

    # Merge adjacent years into chapters (merge if gap <= 1 year)
    merged_chapters = merge_adjacent_groups(year_groups, max_gap=1)

    chapters = []
    for sequence, (year_start, year_end, chapter_photos) in enumerate(merged_chapters):
        # Get dominant emotion
        dominant_emotion = get_dominant_emotion(chapter_photos, db)

        # Create title
        if year_start == year_end:
            title = f"Life in {year_start}"
        else:
            title = f"Memories {year_start}-{year_end}"

        # Create chapter
        chapter = Chapter(
            user_id=user.id,
            title=title,
            subtitle=None,
            chapter_type='year_based',
            age_start=None,
            age_end=None,
            year_start=year_start,
            year_end=year_end,
            photo_count=len(chapter_photos),
            dominant_emotion=dominant_emotion,
            sequence_order=sequence,
            cover_image_id=chapter_photos[0].id if chapter_photos else None
        )

        chapters.append(chapter)
        logger.info(f"Created chapter: {chapter.title} ({len(chapter_photos)} photos)")

    return chapters


def generate_chapters_for_user(user_id: int, db: Session, force_regenerate: bool = False) -> List[Chapter]:
    """
    Main function to generate chapters for a user

    Args:
        user_id: User ID
        db: Database session
        force_regenerate: Delete existing chapters and regenerate

    Returns:
        List of generated Chapter objects
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Check if chapters already exist
    existing_chapters = db.query(Chapter).filter(Chapter.user_id == user_id).count()
    if existing_chapters > 0 and not force_regenerate:
        logger.info(f"User {user_id} already has {existing_chapters} chapters")
        return db.query(Chapter).filter(Chapter.user_id == user_id).order_by(Chapter.sequence_order).all()

    # Delete existing chapters if force regenerate
    if force_regenerate and existing_chapters > 0:
        db.query(Chapter).filter(Chapter.user_id == user_id).delete()
        db.commit()
        logger.info(f"Deleted {existing_chapters} existing chapters for user {user_id}")

    # Get all photos for user (use upload_date as fallback for capture_date)
    photos = db.query(Image).filter(Image.user_id == user_id).all()

    if not photos:
        logger.warning(f"No photos found for user {user_id}")
        return []

    # For photos without capture_date, use upload_date as fallback
    for photo in photos:
        if not photo.capture_date and photo.upload_date:
            photo.capture_date = photo.upload_date

    # Filter out photos without any date
    photos = [p for p in photos if p.capture_date is not None]

    if not photos:
        logger.warning(f"No photos with dates for user {user_id}")
        return []

    # Sort by capture date
    photos.sort(key=lambda p: p.capture_date)

    logger.info(f"Found {len(photos)} photos with dates for user {user_id}")

    # Generate chapters based on whether user has birth date
    if user.birth_date:
        chapters = generate_age_based_chapters(user, photos, db)
    else:
        chapters = generate_year_based_chapters(user, photos, db)

    # Save chapters to database
    for chapter in chapters:
        db.add(chapter)

    db.commit()

    # Refresh to get IDs
    for chapter in chapters:
        db.refresh(chapter)

    logger.info(f"Generated {len(chapters)} chapters for user {user_id}")

    return chapters
