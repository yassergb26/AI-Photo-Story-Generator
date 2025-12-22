"""
File upload and storage handling
"""
import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
import aiofiles
import logging

logger = logging.getLogger(__name__)


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename"""
    return filename.split('.')[-1].lower() if '.' in filename else ''


def is_allowed_file(filename: str, allowed_extensions: list[str]) -> bool:
    """Check if file extension is allowed"""
    ext = get_file_extension(filename)
    return ext in [e.lower() for e in allowed_extensions]


def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename with UUID"""
    ext = get_file_extension(original_filename)
    unique_id = uuid.uuid4().hex
    return f"{unique_id}.{ext}"


async def save_upload_file(
    upload_file: UploadFile,
    upload_dir: str,
    max_size: int
) -> tuple[str, int]:
    """
    Save uploaded file to disk

    Args:
        upload_file: FastAPI UploadFile object
        upload_dir: Directory to save file
        max_size: Maximum file size in bytes

    Returns:
        Tuple of (file_path, file_size)

    Raises:
        ValueError: If file is too large or invalid
    """
    # Create upload directory if it doesn't exist
    Path(upload_dir).mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    unique_filename = generate_unique_filename(upload_file.filename)
    file_path = os.path.join(upload_dir, unique_filename)

    # Save file in chunks
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks

    try:
        async with aiofiles.open(file_path, 'wb') as f:
            while True:
                chunk = await upload_file.read(chunk_size)
                if not chunk:
                    break

                file_size += len(chunk)

                # Check file size limit
                if file_size > max_size:
                    # Delete partially written file
                    os.remove(file_path)
                    raise ValueError(f"File size exceeds maximum allowed size of {max_size} bytes")

                await f.write(chunk)

        logger.info(f"Saved file: {file_path} ({file_size} bytes)")
        return file_path, file_size

    except Exception as e:
        # Clean up on error
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Error saving file: {str(e)}")
        raise


def delete_file(file_path: str) -> bool:
    """
    Delete a file from disk

    Args:
        file_path: Path to file to delete

    Returns:
        True if successful, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted file: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        return False
