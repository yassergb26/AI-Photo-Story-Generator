"""
CLIP-based Image Classification Service
Multi-label categorization with confidence scoring
"""
import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import logging
from typing import List, Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class CLIPClassifier:
    """
    CLIP model wrapper for image categorization
    Uses zero-shot classification with predefined categories
    """

    # Predefined event categories with detailed descriptions
    CATEGORIES = {
        "Celebrations": "a photo of birthday party, wedding, anniversary, graduation, holiday celebration, festive event",
        "Travel & Adventures": "a photo of vacation, trip, tourism, adventure, landmark, scenic view, travel destination",
        "Family & Friends": "a photo of family gathering, friends meeting, group photo, social event, reunion",
        "Nature & Outdoors": "a photo of landscape, mountains, forest, beach, sunset, wildlife, outdoor scenery",
        "Food & Dining": "a photo of restaurant, food, meal, cooking, dining, culinary experience",
        "Work & Professional": "a photo of office, workplace, business meeting, conference, professional event",
        "Hobbies & Activities": "a photo of sports, hobbies, exercise, recreational activity, entertainment",
        "Pets & Animals": "a photo of pet, dog, cat, animal, wildlife, animal companion"
    }

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", device: str = None):
        """
        Initialize CLIP model and processor

        Args:
            model_name: Hugging Face model identifier
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
        """
        self.model_name = model_name

        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Initializing CLIP model: {model_name} on {self.device}")

        # Load model and processor
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.eval()  # Set to evaluation mode

        # Prepare category prompts
        self.category_names = list(self.CATEGORIES.keys())
        self.category_prompts = list(self.CATEGORIES.values())

        logger.info(f"CLIP model loaded successfully with {len(self.category_names)} categories")

    def classify_image(
        self,
        image_path: str,
        threshold: float = 0.15,
        top_k: int = 3
    ) -> List[Dict[str, any]]:
        """
        Classify an image into multiple categories with confidence scores

        Args:
            image_path: Path to the image file
            threshold: Minimum confidence threshold (0-1)
            top_k: Maximum number of categories to return

        Returns:
            List of dictionaries with category name and confidence score
            [{"category": "Travel & Adventures", "confidence": 0.85}, ...]
        """
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert("RGB")

            # Prepare inputs
            inputs = self.processor(
                text=self.category_prompts,
                images=image,
                return_tensors="pt",
                padding=True
            ).to(self.device)

            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)

            # Convert to CPU and extract scores
            scores = probs[0].cpu().numpy()

            # Create results with category names and scores
            results = []
            for idx, score in enumerate(scores):
                if score >= threshold:
                    results.append({
                        "category": self.category_names[idx],
                        "confidence": float(score)
                    })

            # Sort by confidence and return top_k
            results.sort(key=lambda x: x["confidence"], reverse=True)
            results = results[:top_k]

            logger.info(f"Classified image {Path(image_path).name}: {len(results)} categories")
            return results

        except Exception as e:
            logger.error(f"Error classifying image {image_path}: {str(e)}")
            return []

    def batch_classify(
        self,
        image_paths: List[str],
        threshold: float = 0.15,
        top_k: int = 3
    ) -> Dict[str, List[Dict[str, any]]]:
        """
        Classify multiple images in batch

        Args:
            image_paths: List of image file paths
            threshold: Minimum confidence threshold
            top_k: Maximum categories per image

        Returns:
            Dictionary mapping image paths to classification results
        """
        results = {}
        for image_path in image_paths:
            results[image_path] = self.classify_image(image_path, threshold, top_k)
        return results

    @classmethod
    def get_category_info(cls) -> Dict[str, str]:
        """
        Get information about available categories

        Returns:
            Dictionary of category names and descriptions
        """
        return cls.CATEGORIES.copy()

    def get_model_info(self) -> Dict[str, any]:
        """
        Get information about the loaded model

        Returns:
            Dictionary with model metadata
        """
        return {
            "model_name": self.model_name,
            "device": self.device,
            "categories": self.category_names,
            "num_categories": len(self.category_names)
        }


# Global classifier instance (singleton pattern)
_classifier_instance = None


def get_classifier() -> CLIPClassifier:
    """
    Get or create the global classifier instance
    Implements lazy loading for better startup performance

    Returns:
        CLIPClassifier instance
    """
    global _classifier_instance
    if _classifier_instance is None:
        logger.info("Creating CLIP classifier instance")
        _classifier_instance = CLIPClassifier()
    return _classifier_instance


def classify_image_file(
    image_path: str,
    threshold: float = 0.15,
    top_k: int = 3
) -> List[Dict[str, any]]:
    """
    Convenience function to classify a single image

    Args:
        image_path: Path to image file
        threshold: Minimum confidence threshold
        top_k: Maximum categories to return

    Returns:
        List of classification results
    """
    classifier = get_classifier()
    return classifier.classify_image(image_path, threshold, top_k)
