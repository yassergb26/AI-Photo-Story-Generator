"""
EXIF metadata extraction from images
"""
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def _convert_to_serializable(value):
    """
    Convert EXIF values to JSON-serializable types

    Args:
        value: EXIF value that may be IFDRational or other non-serializable type

    Returns:
        JSON-serializable value (int, float, str, list, etc.)
    """
    # Handle tuples (like GPS coordinates)
    if isinstance(value, tuple):
        return [_convert_to_serializable(v) for v in value]

    # Handle lists
    if isinstance(value, list):
        return [_convert_to_serializable(v) for v in value]

    # Handle IFDRational (has numerator and denominator)
    if hasattr(value, 'numerator') and hasattr(value, 'denominator'):
        # Convert to float
        if value.denominator == 0:
            return 0.0
        return float(value.numerator) / float(value.denominator)

    # Handle bytes
    if isinstance(value, bytes):
        try:
            decoded = value.decode('utf-8')
            # Remove null bytes that PostgreSQL can't handle
            return decoded.replace('\u0000', '0')
        except:
            return str(value)

    # Handle strings (remove null bytes)
    if isinstance(value, str):
        return value.replace('\u0000', '0')

    # Already serializable types
    if isinstance(value, (int, float, bool, type(None))):
        return value

    # Fallback to string representation
    return str(value)


def extract_exif_data(image_path: str) -> Dict[str, Any]:
    """
    Extract EXIF metadata from an image file

    Args:
        image_path: Path to the image file

    Returns:
        Dictionary containing extracted EXIF data
    """
    exif_data = {}

    try:
        image = Image.open(image_path)
        exif = image.getexif()

        if exif is None:
            logger.warning(f"No EXIF data found in {image_path}")
            return exif_data

        # Extract standard EXIF tags
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            exif_data[tag] = _convert_to_serializable(value)

        # Extract GPS data if available
        gps_ifd = exif.get_ifd(0x8825)  # GPS IFD tag
        if gps_ifd:
            gps_data = {}
            for key, value in gps_ifd.items():
                tag = GPSTAGS.get(key, key)
                gps_data[tag] = _convert_to_serializable(value)
            exif_data['GPSInfo'] = gps_data

        logger.info(f"Successfully extracted EXIF data from {image_path}")

    except Exception as e:
        logger.error(f"Error extracting EXIF from {image_path}: {str(e)}")

    return exif_data


def get_capture_date(exif_data: Dict[str, Any]) -> Optional[datetime]:
    """
    Extract capture date from EXIF data

    Args:
        exif_data: Dictionary of EXIF metadata

    Returns:
        datetime object or None
    """
    # Try different date fields in order of preference
    date_fields = ['DateTimeOriginal', 'DateTime', 'DateTimeDigitized']

    for field in date_fields:
        if field in exif_data:
            try:
                # Format: "YYYY:MM:DD HH:MM:SS"
                date_str = exif_data[field]
                return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            except Exception as e:
                logger.warning(f"Failed to parse date from {field}: {str(e)}")
                continue

    return None


def get_gps_coordinates(exif_data: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """
    Extract GPS coordinates from EXIF data

    Args:
        exif_data: Dictionary of EXIF metadata

    Returns:
        Tuple of (latitude, longitude) or None
    """
    if 'GPSInfo' not in exif_data:
        return None

    gps_info = exif_data['GPSInfo']

    try:
        # Extract latitude
        if 'GPSLatitude' in gps_info and 'GPSLatitudeRef' in gps_info:
            lat = _convert_to_degrees(gps_info['GPSLatitude'])
            if gps_info['GPSLatitudeRef'] == 'S':
                lat = -lat
        else:
            return None

        # Extract longitude
        if 'GPSLongitude' in gps_info and 'GPSLongitudeRef' in gps_info:
            lon = _convert_to_degrees(gps_info['GPSLongitude'])
            if gps_info['GPSLongitudeRef'] == 'W':
                lon = -lon
        else:
            return None

        return (lat, lon)

    except Exception as e:
        logger.error(f"Error extracting GPS coordinates: {str(e)}")
        return None


def _convert_to_degrees(value) -> float:
    """
    Convert GPS coordinates from degrees/minutes/seconds to decimal degrees

    Args:
        value: GPS coordinate in DMS format

    Returns:
        Decimal degrees
    """
    d, m, s = value
    return float(d) + (float(m) / 60.0) + (float(s) / 3600.0)


def get_camera_info(exif_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract camera information from EXIF data

    Args:
        exif_data: Dictionary of EXIF metadata

    Returns:
        Dictionary with camera make, model, etc.
    """
    camera_info = {}

    fields = {
        'Make': 'camera_make',
        'Model': 'camera_model',
        'LensModel': 'lens_model',
        'FocalLength': 'focal_length',
        'FNumber': 'aperture',
        'ExposureTime': 'shutter_speed',
        'ISOSpeedRatings': 'iso'
    }

    for exif_key, info_key in fields.items():
        if exif_key in exif_data:
            camera_info[info_key] = str(exif_data[exif_key])

    return camera_info
