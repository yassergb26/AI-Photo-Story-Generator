"""
Export endpoints for photos, stories, and life events
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import json
import os
import logging

from app.database import get_db
from app.models import Image, Story, LifeEvent
from app.utils.pdf_generator import generate_photo_album_pdf, generate_story_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.get("/photos/json")
async def export_photos_json(
    user_id: int = 1,
    include_metadata: bool = True,
    db: Session = Depends(get_db)
):
    """
    Export all photos for a user as JSON

    Args:
        user_id: User ID to export photos for
        include_metadata: Include EXIF and location data
        db: Database session

    Returns:
        JSON file with photo data
    """
    try:
        images = db.query(Image).filter(Image.user_id == user_id).all()

        export_data = {
            "export_date": datetime.now().isoformat(),
            "user_id": user_id,
            "total_photos": len(images),
            "photos": []
        }

        for image in images:
            photo_data = {
                "id": image.id,
                "filename": image.filename,
                "upload_date": image.upload_date.isoformat() if image.upload_date else None,
                "capture_date": image.capture_date.isoformat() if image.capture_date else None,
                "file_size": image.file_size,
                "processed": image.processed
            }

            if include_metadata:
                photo_data["exif_data"] = image.exif_data
                if image.location:
                    photo_data["location"] = {
                        "latitude": image.location.latitude,
                        "longitude": image.location.longitude,
                        "location_name": image.location.location_name,
                        "city": image.location.city,
                        "country": image.location.country
                    }

            export_data["photos"].append(photo_data)

        return JSONResponse(content=export_data)

    except Exception as e:
        logger.error(f"Error exporting photos to JSON: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export photos: {str(e)}"
        )


@router.get("/photos/pdf")
async def export_photos_pdf(
    user_id: int = 1,
    title: str = "Photo Album",
    include_metadata: bool = True,
    db: Session = Depends(get_db)
):
    """
    Export photos as a PDF album

    Args:
        user_id: User ID to export photos for
        title: Title of the photo album
        include_metadata: Include dates and locations
        db: Database session

    Returns:
        PDF file download
    """
    try:
        images = db.query(Image).filter(Image.user_id == user_id).all()

        if not images:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No photos found for this user"
            )

        # Generate PDF
        pdf_path = await generate_photo_album_pdf(
            images,
            title=title,
            include_metadata=include_metadata
        )

        # Return PDF file
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"photo_album_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting photos to PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@router.get("/stories/json")
async def export_stories_json(
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """
    Export all stories for a user as JSON

    Args:
        user_id: User ID to export stories for
        db: Database session

    Returns:
        JSON file with story data
    """
    try:
        stories = db.query(Story).filter(Story.user_id == user_id).all()

        export_data = {
            "export_date": datetime.now().isoformat(),
            "user_id": user_id,
            "total_stories": len(stories),
            "stories": []
        }

        for story in stories:
            story_data = {
                "id": story.id,
                "title": story.title,
                "narrative": story.narrative,
                "story_type": story.story_type,
                "start_date": story.start_date.isoformat() if story.start_date else None,
                "end_date": story.end_date.isoformat() if story.end_date else None,
                "created_at": story.created_at.isoformat() if story.created_at else None,
                "image_count": len(story.story_images)
            }

            export_data["stories"].append(story_data)

        return JSONResponse(content=export_data)

    except Exception as e:
        logger.error(f"Error exporting stories to JSON: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export stories: {str(e)}"
        )


@router.get("/stories/{story_id}/pdf")
async def export_story_pdf(
    story_id: int,
    db: Session = Depends(get_db)
):
    """
    Export a single story as a PDF

    Args:
        story_id: Story ID to export
        db: Database session

    Returns:
        PDF file download
    """
    try:
        story = db.query(Story).filter(Story.id == story_id).first()

        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Story with ID {story_id} not found"
            )

        # Generate PDF
        pdf_path = await generate_story_pdf(story)

        # Return PDF file
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"story_{story.title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting story to PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@router.get("/life-events/json")
async def export_life_events_json(
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """
    Export all life events for a user as JSON

    Args:
        user_id: User ID to export life events for
        db: Database session

    Returns:
        JSON file with life event data
    """
    try:
        events = db.query(LifeEvent).filter(LifeEvent.user_id == user_id).all()

        export_data = {
            "export_date": datetime.now().isoformat(),
            "user_id": user_id,
            "total_events": len(events),
            "life_events": []
        }

        for event in events:
            event_data = {
                "id": event.id,
                "event_type": event.event_type,
                "event_name": event.event_name,
                "event_date": event.event_date.isoformat() if event.event_date else None,
                "event_location": event.event_location,
                "description": event.description,
                "detection_method": event.detection_method,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "image_count": len(event.life_event_images)
            }

            export_data["life_events"].append(event_data)

        return JSONResponse(content=export_data)

    except Exception as e:
        logger.error(f"Error exporting life events to JSON: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export life events: {str(e)}"
        )
