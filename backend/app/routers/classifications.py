"""
Classification endpoints for image categorization
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database import get_db
from app.models import Image, Category, ImageCategory
from app.schemas import ClassificationResponse, CategoryResponse, ImageWithCategoriesResponse
from app.services import classify_image_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/classifications", tags=["classifications"])


@router.post("/{image_id}", response_model=ClassificationResponse)
async def classify_image(
    image_id: int,
    db: Session = Depends(get_db),
    threshold: float = 0.15,
    top_k: int = 3
):
    """
    Classify a specific image and store results

    Args:
        image_id: ID of the image to classify
        threshold: Minimum confidence threshold (0-1)
        top_k: Maximum number of categories
        db: Database session

    Returns:
        Classification results with categories and confidence scores
    """
    # Get image from database
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with ID {image_id} not found"
        )

    try:
        # Run classification
        logger.info(f"Classifying image {image_id}: {image.filename}")
        results = classify_image_file(image.file_path, threshold, top_k)

        if not results:
            logger.warning(f"No categories found for image {image_id}")
            return ClassificationResponse(
                image_id=image_id,
                filename=image.filename,
                categories=[],
                message="No categories met the confidence threshold"
            )

        # Delete existing classifications for this image
        db.query(ImageCategory).filter(ImageCategory.image_id == image_id).delete()

        # Store new classifications
        category_responses = []
        for result in results:
            # Get or create category
            category = db.query(Category).filter(Category.name == result["category"]).first()
            if not category:
                # Create category if it doesn't exist
                category = Category(
                    name=result["category"],
                    description=f"Auto-generated category for {result['category']}"
                )
                db.add(category)
                db.flush()

            # Create image-category association
            image_category = ImageCategory(
                image_id=image_id,
                category_id=category.id,
                confidence_score=result["confidence"]
            )
            db.add(image_category)

            category_responses.append({
                "id": category.id,
                "name": category.name,
                "confidence": result["confidence"]
            })

        # Mark image as processed
        image.processed = True
        db.commit()

        logger.info(f"Successfully classified image {image_id} into {len(results)} categories")

        return ClassificationResponse(
            image_id=image_id,
            filename=image.filename,
            categories=category_responses,
            message=f"Successfully classified into {len(results)} categories"
        )

    except Exception as e:
        logger.error(f"Error classifying image {image_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error classifying image: {str(e)}"
        )


@router.post("/batch", response_model=List[ClassificationResponse])
async def classify_batch(
    image_ids: List[int],
    db: Session = Depends(get_db),
    threshold: float = 0.15,
    top_k: int = 3
):
    """
    Classify multiple images in batch

    Args:
        image_ids: List of image IDs to classify
        threshold: Minimum confidence threshold
        top_k: Maximum categories per image
        db: Database session

    Returns:
        List of classification results
    """
    results = []
    for image_id in image_ids:
        try:
            result = await classify_image(image_id, db, threshold, top_k)
            results.append(result)
        except HTTPException as e:
            logger.warning(f"Skipping image {image_id}: {e.detail}")
            continue

    return results


@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """
    Get all available categories

    Args:
        db: Database session

    Returns:
        List of all categories
    """
    categories = db.query(Category).all()
    return categories


@router.get("/images/{image_id}", response_model=ImageWithCategoriesResponse)
def get_image_with_categories(image_id: int, db: Session = Depends(get_db)):
    """
    Get image with its assigned categories

    Args:
        image_id: ID of the image
        db: Database session

    Returns:
        Image details with categories and confidence scores
    """
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with ID {image_id} not found"
        )

    # Get image categories with confidence scores
    image_categories = db.query(ImageCategory, Category)\
        .join(Category)\
        .filter(ImageCategory.image_id == image_id)\
        .all()

    categories = [
        {
            "id": cat.id,
            "name": cat.name,
            "description": cat.description,
            "color_code": cat.color_code,
            "confidence": float(ic.confidence_score)
        }
        for ic, cat in image_categories
    ]

    return ImageWithCategoriesResponse(
        id=image.id,
        filename=image.filename,
        file_path=image.file_path,
        file_size=image.file_size,
        upload_date=image.upload_date,
        capture_date=image.capture_date,
        processed=image.processed,
        categories=categories
    )


@router.get("/by-category/{category_id}")
def get_images_by_category(
    category_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get all images in a specific category

    Args:
        category_id: ID of the category
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of images in the category
    """
    # Check if category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} not found"
        )

    # Get images in this category
    image_categories = db.query(ImageCategory)\
        .filter(ImageCategory.category_id == category_id)\
        .offset(skip)\
        .limit(limit)\
        .all()

    image_ids = [ic.image_id for ic in image_categories]
    images = db.query(Image).filter(Image.id.in_(image_ids)).all()

    return {
        "category": {
            "id": category.id,
            "name": category.name,
            "description": category.description
        },
        "images": images,
        "count": len(images)
    }
