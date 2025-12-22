"""
Duplicate image detection utilities using SHA-256 hashing
"""
import hashlib
import os
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Image


def calculate_file_hash(file_path: str) -> str:
    """
    Calculate SHA-256 hash of file contents for duplicate detection

    Args:
        file_path: Path to image file

    Returns:
        Hexadecimal hash string (64 characters)
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Read file in chunks to handle large images
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def check_duplicate_image(db: Session, user_id: int, file_hash: str) -> Optional[Image]:
    """
    Check if image hash already exists for this user

    Args:
        db: Database session
        user_id: User ID
        file_hash: SHA-256 hash of image file

    Returns:
        Existing image if duplicate found, None otherwise
    """
    existing_image = db.query(Image).filter(
        Image.user_id == user_id,
        Image.file_hash == file_hash
    ).first()

    return existing_image


def is_duplicate(file_path: str, db: Session, user_id: int) -> tuple[bool, Optional[Image]]:
    """
    Check if a file is a duplicate

    Args:
        file_path: Path to the file to check
        db: Database session
        user_id: User ID

    Returns:
        Tuple of (is_duplicate: bool, original_image: Optional[Image])
    """
    # Calculate hash
    file_hash = calculate_file_hash(file_path)

    # Check for duplicate
    existing = check_duplicate_image(db, user_id, file_hash)

    if existing:
        return True, existing

    return False, None
