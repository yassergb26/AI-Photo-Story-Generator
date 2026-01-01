"""
AI Narrative Generation endpoints
Generates and regenerates story narratives using LLM
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime

from app.database import get_db
from app.models import Story, StoryImage, StoryEmotion, Emotion, Category, ImageCategory
from app.services.ai_narrative import generate_narrative
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/narratives", tags=["narratives"])


# Schemas
class NarrativeRequest(BaseModel):
    narrative_tone: str = "joyful"  # joyful, nostalgic, celebratory, reflective
    use_llm: bool = True  # Whether to use LLM or templates


class NarrativeResponse(BaseModel):
    story_id: int
    title: str
    description: str
    narrative_tone: str
    generation_method: str  # llm_generated or template_based


@router.post("/{story_id}/generate", response_model=NarrativeResponse)
async def generate_story_narrative(
    story_id: int,
    request: NarrativeRequest = NarrativeRequest(),
    db: Session = Depends(get_db)
):
    """
    Generate AI narrative for a story

    Uses LLM to create creative title and description based on:
    - Images in story
    - Detected emotions
    - Categories and themes
    - Dates and locations
    """
    try:
        # Get story
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        # Get story images
        story_images = db.query(StoryImage).filter(StoryImage.story_id == story_id).all()
        image_count = len(story_images)

        # Get emotions for story
        story_emotions = db.query(StoryEmotion, Emotion)\
            .join(Emotion)\
            .filter(StoryEmotion.story_id == story_id)\
            .order_by(StoryEmotion.percentage.desc())\
            .all()

        emotions_dict = {}
        for story_emotion, emotion in story_emotions:
            emotions_dict[emotion.name] = float(story_emotion.percentage)

        # Get categories from images
        from app.models import Image
        image_ids = [si.image_id for si in story_images]
        categories_query = db.query(Category.name, Category.id)\
            .join(ImageCategory)\
            .join(Image)\
            .filter(Image.id.in_(image_ids))\
            .distinct()\
            .limit(5)\
            .all()

        categories = [cat.name for cat in categories_query]

        # Get location from story_metadata if available
        location = None
        if story.story_metadata and isinstance(story.story_metadata, dict):
            location = story.story_metadata.get('location')

        # Build metadata for narrative generation
        story_metadata = {
            "image_count": image_count,
            "categories": categories,
            "emotions": emotions_dict,
            "start_date": story.start_date,
            "end_date": story.end_date,
            "location": location,
            "category": categories[0] if categories else "photos",
            "event_name": story.story_type or "moments"
        }

        # Determine pattern type from story_metadata
        pattern_type = "visual"
        if story.story_metadata and isinstance(story.story_metadata, dict):
            pattern_type = story.story_metadata.get('pattern_type', 'visual')

        # Generate narrative
        logger.info(f"Generating narrative for story {story_id} (tone: {request.narrative_tone})")

        narrative_data = generate_narrative(
            story_metadata=story_metadata,
            narrative_tone=request.narrative_tone,
            pattern_type=pattern_type,
            use_llm=request.use_llm
        )

        # Update story with new narrative
        story.title = narrative_data['title']
        story.description = narrative_data['description']
        story.narrative_tone = narrative_data['tone']

        # Update story_metadata to track generation method
        if not story.story_metadata:
            story.story_metadata = {}

        story.story_metadata['generation_method'] = narrative_data['method']
        story.story_metadata['generated_at'] = datetime.now().isoformat()

        db.commit()

        logger.info(f"Narrative generated: {narrative_data['title']}")

        return NarrativeResponse(
            story_id=story_id,
            title=narrative_data['title'],
            description=narrative_data['description'],
            narrative_tone=narrative_data['tone'],
            generation_method=narrative_data['method']
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating narrative: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{story_id}/regenerate", response_model=NarrativeResponse)
async def regenerate_story_narrative(
    story_id: int,
    narrative_tone: str = Query("joyful", description="Narrative tone"),
    use_llm: bool = Query(True, description="Use LLM generation"),
    db: Session = Depends(get_db)
):
    """
    Regenerate narrative with different tone or method

    Allows user to regenerate the same story with:
    - Different narrative tone
    - Different generation method (LLM vs template)
    """
    request = NarrativeRequest(narrative_tone=narrative_tone, use_llm=use_llm)
    return await generate_story_narrative(story_id, request, db)


@router.post("/generate-batch")
async def generate_batch_narratives(
    story_ids: Optional[List[int]] = None,
    user_id: int = 1,
    narrative_tone: str = "joyful",
    use_llm: bool = True,
    db: Session = Depends(get_db)
):
    """
    Generate narratives for multiple stories

    If story_ids not provided, processes all stories for user
    """
    try:
        # Get stories to process
        if story_ids:
            stories = db.query(Story).filter(Story.id.in_(story_ids)).all()
        else:
            stories = db.query(Story).filter(Story.user_id == user_id).all()

        if not stories:
            return {
                "success": True,
                "message": "No stories to process",
                "processed_count": 0
            }

        # Process each story
        processed_count = 0
        failed_count = 0
        results = []

        for story in stories:
            try:
                # Generate narrative (reuse the endpoint logic)
                request = NarrativeRequest(narrative_tone=narrative_tone, use_llm=use_llm)

                result = await generate_story_narrative(story.id, request, db)

                processed_count += 1
                results.append({
                    "story_id": story.id,
                    "title": result.title,
                    "method": result.generation_method
                })

            except Exception as e:
                logger.error(f"Error processing story {story.id}: {str(e)}")
                failed_count += 1

        return {
            "success": True,
            "message": f"Processed {processed_count} stories",
            "processed_count": processed_count,
            "failed_count": failed_count,
            "total_stories": len(stories),
            "results": results
        }

    except Exception as e:
        logger.error(f"Error in batch generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{story_id}/edit")
async def edit_narrative(
    story_id: int,
    title: str,
    description: str,
    db: Session = Depends(get_db)
):
    """
    Manually edit story narrative

    Allows user to override AI-generated narrative
    """
    try:
        # Get story
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        # Update narrative
        story.title = title
        story.description = description

        # Mark as manually edited
        if not story.story_metadata:
            story.story_metadata = {}

        story.story_metadata['manually_edited'] = True
        story.story_metadata['edited_at'] = datetime.now().isoformat()

        db.commit()

        return {
            "success": True,
            "message": "Narrative updated successfully",
            "story_id": story_id,
            "title": title,
            "description": description
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error editing narrative: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{story_id}/preview")
async def preview_narrative(
    story_id: int,
    narrative_tone: str = Query("joyful", description="Narrative tone to preview"),
    use_llm: bool = Query(True, description="Use LLM generation"),
    db: Session = Depends(get_db)
):
    """
    Preview narrative without saving

    Generates a narrative preview for the user to review before saving
    """
    try:
        # Get story
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        # Get story metadata (same logic as generate)
        story_images = db.query(StoryImage).filter(StoryImage.story_id == story_id).all()
        image_count = len(story_images)

        story_emotions = db.query(StoryEmotion, Emotion)\
            .join(Emotion)\
            .filter(StoryEmotion.story_id == story_id)\
            .order_by(StoryEmotion.percentage.desc())\
            .all()

        emotions_dict = {}
        for story_emotion, emotion in story_emotions:
            emotions_dict[emotion.name] = float(story_emotion.percentage)

        from app.models import Image
        image_ids = [si.image_id for si in story_images]
        categories_query = db.query(Category.name)\
            .join(ImageCategory)\
            .join(Image)\
            .filter(Image.id.in_(image_ids))\
            .distinct()\
            .limit(5)\
            .all()

        categories = [cat.name for cat in categories_query]

        location = None
        if story.story_metadata and isinstance(story.story_metadata, dict):
            location = story.story_metadata.get('location')

        story_metadata = {
            "image_count": image_count,
            "categories": categories,
            "emotions": emotions_dict,
            "start_date": story.start_date,
            "end_date": story.end_date,
            "location": location,
            "category": categories[0] if categories else "photos",
            "event_name": story.story_type or "moments"
        }

        pattern_type = "visual"
        if story.story_metadata and isinstance(story.story_metadata, dict):
            pattern_type = story.story_metadata.get('pattern_type', 'visual')

        # Generate preview (don't save)
        narrative_data = generate_narrative(
            story_metadata=story_metadata,
            narrative_tone=narrative_tone,
            pattern_type=pattern_type,
            use_llm=use_llm
        )

        return {
            "story_id": story_id,
            "preview": narrative_data,
            "current_title": story.title,
            "current_description": story.description
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing narrative: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
