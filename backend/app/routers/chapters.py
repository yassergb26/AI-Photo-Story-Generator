"""
Chapters API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.database import get_db
from app.models import Chapter, Story, User, Image, StoryEmotion, Emotion
from app.schemas_chapters import (
    ChapterResponse,
    ChapterWithArcsResponse,
    ChapterGenerationRequest,
    ChapterGenerationResponse,
    StoryArcSummary,
    ChapterUpdate,
    UserBirthDateUpdate,
    UserBirthDateResponse
)
from app.services.chapter_generator import generate_chapters_for_user
from app.services.story_arc_detector import detect_story_arcs_for_chapter
from app.services.ai_narrative import enhance_chapter_with_ai_narrative, enhance_story_arc_with_ai_narrative
from typing import List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/chapters",
    tags=["chapters"]
)


def get_story_arc_dominant_emotion(story_id: int, db: Session):
    """
    Get the dominant emotion for a story arc
    Returns tuple of (emotion_name, percentage) or (None, None)
    """
    # Get the dominant emotion from story_emotions table (highest percentage)
    dominant = db.query(
        Emotion.name,
        StoryEmotion.percentage
    ).join(
        StoryEmotion, Emotion.id == StoryEmotion.emotion_id
    ).filter(
        StoryEmotion.story_id == story_id
    ).order_by(
        StoryEmotion.percentage.desc()
    ).first()

    if dominant:
        return dominant[0], float(dominant[1])
    return None, None


@router.get("", response_model=List[ChapterWithArcsResponse])
def get_user_chapters(user_id: int = 1, db: Session = Depends(get_db)):
    """
    Get all chapters for a user with nested story arcs
    """
    chapters = db.query(Chapter).filter(
        Chapter.user_id == user_id
    ).order_by(Chapter.sequence_order).all()

    response = []
    for chapter in chapters:
        # Get story arcs for this chapter
        story_arcs = db.query(Story).filter(
            Story.chapter_id == chapter.id
        ).order_by(Story.sequence_order).all()

        # Convert to response format with dominant emotions
        arc_summaries = []
        for arc in story_arcs:
            emotion_name, emotion_pct = get_story_arc_dominant_emotion(arc.id, db)
            arc_summaries.append(
                StoryArcSummary(
                    id=arc.id,
                    title=arc.title,
                    description=arc.description,
                    arc_type=arc.arc_type,
                    photo_count=arc.photo_count,
                    is_ai_detected=arc.is_ai_detected,
                    story_type=arc.story_type,
                    start_date=arc.start_date,
                    end_date=arc.end_date,
                    dominant_emotion=emotion_name,
                    emotion_percentage=emotion_pct
                )
            )

        chapter_response = ChapterWithArcsResponse(
            id=chapter.id,
            user_id=chapter.user_id,
            title=chapter.title,
            subtitle=chapter.subtitle,
            description=chapter.description,
            chapter_type=chapter.chapter_type,
            age_start=chapter.age_start,
            age_end=chapter.age_end,
            year_start=chapter.year_start,
            year_end=chapter.year_end,
            dominant_emotion=chapter.dominant_emotion,
            photo_count=chapter.photo_count,
            sequence_order=chapter.sequence_order,
            cover_image_id=chapter.cover_image_id,
            created_at=chapter.created_at,
            updated_at=chapter.updated_at,
            story_arcs=arc_summaries
        )

        response.append(chapter_response)

    return response


@router.get("/{chapter_id}", response_model=ChapterWithArcsResponse)
def get_chapter_by_id(chapter_id: int, db: Session = Depends(get_db)):
    """
    Get a single chapter by ID with story arcs
    """
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()

    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_id} not found"
        )

    # Get story arcs
    story_arcs = db.query(Story).filter(
        Story.chapter_id == chapter.id
    ).order_by(Story.sequence_order).all()

    arc_summaries = []
    for arc in story_arcs:
        emotion_name, emotion_pct = get_story_arc_dominant_emotion(arc.id, db)
        arc_summaries.append(
            StoryArcSummary(
                id=arc.id,
                title=arc.title,
                description=arc.description,
                arc_type=arc.arc_type,
                photo_count=arc.photo_count,
                is_ai_detected=arc.is_ai_detected,
                story_type=arc.story_type,
                start_date=arc.start_date,
                end_date=arc.end_date,
                dominant_emotion=emotion_name,
                emotion_percentage=emotion_pct
            )
        )

    return ChapterWithArcsResponse(
        id=chapter.id,
        user_id=chapter.user_id,
        title=chapter.title,
        subtitle=chapter.subtitle,
        description=chapter.description,
        chapter_type=chapter.chapter_type,
        age_start=chapter.age_start,
        age_end=chapter.age_end,
        year_start=chapter.year_start,
        year_end=chapter.year_end,
        dominant_emotion=chapter.dominant_emotion,
        photo_count=chapter.photo_count,
        sequence_order=chapter.sequence_order,
        cover_image_id=chapter.cover_image_id,
        created_at=chapter.created_at,
        updated_at=chapter.updated_at,
        story_arcs=arc_summaries
    )


@router.post("/generate", response_model=ChapterGenerationResponse)
async def generate_chapters(request: ChapterGenerationRequest, db: Session = Depends(get_db)):
    """
    Generate chapters for a user
    Includes:
    1. Chapter generation (age-based or year-based)
    2. Story arc detection
    3. AI narrative enhancement
    """
    try:
        logger.info(f"Generating chapters for user {request.user_id}")

        # Step 1: Generate chapters
        chapters = generate_chapters_for_user(
            user_id=request.user_id,
            db=db,
            force_regenerate=request.force_regenerate
        )

        if not chapters:
            return ChapterGenerationResponse(
                success=False,
                message="No photos found to generate chapters",
                chapters_generated=0,
                chapters=[]
            )

        logger.info(f"Generated {len(chapters)} chapters")

        # Step 2: Detect story arcs for each chapter
        all_chapters_with_arcs = []

        for chapter in chapters:
            # Detect story arcs
            story_arcs = detect_story_arcs_for_chapter(chapter.id, db)
            logger.info(f"Detected {len(story_arcs)} story arcs for chapter {chapter.id}")

            # Step 3: Enhance with AI narratives
            if story_arcs:
                # Enhance chapter narrative
                chapter = await enhance_chapter_with_ai_narrative(chapter, story_arcs, db)

                # Enhance story arc narratives
                for arc in story_arcs:
                    if not arc.description or arc.description.startswith("A memorable"):
                        await enhance_story_arc_with_ai_narrative(arc, db)

            # Build response with dominant emotions
            arc_summaries = []
            for arc in story_arcs:
                emotion_name, emotion_pct = get_story_arc_dominant_emotion(arc.id, db)
                arc_summaries.append(
                    StoryArcSummary(
                        id=arc.id,
                        title=arc.title,
                        description=arc.description,
                        arc_type=arc.arc_type,
                        photo_count=arc.photo_count,
                        is_ai_detected=arc.is_ai_detected,
                        story_type=arc.story_type,
                        start_date=arc.start_date,
                        end_date=arc.end_date,
                        dominant_emotion=emotion_name,
                        emotion_percentage=emotion_pct
                    )
                )

            chapter_response = ChapterWithArcsResponse(
                id=chapter.id,
                user_id=chapter.user_id,
                title=chapter.title,
                subtitle=chapter.subtitle,
                description=chapter.description,
                chapter_type=chapter.chapter_type,
                age_start=chapter.age_start,
                age_end=chapter.age_end,
                year_start=chapter.year_start,
                year_end=chapter.year_end,
                dominant_emotion=chapter.dominant_emotion,
                photo_count=chapter.photo_count,
                sequence_order=chapter.sequence_order,
                cover_image_id=chapter.cover_image_id,
                created_at=chapter.created_at,
                updated_at=chapter.updated_at,
                story_arcs=arc_summaries
            )

            all_chapters_with_arcs.append(chapter_response)

        return ChapterGenerationResponse(
            success=True,
            message=f"Successfully generated {len(chapters)} chapters with story arcs",
            chapters_generated=len(chapters),
            chapters=all_chapters_with_arcs
        )

    except Exception as e:
        logger.error(f"Error generating chapters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate chapters: {str(e)}"
        )


@router.post("/auto-generate")
async def auto_generate_pipeline(user_id: int = 1, db: Session = Depends(get_db)):
    """
    AUTO MODE: Run complete pipeline
    1. Spread capture dates across life phases (demo mode)
    2. Classify all unprocessed images (AI categories)
    3. Detect emotions on all images (facial analysis)
    4. Detect patterns (temporal, spatial, visual)
    5. Generate life story chapters
    6. Detect story arcs within chapters
    7. Enhance with AI narratives

    This is the "magic button" that processes everything automatically
    """
    try:
        logger.info(f"Starting auto-generate pipeline for user {user_id}")

        # Step 0: Get user and check birth date
        from app.models import ImageCategory, ImageEmotion, Emotion, Category
        from app.services import classify_image_file
        from app.services.emotion_detection import detect_emotions, get_dominant_emotion
        from datetime import timedelta
        import random

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.birth_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User birth date not set. Please set birth date in Chapters view first."
            )

        # Step 1: Get all images (both processed and unprocessed)
        all_images = db.query(Image).filter(Image.user_id == user_id).order_by(Image.upload_date).all()
        unprocessed_images = [img for img in all_images if not img.processed]

        classified_count = 0
        emotion_count = 0
        dates_spread_count = 0

        logger.info(f"Found {len(all_images)} total images, {len(unprocessed_images)} unprocessed")

        # Step 1a: Spread capture dates across life (for ALL images, not just unprocessed)
        # This ensures even already-processed images get proper dates
        if all_images:
            current_year = datetime.now().year
            birth_year = user.birth_date.year
            total_years = current_year - birth_year

            logger.info(f"Spreading {len(all_images)} images across {total_years} years ({birth_year}-{current_year})")

            for idx, image in enumerate(all_images):
                # Calculate year for this image (spread evenly)
                if len(all_images) > 1:
                    year_offset = int((idx / (len(all_images) - 1)) * total_years)
                else:
                    year_offset = total_years // 2

                # Add some randomness (±1 year)
                year_offset = max(0, min(total_years, year_offset + random.randint(-1, 1)))

                # Generate capture date
                capture_year = birth_year + year_offset
                capture_date = datetime(
                    capture_year,
                    random.randint(1, 12),  # Random month
                    random.randint(1, 28),  # Random day (safe for all months)
                    random.randint(8, 20),  # Random hour (daytime)
                    random.randint(0, 59),  # Random minute
                    random.randint(0, 59)   # Random second
                )

                image.capture_date = capture_date
                dates_spread_count += 1

            db.commit()
            logger.info(f"Spread capture dates for {dates_spread_count} images")

        # Step 2: Classify and detect emotions for each image
        for image in unprocessed_images:
            try:
                # Classification
                classification_results = classify_image_file(image.file_path, threshold=0.15, top_k=3)
                if classification_results:
                    for result in classification_results:
                        category = db.query(Category).filter(Category.name == result["category"]).first()
                        if not category:
                            category = Category(
                                name=result["category"],
                                description=f"Auto-generated category for {result['category']}"
                            )
                            db.add(category)
                            db.flush()

                        image_category = ImageCategory(
                            image_id=image.id,
                            category_id=category.id,
                            confidence_score=result["confidence"]
                        )
                        db.add(image_category)
                    classified_count += 1

                # Emotion Detection
                emotions_data = detect_emotions(image.file_path)
                if emotions_data:
                    dominant = get_dominant_emotion(emotions_data)
                    for emotion_data in emotions_data:
                        emotion_name = emotion_data['emotion']
                        emotion_obj = db.query(Emotion).filter(Emotion.name == emotion_name).first()

                        if emotion_obj:
                            image_emotion = ImageEmotion(
                                image_id=image.id,
                                emotion_id=emotion_obj.id,
                                confidence_score=emotion_data['confidence'],
                                face_count=1,
                                dominant_emotion=(emotion_name == dominant['emotion'])
                            )
                            db.add(image_emotion)
                    emotion_count += 1

                image.processed = True

            except Exception as e:
                logger.warning(f"Error processing image {image.id}: {e}")
                continue

        db.commit()
        logger.info(f"Classified {classified_count} images, detected emotions in {emotion_count} images")

        # Step 3: Detect patterns (temporal, spatial, visual)
        patterns_detected = 0
        try:
            from app.routers.patterns import detect_temporal_patterns, detect_spatial_patterns, detect_visual_patterns

            logger.info("Detecting patterns (temporal, spatial, visual)...")

            # Detect all pattern types
            detected_patterns = []
            temporal_patterns = await detect_temporal_patterns(db, user_id, all_images)
            detected_patterns.extend(temporal_patterns)

            spatial_patterns = await detect_spatial_patterns(db, user_id, all_images)
            detected_patterns.extend(spatial_patterns)

            visual_patterns = await detect_visual_patterns(db, user_id, all_images)
            detected_patterns.extend(visual_patterns)

            patterns_detected = len(detected_patterns)
            db.commit()
            logger.info(f"Detected {patterns_detected} patterns")
        except Exception as e:
            logger.warning(f"Pattern detection failed (non-critical): {e}")

        # Step 4: Generate chapters with story arcs
        chapters = generate_chapters_for_user(
            user_id=user_id,
            db=db,
            force_regenerate=True
        )

        if not chapters:
            return {
                "success": False,
                "message": "No photos found to generate chapters",
                "classified_count": classified_count,
                "emotion_count": emotion_count,
                "chapters_generated": 0
            }

        # Step 5: Detect story arcs and enhance with AI
        for chapter in chapters:
            story_arcs = detect_story_arcs_for_chapter(chapter.id, db)
            logger.info(f"Detected {len(story_arcs)} story arcs for chapter {chapter.id}")

            if story_arcs:
                chapter = await enhance_chapter_with_ai_narrative(chapter, story_arcs, db)

                # Generate AI titles and descriptions for ALL story arcs based on actual content
                from app.services.ai_narrative import generate_story_arc_title_and_narrative
                logger.info(f"Generating AI titles for {len(story_arcs)} story arcs...")

                for idx, arc in enumerate(story_arcs, 1):
                    # Use the unified metadata (classifications + emotions) for AI generation
                    metadata = arc.story_metadata or {}

                    arc_data = {
                        'categories': metadata.get('categories', []),
                        'emotions': metadata.get('emotions', []),
                        'photo_count': arc.photo_count,
                        'start_date': arc.start_date,
                        'end_date': arc.end_date,
                        'temporal_span_days': metadata.get('temporal_span_days', 0)
                    }

                    try:
                        logger.info(f"  [{idx}/{len(story_arcs)}] Generating AI title...")
                        ai_result = generate_story_arc_title_and_narrative(arc_data)
                        arc.title = ai_result['title']
                        arc.description = ai_result['description']
                        logger.info(f"  [{idx}/{len(story_arcs)}] ✓ {arc.title}")
                    except Exception as e:
                        logger.warning(f"  [{idx}/{len(story_arcs)}] ✗ AI generation failed: {e}")
                        # Keep the template title/description if AI fails

        db.commit()

        total_arcs = sum(len(db.query(Story).filter(Story.chapter_id == c.id).all()) for c in chapters)

        return {
            "success": True,
            "message": f"Auto-generation complete! Spread {dates_spread_count} dates, classified {classified_count} images, detected {emotion_count} emotions, found {patterns_detected} patterns, generated {len(chapters)} chapters with {total_arcs} story arcs",
            "dates_spread_count": dates_spread_count,
            "classified_count": classified_count,
            "emotion_count": emotion_count,
            "patterns_detected": patterns_detected,
            "chapters_generated": len(chapters),
            "story_arcs_count": total_arcs
        }

    except Exception as e:
        logger.error(f"Error in auto-generate pipeline: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-generation failed: {str(e)}"
        )


@router.put("/{chapter_id}", response_model=ChapterResponse)
def update_chapter(chapter_id: int, update: ChapterUpdate, db: Session = Depends(get_db)):
    """
    Update chapter details (title, subtitle, description)
    """
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()

    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_id} not found"
        )

    # Update fields
    if update.title is not None:
        chapter.title = update.title
    if update.subtitle is not None:
        chapter.subtitle = update.subtitle
    if update.description is not None:
        chapter.description = update.description
    if update.dominant_emotion is not None:
        chapter.dominant_emotion = update.dominant_emotion

    db.commit()
    db.refresh(chapter)

    return ChapterResponse.from_orm(chapter)


@router.delete("/delete-all")
async def delete_all_chapters(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Delete ALL chapters and story arcs for a user"""
    # Delete all story arcs first (foreign key constraint)
    story_count = db.query(Story).filter(Story.user_id == user_id).delete()

    # Delete all chapters
    chapter_count = db.query(Chapter).filter(Chapter.user_id == user_id).delete()

    db.commit()

    return {
        "message": f"Deleted {chapter_count} chapters and {story_count} story arcs",
        "chapters_deleted": chapter_count,
        "stories_deleted": story_count
    }


@router.delete("/{chapter_id}")
def delete_chapter(chapter_id: int, db: Session = Depends(get_db)):
    """
    Delete a chapter and its story arcs
    """
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()

    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_id} not found"
        )

    db.delete(chapter)
    db.commit()

    return {"success": True, "message": f"Chapter {chapter_id} deleted"}


@router.put("/users/{user_id}/birth-date", response_model=UserBirthDateResponse)
def update_user_birth_date(user_id: int, update: UserBirthDateUpdate, db: Session = Depends(get_db)):
    """
    Update user's birth date
    This will trigger chapter regeneration to use age-based grouping
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )

    # Update birth date
    user.birth_date = update.birth_date
    db.commit()
    db.refresh(user)

    return UserBirthDateResponse(
        success=True,
        message="Birth date updated successfully. Regenerate chapters to use age-based grouping.",
        birth_date=user.birth_date,
        has_birth_date=True
    )


@router.get("/users/{user_id}/birth-date", response_model=UserBirthDateResponse)
def get_user_birth_date(user_id: int, db: Session = Depends(get_db)):
    """
    Get user's birth date status
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )

    return UserBirthDateResponse(
        success=True,
        message="User found",
        birth_date=user.birth_date,
        has_birth_date=user.birth_date is not None
    )
