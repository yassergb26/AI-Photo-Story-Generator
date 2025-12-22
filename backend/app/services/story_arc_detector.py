"""
Story Arc Detector Service
Detects story arcs within chapters (events, trips, milestones)
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.models import Chapter, Story, Image, LifeEvent, LifeEventImage, StoryImage
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def cluster_photos_by_temporal_bursts(photos: List[Image], min_gap_days: int = 3) -> List[List[Image]]:
    """
    Cluster photos by temporal bursts (photos taken close together in time)
    Photos within min_gap_days are grouped together
    """
    if not photos:
        return []

    # Sort by capture date
    sorted_photos = sorted(photos, key=lambda p: p.capture_date)

    clusters = []
    current_cluster = [sorted_photos[0]]

    for i in range(1, len(sorted_photos)):
        current_photo = sorted_photos[i]
        previous_photo = sorted_photos[i-1]

        # Calculate days between photos
        days_gap = (current_photo.capture_date - previous_photo.capture_date).days

        if days_gap <= min_gap_days:
            # Add to current cluster
            current_cluster.append(current_photo)
        else:
            # Save current cluster and start new one
            if len(current_cluster) >= 2:  # Only keep clusters with 2+ photos
                clusters.append(current_cluster)
            current_cluster = [current_photo]

    # Add final cluster
    if len(current_cluster) >= 2:
        clusters.append(current_cluster)

    return clusters


def cluster_photos_by_location(photos: List[Image], min_cluster_size: int = 5) -> List[List[Image]]:
    """
    Cluster photos by location (GPS coordinates)
    Groups photos taken at similar locations (trips, venues)
    """
    location_groups = defaultdict(list)

    for photo in photos:
        if not photo.location or not photo.location.get('latitude'):
            continue

        # Round coordinates to group nearby photos
        # ~11km precision with 2 decimal places
        lat = round(photo.location['latitude'], 1)
        lon = round(photo.location['longitude'], 1)
        location_key = f"{lat},{lon}"

        location_groups[location_key].append(photo)

    # Filter clusters by minimum size
    clusters = [photos for photos in location_groups.values() if len(photos) >= min_cluster_size]

    return clusters


def detect_life_event_arcs(chapter: Chapter, db: Session) -> List[Story]:
    """
    Detect story arcs from existing LifeEvents within chapter timeframe
    """
    story_arcs = []

    # Get life events within chapter date range
    query = db.query(LifeEvent).filter(LifeEvent.user_id == chapter.user_id)

    if chapter.year_start and chapter.year_end:
        # Filter by year range
        start_date = datetime(chapter.year_start, 1, 1)
        end_date = datetime(chapter.year_end, 12, 31, 23, 59, 59)
        query = query.filter(
            and_(
                LifeEvent.event_date >= start_date,
                LifeEvent.event_date <= end_date
            )
        )

    life_events = query.all()

    for event in life_events:
        # Get photos linked to this life event
        event_photos = db.query(Image).join(
            LifeEventImage, LifeEventImage.image_id == Image.id
        ).filter(
            LifeEventImage.life_event_id == event.id
        ).all()

        if not event_photos:
            continue

        # Map event type to arc type
        arc_type_mapping = {
            'wedding': 'event',
            'birth': 'event',
            'graduation': 'event',
            'move': 'milestone',
            'vacation': 'trip',
            'birthday': 'tradition',
            'anniversary': 'tradition'
        }

        arc_type = arc_type_mapping.get(event.event_type, 'event')

        # Get emoji for event type
        event_emojis = {
            'wedding': '💒',
            'birth': '👶',
            'graduation': '🎓',
            'move': '🏠',
            'vacation': '🏖️',
            'birthday': '🎂',
            'anniversary': '💝'
        }
        emoji = event_emojis.get(event.event_type, '🎉')

        # Create story arc
        story_arc = Story(
            user_id=chapter.user_id,
            chapter_id=chapter.id,
            title=f"{emoji} {event.event_name}",
            description=event.description,
            story_type=event.event_type,
            arc_type=arc_type,
            start_date=event.event_date,
            end_date=event.event_date,
            is_ai_detected=event.detection_method == 'ai_detected',
            photo_count=len(event_photos),
            generation_source='life_event',
            story_metadata={'life_event_id': event.id},
            sequence_order=len(story_arcs)
        )

        story_arcs.append(story_arc)
        logger.info(f"Created life event arc: {story_arc.title} ({len(event_photos)} photos)")

    return story_arcs


def detect_trip_arcs(chapter: Chapter, photos: List[Image], db: Session) -> List[Story]:
    """
    Detect trip story arcs from location clusters
    """
    story_arcs = []

    # Get photos with GPS data
    gps_photos = [p for p in photos if p.location and p.location.get('latitude')]

    if len(gps_photos) < 5:
        return []

    # Cluster by location
    location_clusters = cluster_photos_by_location(gps_photos, min_cluster_size=5)

    for cluster in location_clusters:
        # Get location name from first photo
        location_name = None
        if cluster[0].location:
            location_name = (
                cluster[0].location.get('location_name') or
                cluster[0].location.get('city') or
                cluster[0].location.get('country') or
                'Unknown Location'
            )

        # Get date range
        dates = [p.capture_date for p in cluster if p.capture_date]
        start_date = min(dates) if dates else None
        end_date = max(dates) if dates else None

        # Determine if it's a trip (photos span multiple days)
        is_trip = False
        if start_date and end_date:
            days_span = (end_date - start_date).days
            is_trip = days_span >= 2

        if not is_trip:
            continue  # Skip single-day location clusters

        # Create trip arc
        title = f"🏕️ {location_name}"
        if start_date:
            title += f" {start_date.year}"

        story_arc = Story(
            user_id=chapter.user_id,
            chapter_id=chapter.id,
            title=title,
            description=f"A memorable trip to {location_name}",
            story_type='trip',
            arc_type='trip',
            start_date=start_date,
            end_date=end_date,
            is_ai_detected=True,
            photo_count=len(cluster),
            generation_source='trip_cluster',
            story_metadata={'location_name': location_name},
            sequence_order=len(story_arcs)
        )

        story_arcs.append(story_arc)
        logger.info(f"Created trip arc: {story_arc.title} ({len(cluster)} photos)")

    return story_arcs


def detect_temporal_arcs(chapter: Chapter, photos: List[Image], db: Session) -> List[Story]:
    """
    Detect story arcs from temporal bursts (events clustered in time)
    """
    story_arcs = []

    # Get photos not already in life events or trips
    # For now, cluster all photos
    temporal_clusters = cluster_photos_by_temporal_bursts(photos, min_gap_days=7)

    for cluster in temporal_clusters:
        # Skip small clusters (reduced from 10 to 5 for smaller photo collections)
        if len(cluster) < 5:
            continue

        # Get date range
        dates = [p.capture_date for p in cluster if p.capture_date]
        start_date = min(dates) if dates else None
        end_date = max(dates) if dates else None

        if not start_date:
            continue

        # Generate title based on month/season
        month_name = start_date.strftime('%B')
        title = f"📸 {month_name} Moments"

        story_arc = Story(
            user_id=chapter.user_id,
            chapter_id=chapter.id,
            title=title,
            description=f"Memories from {month_name} {start_date.year}",
            story_type='moments',
            arc_type='event',
            start_date=start_date,
            end_date=end_date,
            is_ai_detected=False,
            photo_count=len(cluster),
            generation_source='time_cluster',
            story_metadata={},
            sequence_order=len(story_arcs)
        )

        story_arcs.append(story_arc)
        logger.info(f"Created temporal arc: {story_arc.title} ({len(cluster)} photos)")

    return story_arcs


def link_photos_to_story_arc(story: Story, photos: List[Image], db: Session):
    """Link photos to a story arc"""
    for idx, photo in enumerate(photos):
        story_image = StoryImage(
            story_id=story.id,
            image_id=photo.id,
            sequence_order=idx,
            is_cover=(idx == 0)
        )
        db.add(story_image)


def detect_story_arcs_for_chapter(chapter_id: int, db: Session) -> List[Story]:
    """
    Main function to detect all story arcs within a chapter

    Detects:
    1. Life event arcs (from LifeEvents table)
    2. Trip arcs (from GPS location clustering)
    3. AI pattern arcs (from classification + emotions + pattern detection)
    4. Temporal arcs (fallback - from time-based clustering)
    """
    # Get chapter
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise ValueError(f"Chapter {chapter_id} not found")

    logger.info(f"Detecting story arcs for chapter {chapter.id}: {chapter.title}")

    # Get all photos in chapter date range
    query = db.query(Image).filter(
        and_(
            Image.user_id == chapter.user_id,
            Image.capture_date.isnot(None)
        )
    )

    if chapter.year_start and chapter.year_end:
        start_date = datetime(chapter.year_start, 1, 1)
        end_date = datetime(chapter.year_end, 12, 31, 23, 59, 59)
        query = query.filter(
            and_(
                Image.capture_date >= start_date,
                Image.capture_date <= end_date
            )
        )

    photos = query.order_by(Image.capture_date).all()

    if not photos:
        logger.warning(f"No photos found for chapter {chapter_id}")
        return []

    logger.info(f"Found {len(photos)} photos in chapter timeframe")

    all_story_arcs = []

    # 1. Detect life event arcs (highest priority)
    life_event_arcs = detect_life_event_arcs(chapter, db)
    all_story_arcs.extend(life_event_arcs)

    # 2. Detect trip arcs
    trip_arcs = detect_trip_arcs(chapter, photos, db)
    all_story_arcs.extend(trip_arcs)

    # 3. Detect AI pattern arcs (uses classification + emotions)
    ai_arcs_count = 0
    try:
        from app.services.ai_story_arc_detector import detect_ai_pattern_arcs
        ai_arcs = detect_ai_pattern_arcs(chapter, photos, db)
        all_story_arcs.extend(ai_arcs)
        ai_arcs_count = len(ai_arcs)
        logger.info(f"AI pattern detection found {ai_arcs_count} arcs")
    except Exception as e:
        import traceback
        logger.error(f"AI pattern detection failed: {e}")
        logger.error(traceback.format_exc())

    # 4. Fallback to temporal arcs (only if AI detection failed or found no arcs)
    # Don't use temporal fallback if AI detection successfully found arcs
    if ai_arcs_count == 0 and len(all_story_arcs) < 2:
        temporal_arcs = detect_temporal_arcs(chapter, photos, db)
        all_story_arcs.extend(temporal_arcs[:2])  # Limit to 2 temporal arcs
        logger.info(f"Using temporal fallback: {len(temporal_arcs)} arcs")

    # Save story arcs
    for story_arc in all_story_arcs:
        db.add(story_arc)

    db.commit()

    # Refresh to get IDs
    for story_arc in all_story_arcs:
        db.refresh(story_arc)

    logger.info(f"Detected {len(all_story_arcs)} story arcs for chapter {chapter_id}")

    # Link photos to story arcs
    for story_arc in all_story_arcs:
        # Get photos for this arc based on generation source
        if story_arc.generation_source == 'life_event':
            # Get photos from life event
            life_event_id = story_arc.story_metadata.get('life_event_id')
            arc_photos = db.query(Image).join(
                LifeEventImage, LifeEventImage.image_id == Image.id
            ).filter(
                LifeEventImage.life_event_id == life_event_id
            ).all()
        elif story_arc.generation_source in ['ai_pattern', 'unified_ai_pattern']:
            # AI pattern arcs already store photo IDs in metadata
            photo_ids = story_arc.story_metadata.get('photo_ids', [])
            if photo_ids:
                arc_photos = db.query(Image).filter(Image.id.in_(photo_ids)).order_by(Image.capture_date).all()
            else:
                # Fallback to date range
                arc_photos = db.query(Image).filter(
                    and_(
                        Image.user_id == chapter.user_id,
                        Image.capture_date >= story_arc.start_date,
                        Image.capture_date <= story_arc.end_date
                    )
                ).order_by(Image.capture_date).all()
        elif story_arc.start_date and story_arc.end_date:
            # Get photos in date range
            arc_photos = db.query(Image).filter(
                and_(
                    Image.user_id == chapter.user_id,
                    Image.capture_date >= story_arc.start_date,
                    Image.capture_date <= story_arc.end_date
                )
            ).order_by(Image.capture_date).all()
        else:
            arc_photos = []

        if arc_photos:
            link_photos_to_story_arc(story_arc, arc_photos, db)

    db.commit()

    return all_story_arcs
