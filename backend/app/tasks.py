"""
Celery Tasks for Async Processing
"""
from celery import Task
from app.celery_app import celery_app
from app.database import SessionLocal
from typing import List
import logging

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management"""
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(base=DatabaseTask, bind=True, name='app.tasks.classify_image_task')
def classify_image_task(self, image_id: int) -> dict:
    """
    Async task to classify a single image

    Args:
        image_id: Image ID to classify

    Returns:
        dict with classification results
    """
    from app.models import Image, Category, ImageCategory
    from app.services.clip_classifier import classify_image_file

    try:
        # Update task state
        self.update_state(state='PROCESSING', meta={'image_id': image_id, 'progress': 0})

        # Get image
        image = self.db.query(Image).filter(Image.id == image_id).first()
        if not image:
            raise ValueError(f"Image {image_id} not found")

        # Classify image
        self.update_state(state='PROCESSING', meta={'image_id': image_id, 'progress': 50})
        results = classify_image_file(image.file_path, threshold=0.15, top_k=5)

        # Save classifications
        for result in results:
            category = self.db.query(Category).filter(Category.name == result["category"]).first()
            if not category:
                category = Category(name=result["category"], description=f"Auto-generated: {result['category']}")
                self.db.add(category)
                self.db.flush()

            image_category = ImageCategory(
                image_id=image.id,
                category_id=category.id,
                confidence_score=result["confidence"]
            )
            self.db.add(image_category)

        self.db.commit()

        logger.info(f"Classified image {image_id}: {len(results)} categories")

        return {
            'image_id': image_id,
            'categories_count': len(results),
            'top_category': results[0]['category'] if results else None,
            'status': 'completed'
        }

    except Exception as e:
        logger.error(f"Failed to classify image {image_id}: {e}")
        self.db.rollback()
        raise


@celery_app.task(base=DatabaseTask, bind=True, name='app.tasks.detect_emotions_task')
def detect_emotions_task(self, image_id: int) -> dict:
    """
    Async task to detect emotions in an image

    Args:
        image_id: Image ID to process

    Returns:
        dict with emotion detection results
    """
    from app.models import Image, Emotion, ImageEmotion
    from app.services.clip_classifier import detect_emotions, get_dominant_emotion

    try:
        self.update_state(state='PROCESSING', meta={'image_id': image_id, 'progress': 0})

        # Get image
        image = self.db.query(Image).filter(Image.id == image_id).first()
        if not image:
            raise ValueError(f"Image {image_id} not found")

        # Detect emotions
        self.update_state(state='PROCESSING', meta={'image_id': image_id, 'progress': 50})
        emotions_data = detect_emotions(image.file_path)

        if not emotions_data:
            return {'image_id': image_id, 'emotions_count': 0, 'status': 'no_faces_detected'}

        dominant = get_dominant_emotion(emotions_data)

        # Save emotions
        for emotion_data in emotions_data:
            emotion_name = emotion_data['emotion']
            emotion_obj = self.db.query(Emotion).filter(Emotion.name == emotion_name).first()

            if emotion_obj:
                image_emotion = ImageEmotion(
                    image_id=image.id,
                    emotion_id=emotion_obj.id,
                    confidence_score=emotion_data['confidence'],
                    face_count=1,
                    dominant_emotion=(emotion_name == dominant['emotion'])
                )
                self.db.add(image_emotion)

        self.db.commit()

        logger.info(f"Detected emotions for image {image_id}: {len(emotions_data)} emotions")

        return {
            'image_id': image_id,
            'emotions_count': len(emotions_data),
            'dominant_emotion': dominant['emotion'] if dominant else None,
            'status': 'completed'
        }

    except Exception as e:
        logger.error(f"Failed to detect emotions for image {image_id}: {e}")
        self.db.rollback()
        raise


@celery_app.task(base=DatabaseTask, bind=True, name='app.tasks.process_image_batch')
def process_image_batch(self, image_ids: List[int]) -> dict:
    """
    Process a batch of images (classify + detect emotions)

    Args:
        image_ids: List of image IDs to process

    Returns:
        dict with batch processing results
    """
    try:
        total = len(image_ids)
        results = {
            'total': total,
            'processed': 0,
            'failed': 0,
            'image_results': []
        }

        for idx, image_id in enumerate(image_ids):
            try:
                # Update progress
                progress = int((idx / total) * 100)
                self.update_state(
                    state='PROCESSING',
                    meta={'progress': progress, 'current': idx + 1, 'total': total}
                )

                # Classify image
                classify_result = classify_image_task(image_id)

                # Detect emotions
                emotion_result = detect_emotions_task(image_id)

                results['processed'] += 1
                results['image_results'].append({
                    'image_id': image_id,
                    'classification': classify_result,
                    'emotions': emotion_result
                })

            except Exception as e:
                logger.error(f"Failed to process image {image_id}: {e}")
                results['failed'] += 1

        logger.info(f"Batch processing complete: {results['processed']}/{total} successful")

        return results

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise


@celery_app.task(base=DatabaseTask, bind=True, name='app.tasks.generate_story_arcs_task')
def generate_story_arcs_task(self, chapter_id: int) -> dict:
    """
    Async task to generate story arcs for a chapter

    Args:
        chapter_id: Chapter ID

    Returns:
        dict with story arc generation results
    """
    from app.services.story_arc_detector import detect_story_arcs_for_chapter

    try:
        self.update_state(state='PROCESSING', meta={'chapter_id': chapter_id, 'progress': 0})

        # Detect story arcs
        story_arcs = detect_story_arcs_for_chapter(chapter_id, self.db)

        logger.info(f"Generated {len(story_arcs)} story arcs for chapter {chapter_id}")

        return {
            'chapter_id': chapter_id,
            'story_arcs_count': len(story_arcs),
            'story_arc_ids': [arc.id for arc in story_arcs],
            'status': 'completed'
        }

    except Exception as e:
        logger.error(f"Failed to generate story arcs for chapter {chapter_id}: {e}")
        self.db.rollback()
        raise
