"""
Emotion detection and aggregation endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database import get_db
from app.models import Image, Emotion, ImageEmotion, Story, StoryEmotion
from app.services.emotion_detection import detect_emotions, get_dominant_emotion, aggregate_image_emotions
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/emotions", tags=["emotions"])


# Schemas
class EmotionResponse(BaseModel):
    id: int
    name: str
    description: str | None
    color_code: str | None

    class Config:
        from_attributes = True


class ImageEmotionResponse(BaseModel):
    emotion: str
    confidence: float
    face_count: int | None


class StoryEmotionResponse(BaseModel):
    emotion: str
    percentage: float
    image_count: int


@router.post("/detect/{image_id}")
async def detect_image_emotions(
    image_id: int,
    db: Session = Depends(get_db)
):
    """
    Detect emotions in a specific image

    Analyzes faces in the image and detects emotions.
    Stores results in image_emotions table.
    """
    try:
        # Get image
        image = db.query(Image).filter(Image.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")

        # Detect emotions
        logger.info(f"Detecting emotions for image {image_id}")
        # Convert URL path to file system path
        file_path = image.file_path.lstrip('/')
        emotions_data = detect_emotions(file_path)

        if not emotions_data:
            return {
                "success": False,
                "message": "No faces detected in image",
                "image_id": image_id,
                "emotions": []
            }

        # Get dominant emotion
        dominant = get_dominant_emotion(emotions_data)

        # Clear existing emotions for this image
        db.query(ImageEmotion).filter(ImageEmotion.image_id == image_id).delete()

        # Store emotions in database
        stored_emotions = []

        for emotion_data in emotions_data:
            # Get emotion name from HSEmotion (already capitalized correctly)
            # HSEmotion returns: Anger, Contempt, Disgust, Fear, Happiness, Neutral, Sadness, Surprise
            emotion_name = emotion_data['emotion']

            emotion_obj = db.query(Emotion).filter(Emotion.name == emotion_name).first()

            if not emotion_obj:
                logger.warning(f"Emotion '{emotion_name}' not found in database")
                continue

            # Create image_emotion record
            image_emotion = ImageEmotion(
                image_id=image_id,
                emotion_id=emotion_obj.id,
                confidence_score=float(emotion_data['confidence']),
                face_count=1,
                dominant_emotion=(emotion_name == dominant['emotion'])
            )
            db.add(image_emotion)
            stored_emotions.append({
                "emotion": emotion_name,
                "confidence": float(emotion_data['confidence'])
            })

        db.commit()

        logger.info(f"Stored {len(stored_emotions)} emotions for image {image_id}")

        return {
            "success": True,
            "message": f"Detected {len(emotions_data)} face(s) with emotions",
            "image_id": image_id,
            "emotions": stored_emotions,
            "dominant_emotion": dominant
        }

    except Exception as e:
        logger.error(f"Error detecting emotions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-batch")
async def detect_batch_emotions(
    image_ids: List[int] | None = None,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """
    Detect emotions for multiple images

    If image_ids not provided, processes all unprocessed images for user
    """
    try:
        # Get images to process
        if image_ids:
            images = db.query(Image).filter(Image.id.in_(image_ids)).all()
        else:
            # Get images without emotions
            images = db.query(Image)\
                .outerjoin(ImageEmotion)\
                .filter(Image.user_id == user_id)\
                .filter(ImageEmotion.id == None)\
                .all()

        if not images:
            return {
                "success": True,
                "message": "No images to process",
                "processed_count": 0
            }

        # Process each image
        processed_count = 0
        failed_count = 0

        for image in images:
            try:
                emotions_data = detect_emotions(image.file_path)

                if emotions_data:
                    dominant = get_dominant_emotion(emotions_data)

                    # Clear existing emotions
                    db.query(ImageEmotion).filter(ImageEmotion.image_id == image.id).delete()

                    # Store emotions
                    for emotion_data in emotions_data:
                        emotion_name = emotion_data['emotion']
                        emotion_obj = db.query(Emotion).filter(Emotion.name == emotion_name).first()

                        if emotion_obj:
                            image_emotion = ImageEmotion(
                                image_id=image.id,
                                emotion_id=emotion_obj.id,
                                confidence_score=float(emotion_data['confidence']),
                                face_count=1,
                                dominant_emotion=(emotion_name == dominant['emotion'])
                            )
                            db.add(image_emotion)

                    processed_count += 1

            except Exception as e:
                logger.error(f"Error processing image {image.id}: {str(e)}")
                failed_count += 1

        db.commit()

        return {
            "success": True,
            "message": f"Processed {processed_count} images",
            "processed_count": processed_count,
            "failed_count": failed_count,
            "total_images": len(images)
        }

    except Exception as e:
        logger.error(f"Error in batch detection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/image/{image_id}")
async def get_image_emotions(
    image_id: int,
    db: Session = Depends(get_db)
):
    """Get emotions for a specific image"""
    try:
        # Get image with emotions
        image = db.query(Image).filter(Image.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")

        # Get emotions
        image_emotions = db.query(ImageEmotion, Emotion)\
            .join(Emotion)\
            .filter(ImageEmotion.image_id == image_id)\
            .all()

        emotions_list = []
        for img_emotion, emotion in image_emotions:
            emotions_list.append({
                "emotion": emotion.name,
                "confidence": float(img_emotion.confidence_score),
                "dominant": img_emotion.dominant_emotion
            })

        return {
            "image_id": image_id,
            "emotions": emotions_list
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image emotions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/story/{story_id}")
async def get_story_emotions(
    story_id: int,
    db: Session = Depends(get_db)
):
    """Get aggregated emotions for a story"""
    try:
        # Get story
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        # Get story emotions
        story_emotions = db.query(StoryEmotion, Emotion)\
            .join(Emotion)\
            .filter(StoryEmotion.story_id == story_id)\
            .order_by(StoryEmotion.percentage.desc())\
            .all()

        emotions_list = []
        for story_emotion, emotion in story_emotions:
            emotions_list.append({
                "emotion": emotion.name,
                "percentage": float(story_emotion.percentage),
                "image_count": story_emotion.image_count,
                "color_code": emotion.color_code
            })

        return {
            "story_id": story_id,
            "emotions": emotions_list
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting story emotions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/story/{story_id}/aggregate")
async def aggregate_story_emotions(
    story_id: int,
    db: Session = Depends(get_db)
):
    """
    Aggregate emotions from all images in a story

    Calculates emotion percentages and stores in story_emotions table
    """
    try:
        # Get story with images
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        # Get all images in story with their dominant emotions
        from app.models import StoryImage

        story_images = db.query(StoryImage).filter(StoryImage.story_id == story_id).all()

        if not story_images:
            return {
                "success": False,
                "message": "No images in story",
                "story_id": story_id
            }

        # Get dominant emotions for each image
        dominant_emotions = []
        for story_image in story_images:
            dominant = db.query(ImageEmotion, Emotion)\
                .join(Emotion)\
                .filter(ImageEmotion.image_id == story_image.image_id)\
                .filter(ImageEmotion.dominant_emotion == True)\
                .first()

            if dominant:
                img_emotion, emotion = dominant
                dominant_emotions.append({
                    "emotion": emotion.name,
                    "confidence": float(img_emotion.confidence_score)
                })

        if not dominant_emotions:
            return {
                "success": False,
                "message": "No emotions detected in story images",
                "story_id": story_id
            }

        # Calculate percentages
        emotion_percentages = aggregate_image_emotions(dominant_emotions)

        # Clear existing story emotions
        db.query(StoryEmotion).filter(StoryEmotion.story_id == story_id).delete()

        # Store new aggregations
        for emotion_name, percentage in emotion_percentages.items():
            emotion_obj = db.query(Emotion).filter(Emotion.name == emotion_name).first()

            if emotion_obj:
                # Count images with this emotion
                image_count = sum(1 for e in dominant_emotions if e['emotion'] == emotion_name)

                story_emotion = StoryEmotion(
                    story_id=story_id,
                    emotion_id=emotion_obj.id,
                    percentage=percentage,
                    image_count=image_count
                )
                db.add(story_emotion)

        # Update story narrative tone based on dominant emotion
        if emotion_percentages:
            dominant_emotion = max(emotion_percentages, key=emotion_percentages.get)

            # Map emotion to narrative tone
            tone_mapping = {
                "happy": "joyful",
                "excited": "celebratory",
                "love": "joyful",
                "joy": "joyful",
                "sad": "reflective",
                "surprised": "celebratory",
                "neutral": "reflective",
                "reflective": "reflective"
            }

            story.narrative_tone = tone_mapping.get(dominant_emotion, "joyful")

        db.commit()

        return {
            "success": True,
            "message": "Story emotions aggregated successfully",
            "story_id": story_id,
            "emotions": emotion_percentages,
            "narrative_tone": story.narrative_tone
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error aggregating story emotions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_all_emotions(db: Session = Depends(get_db)):
    """Get all available emotions"""
    try:
        emotions = db.query(Emotion).all()
        return [EmotionResponse.model_validate(e) for e in emotions]

    except Exception as e:
        logger.error(f"Error getting emotions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
