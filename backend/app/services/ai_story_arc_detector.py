"""
AI-Powered Story Arc Detection
Uses Classification + Emotions + Pattern Detection to create meaningful story arcs
"""
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.models import Image, Story, Chapter, ImageCategory, Category, ImageEmotion, Emotion
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def detect_ai_pattern_arcs(chapter: Chapter, photos: List[Image], db: Session) -> List[Story]:
    """
    UNIFIED STRONG PATTERN DETECTION
    Combines all three signals for intelligent story arc detection:
    1. DATE PROXIMITY - Photos taken close together in time
    2. VISUAL SIMILARITY - Classifications (beach, celebration, outdoor, etc.)
    3. EMOTIONAL CONTEXT - Emotions (happy, sad, excited, etc.)

    This creates meaningful story arcs that understand:
    - WHAT happened (classifications)
    - WHEN it happened (date clustering)
    - HOW people felt (emotions)

    Examples:
    - Beach photos + happy emotions + within 7 days = "Beach Vacation"
    - Celebration category + love emotion + same day = "Wedding Day"
    - Outdoor + happy + 3-day cluster = "Hiking Adventures"
    """
    story_arcs = []

    logger.info(f"Running UNIFIED AI pattern detection on {len(photos)} photos")

    # Debug: Check if photos have capture dates
    photos_with_dates = [p for p in photos if p.capture_date]
    logger.info(f"Photos with capture dates: {len(photos_with_dates)}/{len(photos)}")

    # STEP 1: Temporal clustering (group by date proximity)
    # Photos within 30 days (1 month), minimum 3 photos per cluster
    # This is more flexible for photos spread across many years
    temporal_clusters = _cluster_by_time(photos, max_gap_days=30, min_cluster_size=3)

    logger.info(f"Found {len(temporal_clusters)} temporal clusters")
    for i, cluster in enumerate(temporal_clusters):
        logger.info(f"  Cluster {i+1}: {len(cluster)} photos")

    # STEP 2: Analyze each cluster using BOTH classification AND emotions
    for cluster in temporal_clusters:
        # Analyze this cluster with unified pattern detection
        arc = _analyze_cluster_with_unified_patterns(cluster, chapter, db)
        if arc:
            story_arcs.append(arc)

    return story_arcs


def _analyze_cluster_with_unified_patterns(cluster: List[Image], chapter: Chapter, db: Session) -> Story:
    """
    UNIFIED PATTERN ANALYSIS
    Uses DATE + CLASSIFICATION + EMOTIONS together to create intelligent story arcs

    This is the STRONGEST approach because it considers:
    1. What's in the photos (visual content via classifications)
    2. How people felt (emotional context)
    3. When it happened (temporal context)
    """
    photo_ids = [p.id for p in cluster]

    # Get classifications for this cluster
    classifications = db.query(
        Category.name,
        func.count(ImageCategory.id).label('count'),
        func.avg(ImageCategory.confidence_score).label('avg_confidence')
    ).join(
        ImageCategory, ImageCategory.category_id == Category.id
    ).filter(
        ImageCategory.image_id.in_(photo_ids)
    ).group_by(
        Category.name
    ).order_by(
        func.count(ImageCategory.id).desc()
    ).limit(5).all()  # Get top 5 categories

    # Get emotions for this cluster
    emotions = db.query(
        Emotion.name,
        func.count(ImageEmotion.id).label('count'),
        func.avg(ImageEmotion.confidence_score).label('avg_confidence')
    ).join(
        ImageEmotion, ImageEmotion.emotion_id == Emotion.id
    ).filter(
        ImageEmotion.image_id.in_(photo_ids)
    ).group_by(
        Emotion.name
    ).order_by(
        func.count(ImageEmotion.id).desc()
    ).limit(3).all()  # Get top 3 emotions

    # UNIFIED ANALYSIS: Determine story arc type using ALL signals
    arc_info = _determine_arc_type_unified(classifications, emotions, cluster)

    if not arc_info:
        # If no specific pattern matches, create a generic arc
        # AI will generate the actual title and description later based on content
        start_date = min([p.capture_date for p in cluster])
        month_name = start_date.strftime('%B')

        arc_info = {
            'title': f"{month_name} Moments",  # Placeholder - AI will enhance this
            'description': "To be enhanced by AI",  # Placeholder - AI will generate this
            'story_type': 'moments',
            'arc_type': 'moments'
        }

    # Create story arc with unified metadata
    story_arc = Story(
        user_id=chapter.user_id,
        chapter_id=chapter.id,
        title=arc_info['title'],
        description=arc_info['description'],
        story_type=arc_info['story_type'],
        arc_type=arc_info['arc_type'],
        start_date=cluster[0].capture_date,
        end_date=cluster[-1].capture_date,
        is_ai_detected=True,
        photo_count=len(cluster),
        generation_source='unified_ai_pattern',  # New source identifier
        story_metadata={
            'categories': [c[0] for c in classifications],
            'category_confidences': [float(c[2]) for c in classifications],
            'emotions': [e[0] for e in emotions],
            'emotion_confidences': [float(e[2]) for e in emotions],
            'detection_method': 'date+classification+emotions',  # Unified approach
            'photo_ids': photo_ids,
            'temporal_span_days': (cluster[-1].capture_date - cluster[0].capture_date).days
        }
    )

    logger.info(f"UNIFIED AI detected: {arc_info['title']} ({len(cluster)} photos, "
                f"categories: {[c[0] for c in classifications[:2]]}, "
                f"emotions: {[e[0] for e in emotions[:2]]})")

    return story_arc


def _determine_arc_type_unified(classifications: List, emotions: List, cluster: List[Image]) -> Dict:
    """
    UNIFIED PATTERN MATCHING
    Uses BOTH classifications AND emotions together to intelligently determine event type

    This is much stronger than using temporal patterns alone because it understands:
    - WHAT: Beach, celebration, outdoor, family, etc.
    - HOW: Happy, love, excited, neutral, etc.
    - WHEN: Duration and timing from cluster
    """
    if not classifications:
        return None

    # Extract category and emotion names
    category_names = [c[0].lower() for c in classifications]
    emotion_names = [e[0].lower() for e in emotions] if emotions else []

    # Calculate duration
    duration_days = (cluster[-1].capture_date - cluster[0].capture_date).days

    # PATTERN MATCHING RULES (ordered by specificity)

    # 1. Beach/Vacation (visual + emotional context)
    if any(cat in category_names for cat in ['beach', 'ocean', 'vacation', 'travel', 'tropical']):
        if duration_days >= 3:
            return {
                'title': '🏖️ Beach Vacation',
                'description': 'Sun, sand, and unforgettable memories by the ocean.',
                'story_type': 'vacation',
                'arc_type': 'trip'
            }
        else:
            return {
                'title': '🏖️ Beach Day',
                'description': 'A perfect day by the water.',
                'story_type': 'day_trip',
                'arc_type': 'moments'
            }

    # 2. Wedding/Special Celebration (visual + strong emotional context)
    if any(cat in category_names for cat in ['wedding', 'bride', 'ceremony']):
        return {
            'title': '💒 Wedding Celebration',
            'description': 'A beautiful celebration of love and commitment.',
            'story_type': 'wedding',
            'arc_type': 'event'
        }

    # 3. Birthday/Party (celebration + happiness)
    if 'celebration' in category_names or 'party' in category_names:
        if any(emo in emotion_names for emo in ['happiness', 'happy', 'joy']):
            return {
                'title': '🎉 Celebration',
                'description': 'Joyful moments celebrating together.',
                'story_type': 'celebration',
                'arc_type': 'event'
            }

    # 4. Family & Friends (family/friends + any positive emotion)
    if any(cat in category_names for cat in ['family', 'family & friends', 'gathering']):
        if any(emo in emotion_names for emo in ['happiness', 'love', 'joy']):
            return {
                'title': '👥 Time with Loved Ones',
                'description': 'Cherished moments with family and friends.',
                'story_type': 'social',
                'arc_type': 'event'
            }

    # 5. Outdoor Adventure (outdoor + happiness)
    if any(cat in category_names for cat in ['outdoor', 'nature', 'hiking', 'camping']):
        if any(emo in emotion_names for emo in ['happiness', 'excited']):
            return {
                'title': '🏕️ Outdoor Adventure',
                'description': 'Exploring nature and making memories.',
                'story_type': 'adventure',
                'arc_type': 'trip'
            }

    # 6. Holiday/Festive (holidays + positive emotions)
    if any(cat in category_names for cat in ['holiday', 'christmas', 'festive', 'decoration']):
        return {
            'title': '🎄 Holiday Celebration',
            'description': 'Festive moments filled with joy and warmth.',
            'story_type': 'holiday',
            'arc_type': 'event'
        }

    # 7. Travel/Trip (multiple days + various categories)
    if duration_days >= 3:
        return {
            'title': f'✈️ {cluster[0].capture_date.strftime("%B")} Trip',
            'description': f'A {duration_days}-day journey filled with new experiences.',
            'story_type': 'trip',
            'arc_type': 'trip'
        }

    # 8. Category-based arcs (no emotion required for broader matching)
    # These create story arcs based on dominant visual content alone
    category_patterns = {
        'food': ('🍽️ Food & Dining', 'Delicious meals and culinary experiences.', 'dining'),
        'restaurant': ('🍽️ Food & Dining', 'Delicious meals and culinary experiences.', 'dining'),
        'pets': ('🐾 Pet Moments', 'Special times with furry friends.', 'pets'),
        'dog': ('🐾 Pet Moments', 'Special times with furry friends.', 'pets'),
        'cat': ('🐾 Pet Moments', 'Special times with furry friends.', 'pets'),
        'animal': ('🐾 Animal Encounters', 'Memorable moments with animals.', 'animals'),
        'sports': ('⚽ Sports & Activities', 'Active moments filled with energy.', 'activity'),
        'activity': ('⚽ Sports & Activities', 'Active moments filled with energy.', 'activity'),
        'art': ('🎨 Creative Moments', 'Artistic and creative experiences.', 'creative'),
        'music': ('🎵 Musical Moments', 'Times filled with music and rhythm.', 'music'),
        'car': ('🚗 On the Road', 'Adventures and travels by car.', 'travel'),
        'vehicle': ('🚗 On the Road', 'Adventures and travels by vehicle.', 'travel'),
    }

    for keyword, (title, desc, story_type) in category_patterns.items():
        if keyword in category_names:
            return {
                'title': title,
                'description': desc,
                'story_type': story_type,
                'arc_type': 'moments'
            }

    # Default: Return None to trigger generic "Moments" creation
    return None


def _cluster_by_time(photos: List[Image], max_gap_days: int = 7, min_cluster_size: int = 3) -> List[List[Image]]:
    """
    Cluster photos by temporal proximity
    """
    if not photos:
        return []

    sorted_photos = sorted(photos, key=lambda p: p.capture_date)
    clusters = []
    current_cluster = [sorted_photos[0]]

    for i in range(1, len(sorted_photos)):
        current = sorted_photos[i]
        previous = sorted_photos[i-1]

        days_gap = (current.capture_date - previous.capture_date).days

        if days_gap <= max_gap_days:
            current_cluster.append(current)
        else:
            if len(current_cluster) >= min_cluster_size:
                clusters.append(current_cluster)
            current_cluster = [current]

    # Don't forget last cluster
    if len(current_cluster) >= min_cluster_size:
        clusters.append(current_cluster)

    return clusters


def _analyze_cluster_for_story_arc(cluster: List[Image], chapter: Chapter, db: Session) -> Story:
    """
    Analyze a temporal cluster to detect what kind of story arc it represents
    Uses classification + emotions to determine event type
    """
    photo_ids = [p.id for p in cluster]

    # Get all classifications for these photos
    classifications = db.query(
        Category.name,
        func.count(ImageCategory.id).label('count'),
        func.avg(ImageCategory.confidence_score).label('avg_confidence')
    ).join(
        ImageCategory, ImageCategory.category_id == Category.id
    ).filter(
        ImageCategory.image_id.in_(photo_ids)
    ).group_by(
        Category.name
    ).order_by(
        func.count(ImageCategory.id).desc()
    ).limit(3).all()

    # Get dominant emotions
    emotions = db.query(
        Emotion.name,
        func.count(ImageEmotion.id).label('count')
    ).join(
        ImageEmotion, ImageEmotion.emotion_id == Emotion.id
    ).filter(
        ImageEmotion.image_id.in_(photo_ids)
    ).group_by(
        Emotion.name
    ).order_by(
        func.count(ImageEmotion.id).desc()
    ).limit(2).all()

    # Determine story arc type based on classifications + emotions
    arc_info = _determine_arc_type(classifications, emotions, cluster)

    if not arc_info:
        return None

    # Create story arc
    story_arc = Story(
        user_id=chapter.user_id,
        chapter_id=chapter.id,
        title=arc_info['title'],
        description=arc_info['description'],
        story_type=arc_info['story_type'],
        arc_type=arc_info['arc_type'],
        start_date=cluster[0].capture_date,
        end_date=cluster[-1].capture_date,
        is_ai_detected=True,
        photo_count=len(cluster),
        generation_source='ai_pattern',
        story_metadata={
            'categories': [c[0] for c in classifications],
            'emotions': [e[0] for e in emotions],
            'detection_method': 'classification+emotions',
            'photo_ids': photo_ids  # Store photo IDs for linking
        }
    )

    logger.info(f"AI detected story arc: {arc_info['title']} ({len(cluster)} photos)")

    return story_arc


def _determine_arc_type(classifications: List, emotions: List, cluster: List[Image]) -> Dict:
    """
    Use AI logic to determine what kind of event this cluster represents
    Based on categories and emotions
    """
    if not classifications:
        return None

    # Extract category and emotion names
    category_names = [c[0].lower() for c in classifications] if classifications else []
    emotion_names = [e[0].lower() for e in emotions] if emotions else []

    # Pattern matching rules

    # Beach/Vacation
    if any(cat in category_names for cat in ['beach', 'ocean', 'vacation', 'travel']):
        return {
            'title': '🏖️ Beach Vacation',
            'description': 'Sun, sand, and unforgettable memories by the ocean.',
            'story_type': 'vacation',
            'arc_type': 'trip'
        }

    # Celebration/Wedding/Party
    if any(cat in category_names for cat in ['celebration', 'party', 'wedding']):
        if any(emo in emotion_names for emo in ['love', 'joy', 'happy']):
            return {
                'title': '💝 Special Celebration',
                'description': 'A joyful gathering filled with love and happiness.',
                'story_type': 'celebration',
                'arc_type': 'event'
            }

    # Outdoor/Adventure
    if any(cat in category_names for cat in ['outdoor', 'nature', 'hiking', 'mountain']):
        return {
            'title': '⛰️ Outdoor Adventure',
            'description': 'Exploring the great outdoors and connecting with nature.',
            'story_type': 'adventure',
            'arc_type': 'activity'
        }

    # Family gathering
    if any(cat in category_names for cat in ['family', 'people', 'gathering']):
        if any(emo in emotion_names for emo in ['happy', 'love', 'joy']):
            return {
                'title': '👨‍👩‍👧 Family Time',
                'description': 'Precious moments spent with loved ones.',
                'story_type': 'family',
                'arc_type': 'tradition'
            }

    # Sports/Activity
    if any(cat in category_names for cat in ['sports', 'activity', 'game']):
        return {
            'title': '⚽ Sports & Activities',
            'description': 'Active days filled with energy and excitement.',
            'story_type': 'activity',
            'arc_type': 'hobby'
        }

    # Food/Dining
    if any(cat in category_names for cat in ['food', 'restaurant', 'dining']):
        return {
            'title': '🍽️ Culinary Moments',
            'description': 'Delicious meals and dining experiences to remember.',
            'story_type': 'dining',
            'arc_type': 'activity'
        }

    # Pets
    if any(cat in category_names for cat in ['pets', 'dog', 'cat', 'animal']):
        return {
            'title': '🐾 Pet Memories',
            'description': 'Special moments with our furry friends.',
            'story_type': 'pets',
            'arc_type': 'companionship'
        }

    # Seasonal/Holiday
    if any(cat in category_names for cat in ['christmas', 'holiday', 'seasonal']):
        return {
            'title': '🎄 Holiday Celebrations',
            'description': 'Festive times and seasonal traditions.',
            'story_type': 'holiday',
            'arc_type': 'tradition'
        }

    # Default: General moments based on emotion
    dominant_emotion = emotion_names[0] if emotion_names else 'neutral'

    emotion_titles = {
        'happy': ('😊 Happy Moments', 'Joyful times captured in photographs.'),
        'love': ('❤️ Moments of Love', 'Heartwarming memories filled with affection.'),
        'excited': ('🎉 Exciting Times', 'Days filled with anticipation and thrill.'),
        'sad': ('💙 Reflective Moments', 'Quiet times of reflection and emotion.'),
        'surprised': ('😮 Unexpected Moments', 'Surprising events and discoveries.'),
    }

    if dominant_emotion in emotion_titles:
        title, desc = emotion_titles[dominant_emotion]
        return {
            'title': title,
            'description': desc,
            'story_type': 'moments',
            'arc_type': 'general'
        }

    # Fallback: Generic temporal cluster
    return {
        'title': f'📸 {cluster[0].capture_date.strftime("%B")} Moments',
        'description': 'A collection of meaningful moments from this time.',
        'story_type': 'moments',
        'arc_type': 'general'
    }
