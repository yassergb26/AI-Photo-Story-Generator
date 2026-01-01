"""
Photo upload and retrieval endpoints
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

from app.database import get_db
from app.models import Image, Location, BackgroundTask, ImageEmotion, Emotion, Category, ImageCategory
from app.schemas import ImageUploadResponse, ImageDetailResponse, UploadResponse
from app.config import settings
from app.utils.file_handler import save_upload_file, is_allowed_file
from app.utils.exif_extractor import extract_exif_data, get_capture_date, get_gps_coordinates
from app.utils.duplicate_detection import calculate_file_hash, check_duplicate_image
from app.thumbnails import generate_thumbnail, delete_thumbnail
# from app.tasks import classify_images_batch  # Commented out - requires Redis/Celery
from app.redis_client import cache_api_response, get_api_response, invalidate_user_cache
from app.services import classify_image_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/photos", tags=["photos"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/upload", response_model=UploadResponse)
@limiter.limit("10/minute")  # 10 uploads per minute per IP
async def upload_images(
    request: Request,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload multiple images with automatic EXIF extraction and async classification

    UPDATED: Now generates thumbnails immediately and queues classification as async task

    Args:
        files: List of image files to upload
        db: Database session

    Returns:
        UploadResponse with success status, uploaded image IDs, and async task ID
    """
    uploaded_images = []
    image_ids = []
    duplicate_files = []

    # For now, use a default user_id (we'll add auth later)
    user_id = 1

    for upload_file in files:
        try:
            # Validate file type
            if not is_allowed_file(upload_file.filename, settings.get_allowed_extensions()):
                logger.warning(f"Rejected file with invalid extension: {upload_file.filename}")
                continue

            # Save file to disk
            file_path, file_size = await save_upload_file(
                upload_file,
                settings.UPLOAD_DIR,
                settings.MAX_UPLOAD_SIZE
            )

            # Calculate file hash for duplicate detection
            file_hash = calculate_file_hash(file_path)

            # Check for duplicate
            duplicate = check_duplicate_image(db, user_id, file_hash)
            if duplicate:
                logger.info(f"Duplicate image detected: {upload_file.filename} (original: {duplicate.filename})")
                duplicate_files.append(upload_file.filename)
                # Clean up uploaded file
                import os
                os.remove(file_path)
                # Skip this file
                continue

            # Generate thumbnail immediately (200x200px) - optimized
            thumbnail_path = None
            try:
                thumbnail_path = generate_thumbnail(file_path)
                logger.info(f"Generated thumbnail: {thumbnail_path}")
            except Exception as e:
                logger.warning(f"Failed to generate thumbnail (non-critical): {e}")
                # Continue without thumbnail - it's not critical

            # Extract EXIF metadata
            exif_data = extract_exif_data(file_path)
            capture_date = get_capture_date(exif_data)
            gps_coords = get_gps_coordinates(exif_data)

            # Create image record with new fields (including file_hash)
            db_image = Image(
                user_id=user_id,
                filename=upload_file.filename,
                file_path=file_path,
                thumbnail_path=thumbnail_path,
                file_size=file_size,
                file_hash=file_hash,  # NEW: Store hash
                capture_date=capture_date,
                exif_data=exif_data,
                processed=False,
                embedding_cached=False,
                is_duplicate=False
            )

            db.add(db_image)
            db.flush()  # Get image ID before committing

            # Create location record if GPS data exists
            if gps_coords:
                latitude, longitude = gps_coords
                db_location = Location(
                    image_id=db_image.id,
                    latitude=latitude,
                    longitude=longitude
                )
                db.add(db_location)

            uploaded_images.append(db_image)
            image_ids.append(db_image.id)

            # DISABLED: Auto-processing now handled by Auto Mode button
            # Classification and emotion detection will be triggered manually via /api/chapters/auto-generate

            logger.info(f"Uploaded image {db_image.id}: {upload_file.filename}")

        except Exception as e:
            logger.error(f"Error uploading {upload_file.filename}: {str(e)}")
            continue

    # Commit all changes
    db.commit()

    # Invalidate user cache
    invalidate_user_cache(user_id)

    # Queue async classification task for all uploaded images (if Redis/Celery available)
    # NOTE: Classification is disabled if Redis/Celery is not running
    # To enable: uncomment import at top and start Redis + Celery worker
    task_id = None
    # Uncomment below when Redis/Celery is running:
    # if image_ids:
    #     try:
    #         task = classify_images_batch.delay(image_ids, user_id)
    #         task_id = task.id
    #         bg_task = BackgroundTask(
    #             user_id=user_id,
    #             task_type='classification',
    #             task_id=task.id,
    #             status='pending',
    #             progress=0
    #         )
    #         db.add(bg_task)
    #         db.commit()
    #         logger.info(f"Queued classification task {task.id} for {len(image_ids)} images")
    #     except Exception as e:
    #         logger.warning(f"Skipping classification: {type(e).__name__}")

    # Build appropriate message
    message_parts = []
    if len(uploaded_images) > 0:
        message_parts.append(f"Successfully uploaded {len(uploaded_images)} image(s)")
    if duplicate_files:
        duplicate_names = ", ".join(duplicate_files)
        message_parts.append(f"{len(duplicate_files)} duplicate(s) skipped: {duplicate_names} (already exists in photo gallery)")

    final_message = ". ".join(message_parts) if message_parts else "No images uploaded"

    return UploadResponse(
        success=len(uploaded_images) > 0,
        uploaded_count=len(uploaded_images),
        image_ids=image_ids,
        message=final_message
    )


@router.get("")
def get_images(
    skip: int = 0,
    limit: int = 10000,
    db: Session = Depends(get_db)
):
    """
    Get list of uploaded images with pagination and caching

    UPDATED: Now includes total count, uses Redis cache, and returns thumbnails

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return (max 10000)
        db: Database session

    Returns:
        Paginated response with total count and images
    """
    # For now, get images for default user
    user_id = 1

    # Enforce max limit
    limit = min(limit, 10000)

    # Check cache first
    cache_key = f"api:images:user:{user_id}:skip:{skip}:limit:{limit}"
    cached_response = get_api_response(cache_key)
    if cached_response:
        logger.info(f"Cache hit for images list: {cache_key}")
        return cached_response

    # Get total count
    total = db.query(func.count(Image.id)).filter(
        Image.user_id == user_id
    ).scalar()

    # Get paginated images
    images = db.query(Image)\
        .filter(Image.user_id == user_id)\
        .order_by(Image.upload_date.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()

    response = {
        "total": total,
        "skip": skip,
        "limit": limit,
        "count": len(images),
        "images": [
            {
                "id": img.id,
                "filename": img.filename,
                "file_path": img.file_path,
                "thumbnail_path": img.thumbnail_path,
                "file_size": img.file_size,
                "upload_date": img.upload_date.isoformat() if img.upload_date else None,
                "capture_date": img.capture_date.isoformat() if img.capture_date else None,
                "processed": img.processed,
                "embedding_cached": img.embedding_cached
            }
            for img in images
        ]
    }

    # Cache for 5 minutes
    cache_api_response(cache_key, response, expiry=300)

    return response


@router.get("/{image_id}", response_model=ImageDetailResponse)
def get_image(
    image_id: int,
    db: Session = Depends(get_db)
):
    """
    Get specific image details

    Args:
        image_id: ID of the image
        db: Database session

    Returns:
        Image details with EXIF and location data
    """
    image = db.query(Image).filter(Image.id == image_id).first()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with ID {image_id} not found"
        )

    return image


@router.get("/{image_id}/location")
def get_image_location(
    image_id: int,
    db: Session = Depends(get_db)
):
    """
    Get location data for a specific image

    Args:
        image_id: ID of the image
        db: Database session

    Returns:
        Image with location data
    """
    image = db.query(Image).filter(Image.id == image_id).first()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with ID {image_id} not found"
        )

    return {
        "id": image.id,
        "filename": image.filename,
        "file_path": image.file_path,
        "location": image.location
    }


@router.delete("/delete-all")
def delete_all_photos(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete ALL photos for a user (with confirmation)

    WARNING: This will delete all photos, thumbnails, and associated data!
    """
    from app.models import StoryImage, PatternImage, ImageCategory, ImageEmotion, LifeEventImage
    from app.utils.file_handler import delete_file
    import os

    # Get all images for user
    images = db.query(Image).filter(Image.user_id == user_id).all()

    if not images:
        return {"message": "No photos to delete", "deleted_count": 0}

    deleted_count = 0
    for image in images:
        try:
            # Delete physical files
            if image.file_path and os.path.exists(image.file_path):
                delete_file(image.file_path)

            # Delete thumbnail
            delete_thumbnail(image.file_path)

            # Delete junction table entries
            db.query(StoryImage).filter(StoryImage.image_id == image.id).delete()
            db.query(PatternImage).filter(PatternImage.image_id == image.id).delete()
            db.query(ImageCategory).filter(ImageCategory.image_id == image.id).delete()
            db.query(ImageEmotion).filter(ImageEmotion.image_id == image.id).delete()
            db.query(LifeEventImage).filter(LifeEventImage.image_id == image.id).delete()

            # Delete image record
            db.delete(image)
            deleted_count += 1

        except Exception as e:
            logger.error(f"Error deleting image {image.id}: {e}")
            continue

    db.commit()

    # Invalidate cache
    invalidate_user_cache(user_id)

    return {
        "message": f"Successfully deleted {deleted_count} photos and their data",
        "deleted_count": deleted_count
    }


@router.delete("/{image_id}")
def delete_image(
    image_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete an image

    UPDATED: Now also deletes thumbnails, junction table rows, and invalidates cache

    Args:
        image_id: ID of the image to delete
        db: Database session

    Returns:
        Success message
    """
    from app.models import StoryImage, PatternImage, ImageCategory, ImageEmotion, LifeEventImage
    from app.utils.file_handler import delete_file

    image = db.query(Image).filter(Image.id == image_id).first()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with ID {image_id} not found"
        )

    user_id = image.user_id

    try:
        # Delete all junction table rows first (to avoid foreign key violations)
        db.query(StoryImage).filter(StoryImage.image_id == image_id).delete()
        db.query(PatternImage).filter(PatternImage.image_id == image_id).delete()
        db.query(ImageCategory).filter(ImageCategory.image_id == image_id).delete()
        db.query(ImageEmotion).filter(ImageEmotion.image_id == image_id).delete()
        db.query(LifeEventImage).filter(LifeEventImage.image_id == image_id).delete()

        # Delete files from disk
        delete_file(image.file_path)

        # Delete thumbnail if exists
        if image.thumbnail_path:
            try:
                delete_thumbnail(image.thumbnail_path)
            except Exception as e:
                logger.error(f"Failed to delete thumbnail: {e}")

        # Delete image from database (Location will cascade automatically)
        db.delete(image)
        db.commit()

        # Invalidate user cache
        invalidate_user_cache(user_id)

        logger.info(f"Successfully deleted image {image_id}")
        return {"message": f"Image {image_id} deleted successfully"}

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting image {image_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete image: {str(e)}"
        )


@router.get("/tasks/{task_id}")
def get_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get status of a background classification task

    NEW: Check progress of async image classification

    Args:
        task_id: Celery task ID
        db: Database session

    Returns:
        Task status with progress percentage
    """
    task = db.query(BackgroundTask).filter(BackgroundTask.task_id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )

    return {
        "task_id": task.task_id,
        "task_type": task.task_type,
        "status": task.status,
        "progress": task.progress,
        "result": task.result,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None
    }
