"""
Life Events API Router
Handles CRUD operations for manually created life events and image linking
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.models import LifeEvent, LifeEventImage, Image
from app.schemas import (
    LifeEventCreate,
    LifeEventUpdate,
    LifeEventResponse,
    LifeEventWithImagesResponse,
    LifeEventImageResponse,
    LinkImagesToEventRequest
)

router = APIRouter(prefix="/api/life-events", tags=["life-events"])


@router.post("/", response_model=LifeEventResponse, status_code=status.HTTP_201_CREATED)
async def create_life_event(event: LifeEventCreate, db: Session = Depends(get_db)):
    """
    Create a new life event (manual creation)

    Args:
        event: LifeEventCreate schema with event details
        db: Database session

    Returns:
        Created LifeEvent with basic details
    """
    # Create life event
    db_event = LifeEvent(
        user_id=event.user_id,
        event_type=event.event_type,
        event_name=event.event_name,
        event_date=event.event_date,
        event_location=event.event_location,
        description=event.description,
        detection_method='manual',
        event_metadata=event.event_metadata or {}
    )

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Link images if provided
    if event.image_ids:
        for idx, image_id in enumerate(event.image_ids):
            # Verify image exists and belongs to user
            image = db.query(Image).filter(
                Image.id == image_id,
                Image.user_id == event.user_id
            ).first()

            if image:
                life_event_image = LifeEventImage(
                    life_event_id=db_event.id,
                    image_id=image_id,
                    sequence_order=idx,
                    is_cover_image=(idx == 0)  # First image as cover
                )
                db.add(life_event_image)

        db.commit()

    # Return response with image count
    response = LifeEventResponse.from_orm(db_event)
    response.image_count = len(event.image_ids) if event.image_ids else 0

    return response


@router.get("/", response_model=List[LifeEventResponse])
async def get_life_events(user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all life events for a user

    Args:
        user_id: User ID to filter events
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of life events with basic details
    """
    events = db.query(LifeEvent).filter(
        LifeEvent.user_id == user_id
    ).order_by(LifeEvent.event_date.desc()).offset(skip).limit(limit).all()

    # Add image count to each event
    results = []
    for event in events:
        event_response = LifeEventResponse.from_orm(event)
        event_response.image_count = len(event.life_event_images)
        results.append(event_response)

    return results


@router.get("/{event_id}", response_model=LifeEventWithImagesResponse)
async def get_life_event_detail(event_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific life event including all linked images

    Args:
        event_id: Life event ID
        db: Database session

    Returns:
        LifeEvent with full details and linked images
    """
    event = db.query(LifeEvent).filter(LifeEvent.id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Life event with id {event_id} not found"
        )

    # Build response with images
    images = []
    for life_event_image in event.life_event_images:
        image = life_event_image.image
        images.append(LifeEventImageResponse(
            id=image.id,
            filename=image.filename,
            file_path=image.file_path,
            thumbnail_path=image.thumbnail_path,
            capture_date=image.capture_date,
            sequence_order=life_event_image.sequence_order,
            is_cover_image=life_event_image.is_cover_image
        ))

    # Sort images by sequence order
    images.sort(key=lambda x: x.sequence_order if x.sequence_order is not None else 0)

    # Build response manually to avoid Pydantic validation issues
    return LifeEventWithImagesResponse(
        id=event.id,
        user_id=event.user_id,
        event_type=event.event_type,
        event_name=event.event_name,
        event_date=event.event_date,
        event_location=event.event_location,
        description=event.description,
        detection_method=event.detection_method,
        confidence_score=event.confidence_score,
        event_metadata=event.event_metadata,
        created_at=event.created_at,
        updated_at=event.updated_at,
        image_count=len(images),
        images=images
    )


@router.put("/{event_id}", response_model=LifeEventResponse)
async def update_life_event(event_id: int, event_update: LifeEventUpdate, db: Session = Depends(get_db)):
    """
    Update an existing life event

    Args:
        event_id: Life event ID to update
        event_update: Fields to update
        db: Database session

    Returns:
        Updated LifeEvent
    """
    db_event = db.query(LifeEvent).filter(LifeEvent.id == event_id).first()

    if not db_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Life event with id {event_id} not found"
        )

    # Update fields
    update_data = event_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_event, field, value)

    db_event.updated_at = datetime.now()
    db.commit()
    db.refresh(db_event)

    response = LifeEventResponse.from_orm(db_event)
    response.image_count = len(db_event.life_event_images)

    return response


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_life_event(event_id: int, db: Session = Depends(get_db)):
    """
    Delete a life event (cascade deletes image links)

    Args:
        event_id: Life event ID to delete
        db: Database session
    """
    db_event = db.query(LifeEvent).filter(LifeEvent.id == event_id).first()

    if not db_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Life event with id {event_id} not found"
        )

    db.delete(db_event)
    db.commit()

    return None


@router.post("/{event_id}/images", response_model=LifeEventWithImagesResponse)
async def link_images_to_event(
    event_id: int,
    request: LinkImagesToEventRequest,
    db: Session = Depends(get_db)
):
    """
    Link additional images to an existing life event

    Args:
        event_id: Life event ID
        request: List of image IDs to link
        db: Database session

    Returns:
        Updated LifeEvent with all images
    """
    db_event = db.query(LifeEvent).filter(LifeEvent.id == event_id).first()

    if not db_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Life event with id {event_id} not found"
        )

    # Get current max sequence order
    current_links = db.query(LifeEventImage).filter(
        LifeEventImage.life_event_id == event_id
    ).all()
    max_sequence = max([link.sequence_order for link in current_links if link.sequence_order is not None], default=-1)

    # Link new images
    added_count = 0
    for idx, image_id in enumerate(request.image_ids):
        # Check if already linked
        existing_link = db.query(LifeEventImage).filter(
            LifeEventImage.life_event_id == event_id,
            LifeEventImage.image_id == image_id
        ).first()

        if existing_link:
            continue

        # Verify image exists and belongs to same user
        image = db.query(Image).filter(
            Image.id == image_id,
            Image.user_id == db_event.user_id
        ).first()

        if not image:
            continue

        # Create link
        life_event_image = LifeEventImage(
            life_event_id=event_id,
            image_id=image_id,
            sequence_order=max_sequence + idx + 1,
            is_cover_image=False
        )
        db.add(life_event_image)
        added_count += 1

    db.commit()
    db.refresh(db_event)

    # Return updated event with images
    return await get_life_event_detail(event_id, db)


@router.delete("/{event_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_image_from_event(event_id: int, image_id: int, db: Session = Depends(get_db)):
    """
    Remove an image from a life event

    Args:
        event_id: Life event ID
        image_id: Image ID to unlink
        db: Database session
    """
    link = db.query(LifeEventImage).filter(
        LifeEventImage.life_event_id == event_id,
        LifeEventImage.image_id == image_id
    ).first()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image {image_id} not linked to event {event_id}"
        )

    db.delete(link)
    db.commit()

    return None


@router.get("/types/list")
async def get_event_types():
    """
    Get list of available event types

    Returns:
        List of event type options with descriptions
    """
    event_types = [
        {"value": "birthday", "label": "Birthday", "icon": "🎂", "description": "Birthday celebrations"},
        {"value": "wedding", "label": "Wedding", "icon": "💍", "description": "Wedding ceremonies and receptions"},
        {"value": "anniversary", "label": "Anniversary", "icon": "💐", "description": "Wedding or relationship anniversaries"},
        {"value": "graduation", "label": "Graduation", "icon": "🎓", "description": "Graduation ceremonies and celebrations"},
        {"value": "vacation", "label": "Vacation", "icon": "✈️", "description": "Travel and vacation trips"},
        {"value": "move", "label": "Move/Relocation", "icon": "🏠", "description": "Moving to a new home or city"},
        {"value": "birth", "label": "Birth", "icon": "👶", "description": "Birth of a child"},
        {"value": "party", "label": "Party/Celebration", "icon": "🎉", "description": "Parties and social gatherings"},
        {"value": "holiday", "label": "Holiday", "icon": "🎄", "description": "Holiday celebrations"},
        {"value": "achievement", "label": "Achievement", "icon": "🏆", "description": "Personal or professional achievements"},
        {"value": "custom", "label": "Custom Event", "icon": "📅", "description": "Custom or other event type"}
    ]

    return {"event_types": event_types}


@router.delete("/delete-all")
async def delete_all_life_events(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Delete ALL life events for a user"""
    from app.models import LifeEvent
    event_count = db.query(LifeEvent).filter(LifeEvent.user_id == user_id).delete()
    db.commit()
    return {
        "message": f"Deleted {event_count} life events",
        "deleted_count": event_count
    }

