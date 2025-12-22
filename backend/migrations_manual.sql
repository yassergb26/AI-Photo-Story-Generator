-- ============================================================
-- Complete Architecture Migration SQL
-- Run this file manually using psql or pgAdmin
-- ============================================================

-- Step 1: Add new columns to images table
ALTER TABLE images
ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64) UNIQUE;

ALTER TABLE images
ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN DEFAULT FALSE;

ALTER TABLE images
ADD COLUMN IF NOT EXISTS original_image_id INTEGER REFERENCES images(id);

-- Step 2: Update life_events table structure
-- First backup any existing data if needed, then update columns
ALTER TABLE life_events
DROP COLUMN IF EXISTS start_date;

ALTER TABLE life_events
DROP COLUMN IF EXISTS end_date;

ALTER TABLE life_events
DROP COLUMN IF EXISTS location;

ALTER TABLE life_events
DROP COLUMN IF EXISTS detected_date;

ALTER TABLE life_events
ADD COLUMN IF NOT EXISTS event_date TIMESTAMP;

ALTER TABLE life_events
ADD COLUMN IF NOT EXISTS event_location VARCHAR(255);

ALTER TABLE life_events
ADD COLUMN IF NOT EXISTS detection_method VARCHAR(20) DEFAULT 'manual';

ALTER TABLE life_events
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Make event_name NOT NULL (only if you don't have NULL values)
-- ALTER TABLE life_events ALTER COLUMN event_name SET NOT NULL;

-- Step 3: Create life_event_images junction table
CREATE TABLE IF NOT EXISTS life_event_images (
    id SERIAL PRIMARY KEY,
    life_event_id INTEGER REFERENCES life_events(id) ON DELETE CASCADE NOT NULL,
    image_id INTEGER REFERENCES images(id) ON DELETE CASCADE NOT NULL,
    sequence_order INTEGER,
    is_cover_image BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(life_event_id, image_id)
);

-- Step 4: Recreate emotions tables
-- WARNING: This will drop existing emotions data!
DROP TABLE IF EXISTS image_emotions CASCADE;
DROP TABLE IF EXISTS story_emotions CASCADE;
DROP TABLE IF EXISTS emotions CASCADE;

-- Create new emotions table (predefined emotions)
CREATE TABLE emotions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    color_code VARCHAR(7),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Step 5: Create image_emotions junction table
CREATE TABLE image_emotions (
    id SERIAL PRIMARY KEY,
    image_id INTEGER REFERENCES images(id) ON DELETE CASCADE NOT NULL,
    emotion_id INTEGER REFERENCES emotions(id) ON DELETE CASCADE NOT NULL,
    confidence_score DECIMAL(5, 4) NOT NULL,
    face_count INTEGER DEFAULT 1,
    dominant_emotion BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(image_id, emotion_id)
);

-- Step 6: Create story_emotions table
CREATE TABLE story_emotions (
    id SERIAL PRIMARY KEY,
    story_id INTEGER REFERENCES stories(id) ON DELETE CASCADE NOT NULL,
    emotion_id INTEGER REFERENCES emotions(id) ON DELETE CASCADE NOT NULL,
    percentage DECIMAL(5, 2) NOT NULL,
    image_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(story_id, emotion_id)
);

-- Step 7: Create performance indexes
CREATE INDEX IF NOT EXISTS idx_images_file_hash ON images(file_hash);

CREATE INDEX IF NOT EXISTS idx_life_events_user_id ON life_events(user_id);
CREATE INDEX IF NOT EXISTS idx_life_events_event_type ON life_events(event_type);
CREATE INDEX IF NOT EXISTS idx_life_events_event_date ON life_events(event_date DESC);
CREATE INDEX IF NOT EXISTS idx_life_event_images_event_id ON life_event_images(life_event_id);
CREATE INDEX IF NOT EXISTS idx_life_event_images_image_id ON life_event_images(image_id);

CREATE INDEX IF NOT EXISTS idx_image_emotions_image_id ON image_emotions(image_id);
CREATE INDEX IF NOT EXISTS idx_image_emotions_emotion_id ON image_emotions(emotion_id);
CREATE INDEX IF NOT EXISTS idx_story_emotions_story_id ON story_emotions(story_id);

-- Step 8: Seed initial emotions data
INSERT INTO emotions (name, description, color_code) VALUES
('Happy', 'Smiling, cheerful expressions', '#FFD93D'),
('Excited', 'Energetic, enthusiastic expressions', '#FF6B6B'),
('Love', 'Affectionate, caring expressions', '#FD79A8'),
('Joy', 'Pure happiness, laughter', '#4ECDC4'),
('Surprised', 'Shocked, amazed expressions', '#A29BFE'),
('Neutral', 'Calm, relaxed expressions', '#95E1D3'),
('Reflective', 'Thoughtful, contemplative expressions', '#6C5CE7'),
('Sad', 'Melancholy, tearful expressions', '#74B9FF')
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- Migration Complete!
-- ============================================================
-- New features added:
--   - Duplicate image detection (SHA-256 hashing)
--   - Life events with image relationships
--   - Emotions system (predefined emotions)
--   - Image emotions with confidence scores
--   - Story emotions aggregation
--   - All performance indexes
-- ============================================================
