"""
Services module for business logic
"""
from .clip_classifier import get_classifier, classify_image_file, CLIPClassifier

__all__ = ['get_classifier', 'classify_image_file', 'CLIPClassifier']
