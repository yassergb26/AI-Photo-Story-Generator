"""
Thumbnail generation utilities
"""
from PIL import Image
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

THUMBNAIL_SIZE = (200, 200)
THUMBNAIL_DIR = "./thumbnails"


def ensure_thumbnail_dir():
    """Create thumbnail directory if it doesn't exist"""
    Path(THUMBNAIL_DIR).mkdir(parents=True, exist_ok=True)


def generate_thumbnail(image_path: str, thumbnail_path: str = None) -> str:
    """
    Generate a thumbnail for an image

    Args:
        image_path: Path to the original image
        thumbnail_path: Optional path for the thumbnail. If not provided,
                       will be generated in thumbnail directory

    Returns:
        Path to the generated thumbnail

    Raises:
        Exception if thumbnail generation fails
    """
    try:
        ensure_thumbnail_dir()

        # Open image
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (handles PNG with alpha, etc.)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')

            # Generate thumbnail with faster resampling for better performance
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.BILINEAR)

            # Determine output path
            if thumbnail_path is None:
                filename = os.path.basename(image_path)
                name, ext = os.path.splitext(filename)
                thumbnail_path = os.path.join(THUMBNAIL_DIR, f"{name}_thumb{ext}")

            # Save thumbnail with faster settings
            img.save(thumbnail_path, quality=75, optimize=False)

            logger.info(f"Generated thumbnail: {thumbnail_path}")
            return thumbnail_path

    except Exception as e:
        logger.error(f"Error generating thumbnail for {image_path}: {e}")
        raise


def delete_thumbnail(thumbnail_path: str):
    """Delete a thumbnail file"""
    try:
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            logger.info(f"Deleted thumbnail: {thumbnail_path}")
    except Exception as e:
        logger.error(f"Error deleting thumbnail {thumbnail_path}: {e}")
