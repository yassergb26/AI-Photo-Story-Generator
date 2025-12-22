"""
PDF generation utilities for exporting photos, stories, and life events
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak, Table, TableStyle
from reportlab.lib import colors
from PIL import Image
from datetime import datetime
import os
import tempfile
import logging

logger = logging.getLogger(__name__)


async def generate_photo_album_pdf(images, title="Photo Album", include_metadata=True):
    """
    Generate a PDF photo album from a list of images

    Args:
        images: List of Image model instances
        title: Title of the photo album
        include_metadata: Include dates and locations

    Returns:
        Path to generated PDF file
    """
    # Create temporary file for PDF
    temp_dir = tempfile.gettempdir()
    pdf_filename = f"photo_album_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(temp_dir, pdf_filename)

    # Create PDF document
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 0.3 * inch))

    # Subtitle with count and date
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    subtitle_text = f"{len(images)} photos • Generated on {datetime.now().strftime('%B %d, %Y')}"
    story.append(Paragraph(subtitle_text, subtitle_style))
    story.append(Spacer(1, 0.5 * inch))

    # Add each image
    for idx, image in enumerate(images, 1):
        try:
            # Get image path (remove './' prefix if present)
            img_path = image.file_path.replace('./', '')
            img_path = os.path.join(os.getcwd(), img_path)

            # Check if file exists
            if not os.path.exists(img_path):
                logger.warning(f"Image file not found: {img_path}")
                continue

            # Open image with PIL to get dimensions
            pil_img = Image.open(img_path)
            img_width, img_height = pil_img.size

            # Calculate scaled dimensions (max width 5 inches, max height 6 inches)
            max_width = 5 * inch
            max_height = 6 * inch

            aspect = img_width / img_height
            if img_width > img_height:
                display_width = min(max_width, img_width)
                display_height = display_width / aspect
                if display_height > max_height:
                    display_height = max_height
                    display_width = display_height * aspect
            else:
                display_height = min(max_height, img_height)
                display_width = display_height * aspect
                if display_width > max_width:
                    display_width = max_width
                    display_height = display_width / aspect

            # Add image to PDF
            rl_img = RLImage(img_path, width=display_width, height=display_height)
            story.append(rl_img)
            story.append(Spacer(1, 0.1 * inch))

            # Add metadata if requested
            if include_metadata:
                metadata_lines = []

                # Filename
                metadata_lines.append(f"<b>Filename:</b> {image.filename}")

                # Capture date
                if image.capture_date:
                    metadata_lines.append(
                        f"<b>Date:</b> {image.capture_date.strftime('%B %d, %Y at %I:%M %p')}"
                    )

                # Location
                if image.location:
                    location_parts = []
                    if image.location.location_name:
                        location_parts.append(image.location.location_name)
                    if image.location.city:
                        location_parts.append(image.location.city)
                    if image.location.country:
                        location_parts.append(image.location.country)

                    if location_parts:
                        metadata_lines.append(f"<b>Location:</b> {', '.join(location_parts)}")

                metadata_text = "<br/>".join(metadata_lines)
                metadata_style = ParagraphStyle(
                    'Metadata',
                    parent=styles['Normal'],
                    fontSize=9,
                    textColor=colors.grey
                )
                story.append(Paragraph(metadata_text, metadata_style))

            # Add separator between photos
            story.append(Spacer(1, 0.3 * inch))

            # Page break after every 2 photos
            if idx % 2 == 0 and idx < len(images):
                story.append(PageBreak())

        except Exception as e:
            logger.error(f"Error adding image {image.id} to PDF: {str(e)}")
            continue

    # Build PDF
    doc.build(story)
    logger.info(f"Generated PDF album at: {pdf_path}")

    return pdf_path


async def generate_story_pdf(story):
    """
    Generate a PDF for a single story with its images

    Args:
        story: Story model instance

    Returns:
        Path to generated PDF file
    """
    # Create temporary file for PDF
    temp_dir = tempfile.gettempdir()
    pdf_filename = f"story_{story.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(temp_dir, pdf_filename)

    # Create PDF document
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    pdf_story = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    pdf_story.append(Paragraph(story.title, title_style))
    pdf_story.append(Spacer(1, 0.2 * inch))

    # Story metadata
    metadata_lines = []
    if story.story_type:
        metadata_lines.append(f"<b>Type:</b> {story.story_type.replace('_', ' ').title()}")
    if story.start_date:
        date_str = story.start_date.strftime('%B %d, %Y')
        if story.end_date and story.end_date != story.start_date:
            date_str += f" - {story.end_date.strftime('%B %d, %Y')}"
        metadata_lines.append(f"<b>Date:</b> {date_str}")
    metadata_lines.append(f"<b>Photos:</b> {len(story.story_images)}")

    if metadata_lines:
        metadata_text = " • ".join(metadata_lines)
        metadata_style = ParagraphStyle(
            'Metadata',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        pdf_story.append(Paragraph(metadata_text, metadata_style))
        pdf_story.append(Spacer(1, 0.3 * inch))

    # Narrative
    narrative_style = ParagraphStyle(
        'Narrative',
        parent=styles['Normal'],
        fontSize=12,
        leading=18,
        spaceAfter=20
    )
    pdf_story.append(Paragraph(story.narrative, narrative_style))
    pdf_story.append(Spacer(1, 0.4 * inch))

    # Add story images
    for story_image in story.story_images:
        try:
            image = story_image.image

            # Get image path
            img_path = image.file_path.replace('./', '')
            img_path = os.path.join(os.getcwd(), img_path)

            if not os.path.exists(img_path):
                logger.warning(f"Image file not found: {img_path}")
                continue

            # Open image with PIL
            pil_img = Image.open(img_path)
            img_width, img_height = pil_img.size

            # Calculate scaled dimensions
            max_width = 5.5 * inch
            max_height = 4 * inch

            aspect = img_width / img_height
            if img_width > img_height:
                display_width = min(max_width, img_width)
                display_height = display_width / aspect
                if display_height > max_height:
                    display_height = max_height
                    display_width = display_height * aspect
            else:
                display_height = min(max_height, img_height)
                display_width = display_height * aspect
                if display_width > max_width:
                    display_width = max_width
                    display_height = display_width / aspect

            # Add image
            rl_img = RLImage(img_path, width=display_width, height=display_height)
            pdf_story.append(rl_img)
            pdf_story.append(Spacer(1, 0.2 * inch))

        except Exception as e:
            logger.error(f"Error adding image to story PDF: {str(e)}")
            continue

    # Build PDF
    doc.build(pdf_story)
    logger.info(f"Generated story PDF at: {pdf_path}")

    return pdf_path
