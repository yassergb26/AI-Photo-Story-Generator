"""
Emotion Detection Service - Stub Implementation
This is a temporary stub to allow the system to load
Emotion detection functionality should be re-implemented with proper library
"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def detect_emotions(image_path: str) -> List[Dict]:
    """
    Stub function for emotion detection
    Returns empty list - emotion detection not currently implemented
    """
    logger.warning("Emotion detection called but not implemented - returning empty list")
    return []


def get_dominant_emotion(emotions_data: List[Dict]) -> Optional[Dict]:
    """
    Stub function to get dominant emotion
    Returns None - emotion detection not currently implemented
    """
    if not emotions_data:
        return None
    return emotions_data[0] if emotions_data else None


def aggregate_image_emotions(images: List) -> Dict[str, int]:
    """
    Stub function to aggregate emotions across images
    Returns empty dict - emotion detection not currently implemented
    """
    logger.warning("Emotion aggregation called but not implemented - returning empty dict")
    return {}
