"""
AI Narrative Generation Service
Uses OpenAI GPT-4 to generate rich, personalized chapter and story arc narratives
"""
from openai import OpenAI
import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def generate_chapter_narrative(chapter_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate rich narrative for a chapter using OpenAI GPT-4

    Args:
        chapter_data: Dictionary containing:
            - chapter_type: 'age_based' or 'year_based'
            - age_start, age_end: Age range (if age_based)
            - year_start, year_end: Year range
            - photo_count: Number of photos
            - dominant_emotion: Main emotion in photos
            - life_phase: Life phase name (e.g., "Building a Life")
            - life_events: List of life events in this chapter
            - story_arcs: List of story arc titles

    Returns:
        Dictionary with:
            - title: Short, evocative title (2-4 words)
            - subtitle: One compelling sentence
            - description: 2-3 sentence narrative
    """
    try:
        # Build context for the prompt
        if chapter_data.get('chapter_type') == 'age_based':
            time_period = f"ages {chapter_data['age_start']}-{chapter_data['age_end']} ({chapter_data['year_start']}-{chapter_data['year_end']})"
            life_phase = chapter_data.get('life_phase', '')
        else:
            if chapter_data['year_start'] == chapter_data['year_end']:
                time_period = f"the year {chapter_data['year_start']}"
            else:
                time_period = f"{chapter_data['year_start']}-{chapter_data['year_end']}"
            life_phase = "Life Journey"

        # Build life events string
        life_events_str = ""
        if chapter_data.get('life_events'):
            events = [f"- {event}" for event in chapter_data['life_events']]
            life_events_str = f"\nKey Life Events:\n" + "\n".join(events)

        # Build story arcs string
        story_arcs_str = ""
        if chapter_data.get('story_arcs'):
            arcs = [f"- {arc}" for arc in chapter_data['story_arcs']]
            story_arcs_str = f"\nStory Arcs:\n" + "\n".join(arcs)

        prompt = f"""You are writing a chapter title and description for a photo album.

Context:
- Time Period: {time_period}
- Life Phase: {life_phase}
- Number of Photos: {chapter_data['photo_count']}
- Dominant Emotion: {chapter_data.get('dominant_emotion', 'Joy')}
{life_events_str}
{story_arcs_str}

Create a compelling chapter narrative in JSON format:
{{
    "title": "Short, evocative title (2-4 words) that captures the essence of this period",
    "subtitle": "One compelling sentence that summarizes this chapter",
    "description": "2-3 sentence narrative written in third person that tells the story of this chapter with emotional depth"
}}

Make it personal, warm, and evocative. Focus on the emotions and experiences, not just facts.
Examples of good titles: "City Dreams", "Building a Family", "Golden Moments", "New Beginnings"
Write the description as if telling a story about the person's life."""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a creative writer specializing in personal narratives and photo album storytelling."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=300,
            response_format={"type": "json_object"}
        )

        # Parse response
        narrative = json.loads(response.choices[0].message.content)

        logger.info(f"Generated narrative for chapter: {narrative.get('title')}")

        return {
            'title': narrative.get('title', life_phase),
            'subtitle': narrative.get('subtitle', ''),
            'description': narrative.get('description', '')
        }

    except Exception as e:
        logger.error(f"Error generating chapter narrative: {str(e)}")

        # Fallback to template-based narrative
        if chapter_data.get('chapter_type') == 'age_based':
            title = chapter_data.get('life_phase', 'Life Journey')
            subtitle = f"Ages {chapter_data['age_start']}-{chapter_data['age_end']}"
        else:
            if chapter_data['year_start'] == chapter_data['year_end']:
                title = f"Life in {chapter_data['year_start']}"
            else:
                title = f"Memories {chapter_data['year_start']}-{chapter_data['year_end']}"
            subtitle = f"{chapter_data['photo_count']} cherished moments"

        return {
            'title': title,
            'subtitle': subtitle,
            'description': f"A collection of {chapter_data['photo_count']} photos capturing life's precious moments."
        }


def generate_story_arc_title_and_narrative(arc_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate BOTH title AND description for a story arc using OpenAI GPT-4
    Based on actual photo content (classifications + emotions)

    Args:
        arc_data: Dictionary containing:
            - categories: List of image classifications
            - emotions: List of detected emotions
            - photo_count: Number of photos
            - start_date, end_date: Date range
            - temporal_span_days: Duration in days

    Returns:
        Dictionary with 'title' and 'description'
    """
    try:
        # Build context from classifications and emotions
        categories_str = ", ".join(arc_data.get('categories', []))
        emotions_str = ", ".join(arc_data.get('emotions', []))

        date_range = ""
        if arc_data.get('start_date'):
            date_range = f"\nDate: {arc_data['start_date'].strftime('%B %d, %Y')}"
            if arc_data.get('end_date') and arc_data['end_date'] != arc_data['start_date']:
                date_range += f" - {arc_data['end_date'].strftime('%B %d, %Y')}"
                duration = arc_data.get('temporal_span_days', 0)
                if duration > 0:
                    date_range += f" ({duration} days)"

        prompt = f"""Create a story arc for a collection of {arc_data['photo_count']} photos with these characteristics:

Visual Content (Classifications): {categories_str}
Emotional Context (Detected Emotions): {emotions_str}
{date_range}

Generate a JSON response with:
1. "title": A creative, evocative title (2-6 words) with an appropriate emoji that captures the essence of these photos
2. "description": A warm, personal description (2-3 sentences) in third person

The title should reflect what these photos represent based on the visual content and emotions.
Examples: "🏖️ Coastal Adventures", "👥 Friends Forever", "🎨 Creative Expressions", "🏕️ Mountain Escape"

Return ONLY valid JSON in this exact format:
{{
  "title": "emoji + creative title",
  "description": "warm, personal description"
}}"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a creative writer specializing in personal photo album narratives. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=150,  # Reduced for faster response
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        logger.info(f"✓ AI generated title: {result.get('title')}")
        return {
            'title': result.get('title', 'Memories'),
            'description': result.get('description', '')
        }

    except Exception as e:
        logger.error(f"Error generating AI title and narrative: {str(e)}")
        # Fallback to template-based
        return {
            'title': f"📸 {arc_data.get('start_date', datetime.now()).strftime('%B')} Moments",
            'description': f"A collection of {arc_data.get('photo_count', 0)} memorable photos."
        }


def generate_story_arc_narrative(arc_data: Dict[str, Any]) -> str:
    """
    Generate description for a story arc using OpenAI GPT-4

    Args:
        arc_data: Dictionary containing:
            - title: Arc title
            - arc_type: 'event', 'trip', 'milestone', 'tradition'
            - photo_count: Number of photos
            - start_date, end_date: Date range
            - location: Location name (if applicable)

    Returns:
        2-3 sentence narrative description
    """
    try:
        # Build context
        if arc_data.get('location'):
            location_str = f"\nLocation: {arc_data['location']}"
        else:
            location_str = ""

        date_range = ""
        if arc_data.get('start_date'):
            date_range = f"\nDate: {arc_data['start_date'].strftime('%B %d, %Y')}"
            if arc_data.get('end_date') and arc_data['end_date'] != arc_data['start_date']:
                date_range += f" - {arc_data['end_date'].strftime('%B %d, %Y')}"

        prompt = f"""Write a short, evocative description (2-3 sentences) for a photo album story:

Title: {arc_data['title']}
Type: {arc_data['arc_type']}
Photos: {arc_data['photo_count']}
{date_range}
{location_str}

Write in third person, focusing on emotions and experiences. Make it personal and warm.
Return only the description text, no JSON."""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a creative writer specializing in personal narratives."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=150
        )

        description = response.choices[0].message.content.strip()

        logger.info(f"Generated narrative for story arc: {arc_data['title']}")

        return description

    except Exception as e:
        logger.error(f"Error generating story arc narrative: {str(e)}")

        # Fallback description
        return f"A memorable collection of {arc_data['photo_count']} photos capturing special moments."


async def enhance_chapter_with_ai_narrative(chapter, story_arcs, db):
    """
    Enhance a chapter with AI-generated narrative

    Args:
        chapter: Chapter model instance
        story_arcs: List of Story model instances in this chapter
        db: Database session
    """
    try:
        # Prepare chapter data
        chapter_data = {
            'chapter_type': chapter.chapter_type,
            'age_start': chapter.age_start,
            'age_end': chapter.age_end,
            'year_start': chapter.year_start,
            'year_end': chapter.year_end,
            'photo_count': chapter.photo_count,
            'dominant_emotion': chapter.dominant_emotion,
            'life_phase': chapter.title,  # Current title is life phase
            'life_events': [],
            'story_arcs': []
        }

        # Extract life events and story arc titles
        for arc in story_arcs:
            if arc.generation_source == 'life_event':
                chapter_data['life_events'].append(arc.title)
            chapter_data['story_arcs'].append(arc.title)

        # Generate narrative
        narrative = generate_chapter_narrative(chapter_data)

        # Update chapter
        chapter.title = narrative['title']
        chapter.subtitle = narrative['subtitle']
        chapter.description = narrative['description']

        db.commit()
        db.refresh(chapter)

        logger.info(f"Enhanced chapter {chapter.id} with AI narrative: {chapter.title}")

        return chapter

    except Exception as e:
        logger.error(f"Error enhancing chapter with AI narrative: {str(e)}")
        return chapter


async def enhance_story_arc_with_ai_narrative(story_arc, db):
    """
    Enhance a story arc with AI-generated description

    Args:
        story_arc: Story model instance
        db: Database session
    """
    try:
        # Prepare arc data
        arc_data = {
            'title': story_arc.title,
            'arc_type': story_arc.arc_type,
            'photo_count': story_arc.photo_count,
            'start_date': story_arc.start_date,
            'end_date': story_arc.end_date,
            'location': story_arc.story_metadata.get('location_name') if story_arc.story_metadata else None
        }

        # Generate narrative
        description = generate_story_arc_narrative(arc_data)

        # Update story arc
        story_arc.description = description

        db.commit()
        db.refresh(story_arc)

        logger.info(f"Enhanced story arc {story_arc.id} with AI narrative")

        return story_arc

    except Exception as e:
        logger.error(f"Error enhancing story arc with AI narrative: {str(e)}")
        return story_arc


def generate_narrative(
    story_metadata: Dict[str, Any],
    narrative_tone: str = "joyful",
    pattern_type: str = "visual",
    use_llm: bool = True
) -> Dict[str, str]:
    """
    Wrapper function for backwards compatibility with stories router
    Generates narrative using existing AI narrative functions

    Args:
        story_metadata: Story metadata dictionary
        narrative_tone: Desired tone (default: joyful)
        pattern_type: Type of pattern (default: visual)
        use_llm: Whether to use LLM (default: True)

    Returns:
        Dictionary with title, description, and tone
    """
    # Use the existing story arc generation function
    result = generate_story_arc_title_and_narrative(story_metadata)

    # Add tone to response
    result['tone'] = narrative_tone

    return result
