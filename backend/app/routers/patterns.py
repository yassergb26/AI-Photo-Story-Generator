"""
Pattern Detection & Temporal Grouping Router
Handles pattern detection (temporal, spatial, visual) and image grouping
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from app.database import get_db
from app.models import Pattern, PatternImage, Image, Location, User, Emotion, ImageEmotion
from app.schemas import (
    PatternResponse,
    PatternWithImagesResponse,
    PatternDetectionRequest,
    PatternDetectionResponse,
    ImageUploadResponse
)

router = APIRouter(prefix="/api/patterns", tags=["patterns"])
logger = logging.getLogger(__name__)


@router.post("/detect", response_model=PatternDetectionResponse)
async def detect_patterns(
    request: PatternDetectionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger pattern detection for a user's images
    - Temporal patterns (annual birthdays, monthly events)
    - Spatial patterns (GPS clustering)
    - Visual patterns (CLIP embedding clustering)
    """
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's images
        images = db.query(Image).filter(Image.user_id == request.user_id).all()
        if len(images) < 3:
            return PatternDetectionResponse(
                success=False,
                message="Need at least 3 images to detect patterns",
                patterns_detected=0,
                patterns=[]
            )

        detected_patterns = []

        # Detect patterns based on requested types
        if "temporal" in request.pattern_types:
            temporal_patterns = await detect_temporal_patterns(db, request.user_id, images)
            detected_patterns.extend(temporal_patterns)

        if "spatial" in request.pattern_types:
            spatial_patterns = await detect_spatial_patterns(db, request.user_id, images)
            detected_patterns.extend(spatial_patterns)

        if "visual" in request.pattern_types:
            visual_patterns = await detect_visual_patterns(db, request.user_id, images)
            detected_patterns.extend(visual_patterns)

        db.commit()

        # Convert to response format
        pattern_responses = []
        for pattern in detected_patterns:
            image_count = db.query(PatternImage).filter(
                PatternImage.pattern_id == pattern.id
            ).count()

            pattern_dict = {
                "id": pattern.id,
                "user_id": pattern.user_id,
                "pattern_type": pattern.pattern_type,
                "frequency": pattern.frequency,
                "description": pattern.description,
                "pattern_metadata": pattern.pattern_metadata,
                "confidence_score": float(pattern.confidence_score) if pattern.confidence_score else None,
                "detected_date": pattern.detected_date,
                "created_at": pattern.created_at,
                "image_count": image_count
            }
            pattern_responses.append(PatternResponse(**pattern_dict))

        return PatternDetectionResponse(
            success=True,
            message=f"Detected {len(detected_patterns)} patterns",
            patterns_detected=len(detected_patterns),
            patterns=pattern_responses
        )

    except Exception as e:
        logger.error(f"Pattern detection error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Pattern detection failed: {str(e)}")


async def detect_temporal_patterns(db: Session, user_id: int, images: List[Image]) -> List[Pattern]:
    """
    Detect temporal patterns (recurring events on similar dates)
    - Annual events (birthdays, anniversaries)
    - Monthly events
    - Weekly events
    """
    patterns = []

    # Filter images with capture dates
    dated_images = [img for img in images if img.capture_date]
    if len(dated_images) < 3:
        return patterns

    # Group images by month-day (for annual patterns)
    annual_groups = defaultdict(list)
    for img in dated_images:
        month_day = (img.capture_date.month, img.capture_date.day)
        annual_groups[month_day].append(img)

    # Detect annual patterns (same date across multiple years)
    for (month, day), imgs in annual_groups.items():
        if len(imgs) >= 2:  # At least 2 occurrences
            years = [img.capture_date.year for img in imgs]
            if len(set(years)) >= 2:  # At least 2 different years
                # Create pattern
                pattern = Pattern(
                    user_id=user_id,
                    pattern_type="temporal",
                    frequency="annual",
                    description=f"Annual event on {month}/{day}",
                    pattern_metadata={
                        "month": month,
                        "day": day,
                        "years": years,
                        "date_range": f"{min(years)}-{max(years)}"
                    },
                    confidence_score=min(0.95, 0.7 + (len(imgs) * 0.1))
                )
                db.add(pattern)
                db.flush()

                # Link images to pattern
                for img in imgs:
                    pattern_image = PatternImage(
                        pattern_id=pattern.id,
                        image_id=img.id
                    )
                    db.add(pattern_image)

                patterns.append(pattern)
                logger.info(f"Detected annual pattern: {month}/{day} with {len(imgs)} images")

    # Group images by month (for monthly patterns)
    monthly_groups = defaultdict(list)
    for img in dated_images:
        month = img.capture_date.month
        monthly_groups[month].append(img)

    # Detect monthly patterns (recurring monthly events)
    for month, imgs in monthly_groups.items():
        if len(imgs) >= 3:  # At least 3 images in same month across years
            years = [img.capture_date.year for img in imgs]
            if len(set(years)) >= 2:  # At least 2 different years
                pattern = Pattern(
                    user_id=user_id,
                    pattern_type="temporal",
                    frequency="monthly",
                    description=f"Monthly pattern in {datetime(2000, month, 1).strftime('%B')}",
                    pattern_metadata={
                        "month": month,
                        "years": list(set(years))
                    },
                    confidence_score=min(0.90, 0.6 + (len(imgs) * 0.05))
                )
                db.add(pattern)
                db.flush()

                for img in imgs:
                    pattern_image = PatternImage(
                        pattern_id=pattern.id,
                        image_id=img.id
                    )
                    db.add(pattern_image)

                patterns.append(pattern)
                logger.info(f"Detected monthly pattern: Month {month} with {len(imgs)} images")

    return patterns


async def detect_spatial_patterns(db: Session, user_id: int, images: List[Image]) -> List[Pattern]:
    """
    Detect spatial patterns (GPS clustering for frequent locations)
    Groups images taken at similar locations
    """
    patterns = []

    # Filter images with location data
    located_images = []
    for img in images:
        location = db.query(Location).filter(Location.image_id == img.id).first()
        if location and location.latitude and location.longitude:
            located_images.append((img, location))

    if len(located_images) < 3:
        return patterns

    # Simple clustering: group by proximity (within ~100m = 0.001 degrees)
    PROXIMITY_THRESHOLD = 0.001  # ~100 meters

    clustered = []
    clusters = []

    for img, loc in located_images:
        # Check if belongs to existing cluster
        added = False
        for cluster in clusters:
            cluster_center_lat = sum(l.latitude for _, l in cluster) / len(cluster)
            cluster_center_lon = sum(l.longitude for _, l in cluster) / len(cluster)

            dist = ((loc.latitude - cluster_center_lat) ** 2 +
                   (loc.longitude - cluster_center_lon) ** 2) ** 0.5

            if dist < PROXIMITY_THRESHOLD:
                cluster.append((img, loc))
                added = True
                break

        if not added:
            clusters.append([(img, loc)])

    # Create patterns for clusters with 2+ images
    for cluster in clusters:
        if len(cluster) >= 2:
            imgs, locs = zip(*cluster)

            center_lat = sum(l.latitude for l in locs) / len(locs)
            center_lon = sum(l.longitude for l in locs) / len(locs)

            # Get location name from first location
            location_name = locs[0].location_name or locs[0].city or "Unknown Location"

            pattern = Pattern(
                user_id=user_id,
                pattern_type="spatial",
                frequency="custom",
                description=f"Frequent location: {location_name}",
                pattern_metadata={
                    "center_lat": center_lat,
                    "center_lon": center_lon,
                    "location_name": location_name,
                    "city": locs[0].city,
                    "country": locs[0].country
                },
                confidence_score=min(0.95, 0.7 + (len(cluster) * 0.05))
            )
            db.add(pattern)
            db.flush()

            for img in imgs:
                pattern_image = PatternImage(
                    pattern_id=pattern.id,
                    image_id=img.id
                )
                db.add(pattern_image)

            patterns.append(pattern)
            logger.info(f"Detected spatial pattern at {location_name} with {len(cluster)} images")

    return patterns


async def detect_visual_patterns(db: Session, user_id: int, images: List[Image]) -> List[Pattern]:
    """
    Detect visual patterns (similar looking photos using CLIP embeddings)
    Note: This is a placeholder - full implementation requires CLIP embeddings storage
    """
    patterns = []

    logger.info(f"Starting visual pattern detection for user {user_id} with {len(images)} images")

    # For now, we'll implement a basic version using categories
    # Full implementation would use CLIP embeddings and cosine similarity

    # Group images by their primary category
    category_groups = defaultdict(list)

    for img in images:
        # Get image's top category
        from app.models import ImageCategory, Category
        image_cat = db.query(ImageCategory).filter(
            ImageCategory.image_id == img.id
        ).order_by(ImageCategory.confidence_score.desc()).first()

        if image_cat:
            category = db.query(Category).filter(Category.id == image_cat.category_id).first()
            if category:
                category_groups[category.name].append(img)
                logger.info(f"Image {img.id} -> category '{category.name}'")
            else:
                logger.warning(f"Image {img.id}: category_id {image_cat.category_id} not found")
        else:
            logger.warning(f"Image {img.id} has no categories")

    logger.info(f"Category groups: {[(name, len(imgs)) for name, imgs in category_groups.items()]}")

    # Create visual patterns for categories with 2+ images
    for category_name, imgs in category_groups.items():
        logger.info(f"Checking category '{category_name}' with {len(imgs)} images")
        if len(imgs) >= 2:
            pattern = Pattern(
                user_id=user_id,
                pattern_type="visual",
                frequency="custom",
                description=f"Visual cluster: {category_name}",
                pattern_metadata={
                    "category": category_name,
                    "clustering_method": "category_based"
                },
                confidence_score=0.75
            )
            db.add(pattern)
            db.flush()

            for img in imgs:
                pattern_image = PatternImage(
                    pattern_id=pattern.id,
                    image_id=img.id
                )
                db.add(pattern_image)

            patterns.append(pattern)
            logger.info(f"Detected visual pattern for {category_name} with {len(imgs)} images")

    return patterns


@router.get("/", response_model=List[PatternResponse])
async def get_patterns(
    user_id: int,
    pattern_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all detected patterns for a user
    Optionally filter by pattern_type
    """
    query = db.query(Pattern).filter(Pattern.user_id == user_id)

    if pattern_type:
        query = query.filter(Pattern.pattern_type == pattern_type)

    patterns = query.order_by(Pattern.confidence_score.desc()).all()

    # Add image count to each pattern
    result = []
    for pattern in patterns:
        image_count = db.query(PatternImage).filter(
            PatternImage.pattern_id == pattern.id
        ).count()

        pattern_dict = {
            "id": pattern.id,
            "user_id": pattern.user_id,
            "pattern_type": pattern.pattern_type,
            "frequency": pattern.frequency,
            "description": pattern.description,
            "pattern_metadata": pattern.pattern_metadata,
            "confidence_score": float(pattern.confidence_score) if pattern.confidence_score else None,
            "detected_date": pattern.detected_date,
            "created_at": pattern.created_at,
            "image_count": image_count
        }
        result.append(PatternResponse(**pattern_dict))

    return result


@router.get("/{pattern_id}", response_model=PatternWithImagesResponse)
async def get_pattern_details(
    pattern_id: int,
    db: Session = Depends(get_db)
):
    """
    Get pattern details with all images
    """
    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    # Get images in this pattern
    pattern_images = db.query(PatternImage).filter(
        PatternImage.pattern_id == pattern_id
    ).all()

    images = []
    image_ids = []
    for pi in pattern_images:
        img = db.query(Image).filter(Image.id == pi.image_id).first()
        if img:
            images.append(ImageUploadResponse(
                id=img.id,
                filename=img.filename,
                file_path=img.file_path,
                file_size=img.file_size,
                upload_date=img.upload_date,
                capture_date=img.capture_date
            ))
            image_ids.append(img.id)

    # Calculate dominant emotions for this pattern
    emotions_data = []
    if image_ids:
        # Get all emotions for images in this pattern
        emotion_aggregates = db.query(
            Emotion.id,
            Emotion.name,
            Emotion.color_code,
            func.avg(ImageEmotion.confidence_score).label('avg_confidence'),
            func.count(ImageEmotion.id).label('emotion_count')
        ).join(ImageEmotion).join(Image).filter(
            Image.id.in_(image_ids)
        ).group_by(Emotion.id, Emotion.name, Emotion.color_code).all()

        for emotion_id, emotion_name, color_code, avg_confidence, emotion_count in emotion_aggregates:
            percentage = float(avg_confidence * 100)
            emotions_data.append({
                "emotion": emotion_name,
                "percentage": percentage,
                "image_count": emotion_count,
                "color_code": color_code
            })

        # Sort by percentage descending
        emotions_data.sort(key=lambda x: x['percentage'], reverse=True)

    response_data = PatternWithImagesResponse(
        id=pattern.id,
        user_id=pattern.user_id,
        pattern_type=pattern.pattern_type,
        frequency=pattern.frequency,
        description=pattern.description,
        pattern_metadata=pattern.pattern_metadata or {},
        confidence_score=float(pattern.confidence_score) if pattern.confidence_score else None,
        detected_date=pattern.detected_date,
        created_at=pattern.created_at,
        image_count=len(images),
        images=images
    )

    # Add emotions to pattern_metadata if any exist
    if emotions_data:
        metadata = response_data.pattern_metadata or {}
        metadata['emotions'] = emotions_data
        response_data.pattern_metadata = metadata

    return response_data


@router.delete("/delete-all")
async def delete_all_patterns(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Delete ALL patterns for a user"""
    from app.models import Pattern
    pattern_count = db.query(Pattern).filter(Pattern.user_id == user_id).delete()
    db.commit()
    return {
        "message": f"Deleted {pattern_count} patterns",
        "deleted_count": pattern_count
    }


@router.delete("/{pattern_id}")
async def delete_pattern(
    pattern_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a pattern (cascade deletes pattern_images)
    """
    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    db.delete(pattern)
    db.commit()

    return {"success": True, "message": "Pattern deleted successfully"}

