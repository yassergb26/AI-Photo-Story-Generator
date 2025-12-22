"""
Story generation endpoints for creating narratives from patterns
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, String
from typing import List, Optional
import logging
from datetime import datetime

from app.database import get_db
from app.models import Story, StoryImage, Pattern, PatternImage, Image, User, Category, ImageCategory, Emotion, StoryEmotion
from app.schemas import (
    StoryResponse, StoryWithImagesResponse, StoryCreate, StoryUpdate,
    StoryGenerationRequest, StoryGenerationResponse
)
from app.services.narrative_generation import generate_narrative

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stories", tags=["stories"])


# Story templates for different pattern types
STORY_TEMPLATES = {
    "temporal_annual": {
        "title_templates": [
            "Annual {category} Tradition",
            "Yearly {category} Celebration",
            "Our {category} Ritual"
        ],
        "content_templates": [
            "Every year around {month_name}, a special tradition unfolds. Through {image_count} cherished moments captured over {year_span} years, this collection tells the story of a meaningful annual celebration that has become an important part of life.",
            "Year after year, {month_name} marks a time of {category} and joy. This collection of {image_count} images spans {year_span} years, documenting the evolution and consistency of a beloved tradition.",
            "A tradition that repeats with the calendar - every {month_name} brings new memories while honoring familiar rituals. {image_count} images across {year_span} years capture the essence of this annual celebration."
        ]
    },
    "temporal_monthly": {
        "title_templates": [
            "Monthly {category} Moments",
            "{month_name} Gatherings",
            "Regular {category} Meetups"
        ],
        "content_templates": [
            "Some moments happen like clockwork. This collection captures recurring {category} experiences from {month_name}, with {image_count} memories documented across different years.",
            "In {month_name}, something special happens regularly. Through {image_count} images, this story chronicles the consistent joy and connection of these monthly moments.",
            "{month_name} has become synonymous with {category}. This narrative weaves together {image_count} images that celebrate the rhythm and routine of these regular gatherings."
        ]
    },
    "spatial": {
        "title_templates": [
            "Adventures at {location}",
            "{location} Memories",
            "Our {location} Story"
        ],
        "content_templates": [
            "Some places hold special meaning, becoming backdrops for countless memories. This collection brings together {image_count} moments captured at {location}, each image adding a new chapter to the story of this meaningful place.",
            "{location} has been witness to {image_count} memorable moments. From quiet contemplation to joyous celebration, this place has become woven into the fabric of daily life.",
            "Every visit to {location} creates new memories while echoing familiar feelings. This narrative connects {image_count} images that showcase why this place has become so significant."
        ]
    },
    "visual": {
        "title_templates": [
            "{category} Collection",
            "The {category} Chronicles",
            "Moments of {category}"
        ],
        "content_templates": [
            "Some themes emerge naturally through photography. This collection of {image_count} {category} images reveals patterns in life - the subjects, moods, and moments that draw our attention and deserve to be remembered.",
            "Through {image_count} images, a story of {category} unfolds. Each photo captures a moment that shares something essential with the others - a visual narrative of recurring themes and meaningful subjects.",
            "{category} moments deserve their own chapter. This curated collection of {image_count} images celebrates the beauty, joy, and significance found in these recurring visual themes."
        ]
    }
}


def generate_story_from_pattern(db: Session, pattern: Pattern, user_id: int) -> Optional[Story]:
    """
    Generate a story narrative from a detected pattern using AI
    """
    try:
        logger.info(f"Generating story for pattern {pattern.id} (type: {pattern.pattern_type})")

        # Get all images in the pattern
        pattern_images = db.query(PatternImage).filter(
            PatternImage.pattern_id == pattern.id
        ).all()

        logger.info(f"Found {len(pattern_images)} pattern_image records for pattern {pattern.id}")

        image_ids = [pi.image_id for pi in pattern_images]
        images = db.query(Image).filter(Image.id.in_(image_ids)).all()

        logger.info(f"Found {len(images)} actual images for pattern {pattern.id}")

        if not images:
            logger.warning(f"No images found for pattern {pattern.id} - cannot generate story")
            return None

        # Extract pattern metadata
        metadata = pattern.pattern_metadata or {}

        # Get category names from images
        categories_query = db.query(Category.name, Category.id)\
            .join(ImageCategory)\
            .join(Image)\
            .filter(Image.id.in_(image_ids))\
            .distinct()\
            .limit(5)\
            .all()
        categories = [cat.name for cat in categories_query]

        # Get category name for visual patterns
        category_name = categories[0] if categories else "moments"
        if pattern.pattern_type == "visual" and "category" in metadata:
            category_name = metadata["category"]

        # Get location name for spatial patterns
        location = None
        if pattern.pattern_type == "spatial" and metadata:
            if "location_name" in metadata:
                location = metadata["location_name"]
            elif "city" in metadata:
                location = metadata["city"]

        # Get date range from images
        start_date = None
        end_date = None
        for img in images:
            if img.metadata and isinstance(img.metadata, dict):
                img_date = img.metadata.get('capture_date')
                if img_date:
                    if isinstance(img_date, str):
                        try:
                            img_date = datetime.fromisoformat(img_date)
                        except:
                            continue
                    if not start_date or img_date < start_date:
                        start_date = img_date
                    if not end_date or img_date > end_date:
                        end_date = img_date

        # Create temporary story to get emotions
        temp_story = Story(
            user_id=user_id,
            title="Temporary",
            description="Temporary",
            auto_generated=True
        )
        db.add(temp_story)
        db.flush()

        # Link images temporarily to get emotions
        for image_id in image_ids:
            story_image = StoryImage(
                story_id=temp_story.id,
                image_id=image_id,
                sequence_order=image_ids.index(image_id)
            )
            db.add(story_image)
        db.flush()

        # Calculate story emotions (same logic as in patterns.py)
        from sqlalchemy import func as sql_func
        from app.models import ImageEmotion

        emotion_aggregates = db.query(
            Emotion.id,
            Emotion.name,
            sql_func.avg(ImageEmotion.confidence_score).label('avg_confidence')
        ).join(ImageEmotion).join(Image).filter(
            Image.id.in_(image_ids)
        ).group_by(Emotion.id, Emotion.name).all()

        emotions_dict = {}
        for emotion_id, emotion_name, avg_confidence in emotion_aggregates:
            percentage = float(avg_confidence * 100)
            emotions_dict[emotion_name] = percentage

            # Count how many images have this emotion
            image_count = db.query(ImageEmotion).filter(
                ImageEmotion.image_id.in_(image_ids),
                ImageEmotion.emotion_id == emotion_id
            ).count()

            # Save to story_emotions table
            story_emotion = StoryEmotion(
                story_id=temp_story.id,
                emotion_id=emotion_id,
                percentage=percentage,
                image_count=image_count
            )
            db.add(story_emotion)

        # Build metadata for AI narrative generation
        story_metadata = {
            "image_count": len(images),
            "categories": categories,
            "emotions": emotions_dict,
            "start_date": start_date,
            "end_date": end_date,
            "location": location,
            "category": category_name,
            "event_name": pattern.pattern_type or "moments",
            "pattern_type": pattern.pattern_type
        }

        # Generate narrative using AI with joyful tone by default
        logger.info(f"Calling generate_narrative for pattern {pattern.id} with metadata: {story_metadata}")

        try:
            narrative_data = generate_narrative(
                story_metadata=story_metadata,
                narrative_tone="joyful",
                pattern_type=pattern.pattern_type or "visual",
                use_llm=True  # Use AI for auto-generation
            )
            logger.info(f"Successfully generated narrative: {narrative_data}")
        except Exception as gen_error:
            logger.error(f"Error in generate_narrative: {str(gen_error)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

        # Update the temporary story with AI-generated content
        temp_story.title = narrative_data['title']
        temp_story.description = narrative_data['description']
        temp_story.narrative_tone = narrative_data['tone']
        temp_story.story_metadata = {
            "pattern_id": pattern.id,
            "pattern_type": pattern.pattern_type,
            "pattern_frequency": pattern.frequency,
            "generated_at": datetime.utcnow().isoformat(),
            "generation_method": narrative_data['method'],
            "source": "pattern_based_ai"
        }
        temp_story.generation_source = 'ai_pattern_based'

        db.flush()

        logger.info(f"Generated AI story '{narrative_data['title']}' from pattern {pattern.id} with {len(images)} images (method: {narrative_data['method']})")

        return temp_story

    except Exception as e:
        logger.error(f"Error generating story from pattern {pattern.id}: {str(e)}")
        db.rollback()
        return None


@router.post("/generate", response_model=StoryGenerationResponse)
async def generate_stories(
    request: StoryGenerationRequest,
    db: Session = Depends(get_db)
):
    """
    Generate stories from detected patterns
    """
    # Validate user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {request.user_id} not found"
        )

    stories_generated = []

    try:
        # If specific pattern_id provided, generate story for that pattern
        if request.pattern_id:
            pattern = db.query(Pattern).filter(
                Pattern.id == request.pattern_id,
                Pattern.user_id == request.user_id
            ).first()

            if not pattern:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pattern {request.pattern_id} not found"
                )

            # For now, skip duplicate check due to JSON query complexity
            # TODO: Add proper duplicate check in future
            if not request.force_regenerate:
                # Check if we should skip generating if story already exists
                # For MVP, we'll just generate
                pass

            story = generate_story_from_pattern(db, pattern, request.user_id)
            if story:
                stories_generated.append(story)

        else:
            # Generate stories for all patterns
            patterns = db.query(Pattern).filter(
                Pattern.user_id == request.user_id
            ).all()

            if not patterns:
                logger.warning(f"No patterns found for user {request.user_id}")
                return StoryGenerationResponse(
                    success=False,
                    message="No patterns found. Please detect patterns first before generating stories.",
                    stories_generated=0,
                    stories=[]
                )

            logger.info(f"Generating stories for {len(patterns)} patterns")

            for pattern in patterns:
                # Skip duplicate check for MVP
                try:
                    logger.info(f"Processing pattern {pattern.id}: {pattern.description}")
                    story = generate_story_from_pattern(db, pattern, request.user_id)
                    if story:
                        stories_generated.append(story)
                        logger.info(f"Successfully generated story for pattern {pattern.id}")
                    else:
                        logger.warning(f"generate_story_from_pattern returned None for pattern {pattern.id}")
                except Exception as e:
                    logger.error(f"Exception generating story for pattern {pattern.id}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue

        # Commit all changes
        db.commit()

        # Refresh and add image counts
        for story in stories_generated:
            db.refresh(story)
            image_count = db.query(func.count(StoryImage.id)).filter(
                StoryImage.story_id == story.id
            ).scalar()
            story.image_count = image_count

        return StoryGenerationResponse(
            success=True,
            message=f"Generated {len(stories_generated)} stories",
            stories_generated=len(stories_generated),
            stories=stories_generated
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating stories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate stories: {str(e)}"
        )


@router.get("/", response_model=List[StoryResponse])
async def get_stories(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all stories for a user
    """
    stories = db.query(Story).filter(Story.user_id == user_id).all()

    # Add image counts - use photo_count if available (for AI story arcs), otherwise count StoryImage entries
    for story in stories:
        if story.photo_count is not None and story.photo_count > 0:
            # Use stored photo_count (for AI-generated story arcs)
            story.image_count = story.photo_count
        else:
            # Query StoryImage table (for pattern-based stories)
            image_count = db.query(func.count(StoryImage.id)).filter(
                StoryImage.story_id == story.id
            ).scalar()
            story.image_count = image_count

    return stories


@router.get("/{story_id}", response_model=StoryWithImagesResponse)
async def get_story_details(
    story_id: int,
    db: Session = Depends(get_db)
):
    """
    Get story details with all images
    """
    story = db.query(Story).filter(Story.id == story_id).first()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story {story_id} not found"
        )

    # Get all images for this story, ordered by sequence
    story_images = db.query(StoryImage).filter(
        StoryImage.story_id == story_id
    ).order_by(StoryImage.sequence_order).all()

    image_ids = [si.image_id for si in story_images]
    images = db.query(Image).filter(Image.id.in_(image_ids)).all()

    # Maintain order
    images_dict = {img.id: img for img in images}
    ordered_images = [images_dict[img_id] for img_id in image_ids if img_id in images_dict]

    # Create response
    story.images = ordered_images
    story.image_count = len(ordered_images)

    return story


@router.put("/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: int,
    story_update: StoryUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a story (edit title or content)
    """
    story = db.query(Story).filter(Story.id == story_id).first()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story {story_id} not found"
        )

    # Update fields
    if story_update.title is not None:
        story.title = story_update.title
    if story_update.description is not None:
        story.description = story_update.description
    if story_update.story_metadata is not None:
        story.story_metadata = story_update.story_metadata

    story.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(story)

    # Add image count
    image_count = db.query(func.count(StoryImage.id)).filter(
        StoryImage.story_id == story.id
    ).scalar()
    story.image_count = image_count

    return story


@router.delete("/{story_id}")
async def delete_story(
    story_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a story and all related data
    """
    from app.models import StoryEmotion

    story = db.query(Story).filter(Story.id == story_id).first()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story {story_id} not found"
        )

    # Delete related story emotions first
    db.query(StoryEmotion).filter(StoryEmotion.story_id == story_id).delete()

    # Now delete the story (cascade will handle story_images and story_sections)
    db.delete(story)
    db.commit()

    return {"success": True, "message": "Story deleted successfully"}


@router.post("/", response_model=StoryResponse)
async def create_custom_story(
    story: StoryCreate,
    db: Session = Depends(get_db)
):
    """
    Create a custom story manually
    """
    # Validate user
    user = db.query(User).filter(User.id == story.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {story.user_id} not found"
        )

    # Create story
    new_story = Story(
        user_id=story.user_id,
        title=story.title,
        description=story.description,
        story_metadata=story.story_metadata or {"source": "manual"},
        auto_generated=False,
        generation_source='manual'
    )

    db.add(new_story)
    db.flush()

    # Link images if provided
    if story.image_ids:
        for idx, image_id in enumerate(story.image_ids):
            story_image = StoryImage(
                story_id=new_story.id,
                image_id=image_id,
                sequence_order=idx
            )
            db.add(story_image)

    db.commit()
    db.refresh(new_story)

    # Add image count
    new_story.image_count = len(story.image_ids) if story.image_ids else 0

    return new_story


@router.delete("/delete-all")
async def delete_all_stories(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Delete ALL stories for a user"""
    story_count = db.query(Story).filter(Story.user_id == user_id).delete()
    db.commit()
    return {
        "message": f"Deleted {story_count} stories",
        "deleted_count": story_count
    }

