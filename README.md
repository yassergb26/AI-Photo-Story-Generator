# 📸 AI-Powered Photo Story Generation System

An intelligent system that transforms your photo collection into meaningful life stories using AI-powered image classification, emotion detection, and narrative generation.

---

## 🌟 Features

### Core Capabilities
- **🤖 AI Image Classification** - Automatically categorizes photos using OpenAI's CLIP model
- **😊 Emotion Detection** - Detects facial emotions using HSEmotion (Happiness, Neutral, Surprise, Sadness, Anger, Disgust, Fear, Contempt)
- **📖 Smart Chapter Generation** - Organizes photos into life chapters based on age ranges
- **✨ Story Arc Detection** - Intelligently groups photos into meaningful story arcs using:
  - Temporal clustering (date proximity)
  - **DBSCAN spatial clustering with Haversine distance** for geographic location grouping
  - Visual similarity (CLIP classifications)
  - Emotional context (detected emotions)
- **🎯 GPT-4 Narrative Generation** - Creates creative titles and descriptions for chapters and stories
- **🔍 Pattern Detection** - Discovers temporal, spatial, and visual patterns in your photos

### Production Features
- **⚡ Async Task Processing** - Celery+Redis pipeline for long-running operations
- **📊 Task Status Tracking** - Real-time progress monitoring for background tasks
- **🚦 Rate Limiting** - IP-based rate limits to prevent API abuse
- **💾 Redis Caching** - Fast API responses with automatic cache invalidation
- **📍 Geographic Clustering** - DBSCAN algorithm with Haversine distance for location-based photo grouping
- **📄 Paginated APIs** - Efficient data loading for large photo collections

### User Experience
- **One-Click Auto Mode** - Complete processing pipeline in a single click
- **Interactive Gallery** - Browse photos with categories, emotions, and metadata
- **Chapter View** - Navigate your life story through organized chapters
- **Story Details** - Expand story arcs to see photos and AI-generated narratives
- **Admin Panel** - Manage photos, chapters, and system settings

---

## 🏗️ Architecture

### Backend (FastAPI + Python)
```
backend/
├── app/
│   ├── routers/          # API endpoints
│   │   ├── photos.py     # Photo upload & management
│   │   ├── chapters.py   # Chapter & auto-mode generation
│   │   ├── classifications.py
│   │   ├── emotions.py
│   │   ├── patterns.py
│   │   └── stories.py
│   ├── services/         # Business logic
│   │   ├── ai_story_arc_detector.py     # Unified pattern detection
│   │   ├── chapter_generator.py          # Chapter creation
│   │   ├── ai_narrative.py               # GPT-4 integration
│   │   ├── clip_classifier.py            # Image classification
│   │   └── emotion_detector.py           # Emotion detection
│   ├── models.py         # Database models
│   ├── database.py       # PostgreSQL connection
│   └── config.py         # Configuration
├── main.py               # Application entry point
└── venv/                 # Python virtual environment
```

### Frontend (React + Vite)
```
frontend/
├── src/
│   ├── components/
│   │   ├── ImageUpload.jsx       # Upload & auto mode
│   │   ├── ImageGallery.jsx      # Photo grid display
│   │   ├── ChapterView.jsx       # Chapters & story arcs
│   │   ├── PhotoMetadata.jsx     # Photo details
│   │   └── AdminPanel.jsx        # System management
│   ├── App.jsx           # Main application
│   └── main.jsx          # React entry point
└── package.json          # Dependencies
```

### Database (PostgreSQL)
- **Users** - User profiles with birth dates
- **Images** - Photo metadata, file paths, embeddings
- **Categories** - Classification labels (Beach, Family & Friends, etc.)
- **Emotions** - Emotion types (Happiness, Neutral, etc.)
- **ImageCategory** - Photo-to-category mappings
- **ImageEmotion** - Photo-to-emotion mappings
- **Chapters** - Life chapters with age ranges
- **Stories** - Story arcs within chapters
- **StoryImage** - Photo-to-story associations
- **Patterns** - Detected temporal/spatial/visual patterns

---

## 🚀 Getting Started

### Prerequisites

**1. Python 3.11+**
```bash
python --version  # Should be 3.11 or higher
```

**2. Node.js 18+**
```bash
node --version  # Should be 18.0.0 or higher
npm --version
```

**3. PostgreSQL 14+**
- Install PostgreSQL from https://www.postgresql.org/download/
- Create a database named `photo_story_db`

**4. Redis Server**
- Install Redis from https://redis.io/download
- Required for async task processing and caching
- Windows: https://github.com/microsoftarchive/redis/releases
- Mac: `brew install redis`
- Linux: `sudo apt install redis-server`

**5. API Keys**
- **OpenAI API Key** - Required for CLIP classification and GPT-4 narratives
  - Get from: https://platform.openai.com/api-keys
  - Set as environment variable: `OPENAI_API_KEY`

---

### Installation

**1. Clone the Repository**
```bash
git clone <repository-url>
cd 
```

**2. Backend Setup**

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your configuration
# (See Backend Configuration section below)
```

**3. Frontend Setup**

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

**4. Database Setup**

```bash
# Create PostgreSQL database
psql -U postgres
CREATE DATABASE photo_story_db;
\q

# Database tables will be created automatically on first run
```

---

### Configuration

**Backend Configuration** (`backend/.env`)

Create a `.env` file in the `backend/` directory:

```env
# Database
DATABASE_URL=postgresql://postgres:your_password@localhost/photo_story_db

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key-here

# Application
API_HOST=localhost
API_PORT=8000
DEBUG=true

# Upload Settings
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=10485760  # 10MB

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Logging
LOG_LEVEL=INFO
```

**Frontend Configuration** (`frontend/.env`)

```env
VITE_API_URL=http://localhost:8000
```

---

### Running the Application

**1. Start Redis Server**

```bash
# Windows (from Redis installation directory)
redis-server

# Mac
brew services start redis

# Linux
sudo service redis-server start

# Or run directly
redis-server
```

**2. Start Celery Worker** (Optional - for async processing)

```bash
# From backend directory (new terminal)
cd backend
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

celery -A app.celery_app worker --loglevel=info --pool=solo
```

**3. Start Backend**

```bash
# From backend directory (new terminal)
cd backend
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

python main.py
```

Backend will start at: http://localhost:8000

**4. Start Frontend**

```bash
# From frontend directory (new terminal)
cd frontend
npm run dev
```

Frontend will start at: http://localhost:5173

**5. Access the Application**

Open your browser to: http://localhost:5173

---

## 📖 Usage Guide

### First Time Setup

1. **Set Birth Date**
   - Go to "Chapters" tab
   - Click "Set Birth Date"
   - Enter your birth date (required for age-based chapters)

2. **Upload Photos**
   - Go to upload section
   - Drag & drop photos or click to select
   - Upload 50-500+ photos for best results

3. **Run Auto Mode**
   - Scroll to "Auto Mode (Full Demo Pipeline)" section
   - Click "🚀 Run Auto Mode"
   - Wait for processing (3-10 minutes depending on photo count)

### What Auto Mode Does

Auto Mode runs the complete AI pipeline:

1. **Spread Dates** - Distributes photos across your lifetime
2. **Classify Images** - AI categorizes each photo (Family & Friends, Beach, Outdoor, etc.)
3. **Detect Emotions** - Analyzes facial emotions in photos
4. **Detect Patterns** - Finds temporal, spatial, and visual patterns
5. **Generate Chapters** - Creates age-based life chapters
6. **Detect Story Arcs** - Groups photos into meaningful stories using unified AI detection
7. **AI Narratives** - Generates creative titles and descriptions with GPT-4

### Viewing Results

**Gallery View**
- See all photos with categories and emotions
- Click photos to see detailed metadata
- Filter and search capabilities

**Chapters View**
- Browse life chapters (Early Childhood, Teenage Years, etc.)
- Each chapter shows:
  - AI-generated title and description
  - Photo count and dominant emotion
  - Story arcs within the chapter
- Expand chapters to see story arcs
- Expand story arcs to see photos and narratives

**Story Arc Details**
- AI-generated creative title (e.g., "🎢 Life's Rollercoaster", "🏖️ Coastal Adventures")
- Warm, personal description
- Photo count and date range
- Photo thumbnails
- Classifications and emotions detected

---

## 🤖 AI Models Used

### 1. CLIP (OpenAI)
- **Purpose**: Image classification
- **Model**: `openai/clip-vit-base-patch32`
- **Categories**: 30+ predefined categories including:
  - Family & Friends
  - Beach/Ocean
  - Outdoor/Nature
  - Celebration/Party
  - Food/Dining
  - Pets
  - Travel
  - Sports/Activity

### 2. HSEmotion
- **Purpose**: Facial emotion detection
- **Model**: `savrasovmv/hsemotion-enet-b0-8`
- **Emotions Detected**:
  - Happiness (😊)
  - Neutral (😐)
  - Surprise (😮)
  - Sadness (😢)
  - Anger (😠)
  - Disgust (🤢)
  - Fear (😨)
  - Contempt (😒)

### 3. GPT-4 Turbo (OpenAI)
- **Purpose**: Creative narrative generation
- **Model**: `gpt-4-turbo-preview`
- **Features**:
  - JSON mode for structured output
  - Creative chapter titles and descriptions
  - Story arc titles based on photo content
  - Warm, personal storytelling style

---

## 🔧 API Endpoints

### Photos
- `POST /api/photos/upload` - Upload photos (Rate limited: 10/minute)
- `GET /api/photos` - List photos with pagination (Redis cached)
- `GET /api/photos/{id}` - Get photo details
- `DELETE /api/photos/{id}` - Delete photo

### Tasks (Async Processing)
- `GET /api/tasks/{task_id}` - Get task status and progress (Rate limited: 60/minute)
- `DELETE /api/tasks/{task_id}` - Cancel running task
- `GET /api/tasks/` - List active tasks

### Chapters
- `GET /api/chapters` - List chapters
- `POST /api/chapters/auto-generate` - Run complete Auto Mode pipeline
- `POST /api/chapters/set-birth-date` - Set user birth date
- `DELETE /api/chapters/{id}` - Delete chapter

### Classifications
- `POST /api/classifications/classify-image` - Classify single image (can trigger async task)
- `GET /api/classifications` - Get classifications for image

### Emotions
- `POST /api/emotions/detect` - Detect emotions in image
- `GET /api/emotions` - Get emotions for image

### Patterns
- `POST /api/patterns/detect-temporal` - Detect temporal patterns
- `POST /api/patterns/detect-spatial` - Detect spatial patterns (uses DBSCAN)
- `POST /api/patterns/detect-visual` - Detect visual patterns

### Stories
- `GET /api/stories` - List story arcs
- `GET /api/stories/{id}` - Get story details

---

## ⚡ Async Task Processing

### Overview
The system uses Celery+Redis for background processing of long-running operations. This allows the API to return immediately while tasks run asynchronously.

### Available Async Tasks

1. **Image Classification** (`classify_image_task`)
   - Processes a single image with CLIP model
   - Returns categories with confidence scores
   - Saves results to database

2. **Emotion Detection** (`detect_emotions_task`)
   - Detects facial emotions in image
   - Returns dominant emotion and all detected emotions
   - Saves results to database

3. **Batch Processing** (`process_image_batch`)
   - Processes multiple images in parallel
   - Tracks progress (current/total)
   - Returns aggregate results

4. **Story Arc Generation** (`generate_story_arcs_task`)
   - Analyzes photos for patterns
   - Uses DBSCAN for location clustering
   - Creates story arcs with AI narratives

### Monitoring Task Progress

```python
# Submit async task
response = requests.post('/api/photos/upload', files=files)
task_id = response.json()['task_id']

# Check task status
status = requests.get(f'/api/tasks/{task_id}')
print(status.json())
# {
#   "task_id": "abc123",
#   "state": "PROCESSING",
#   "progress": 45,
#   "current": 45,
#   "total": 100
# }

# Cancel task if needed
requests.delete(f'/api/tasks/{task_id}')
```

### Testing Async Processing

```bash
# Start services
cd backend
python test_celery.py

# Expected output:
# ✅ Redis connection successful!
# ✅ Task was received and executed by worker!
# ✅ All tests passed! Async processing is ready.
```

---

## 🧪 Testing

### Testing the Complete Pipeline

1. **Clean Slate**
   - Go to Admin panel
   - Click "Delete All Photos"
   - Click "Delete All Chapters"

2. **Upload Test Photos**
   - Use a collection of 50-100 photos
   - Include variety: people, places, events

3. **Run Auto Mode**
   - Click "🚀 Run Auto Mode"
   - Monitor backend console for progress

4. **Verify Results**
   - Gallery: Photos have categories and emotions
   - Chapters: 6 age-based chapters created
   - Stories: Multiple story arcs with AI-generated titles
   - Check story arc details for accuracy

### Expected Performance

**For 100 photos:**
- Upload: ~30 seconds
- Auto Mode: ~3-5 minutes
- Expected Output:
  - 6 chapters
  - 10-20 story arcs
  - All photos classified and emotion-detected

**For 425 photos:**
- Upload: ~2 minutes
- Auto Mode: ~8-12 minutes
- Expected Output:
  - 6 chapters
  - 25-40 story arcs
  - Comprehensive coverage of life events

---

## 📊 System Requirements

### Minimum Requirements
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Storage**: 20 GB free space (for photos and models)
- **GPU**: Not required (CPU inference supported)

### Recommended Requirements
- **CPU**: 8+ cores
- **RAM**: 16 GB
- **Storage**: 50 GB+ free space
- **GPU**: NVIDIA GPU with CUDA support (for faster processing)

### Network
- Stable internet connection for OpenAI API calls
- ~1-2 MB per story arc for GPT-4 API calls

---

## 🛠️ Troubleshooting

### Backend Won't Start
**Issue**: `ModuleNotFoundError` or import errors

**Solution**:
```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
```

### Database Connection Error
**Issue**: `psycopg2.OperationalError: could not connect to server`

**Solution**:
1. Verify PostgreSQL is running
2. Check DATABASE_URL in `.env`
3. Ensure database exists: `CREATE DATABASE photo_story_db;`

### OpenAI API Errors
**Issue**: `AuthenticationError` or rate limit errors

**Solution**:
1. Verify OPENAI_API_KEY in `.env`
2. Check API key at https://platform.openai.com/api-keys
3. Ensure you have credits/billing enabled
4. Rate limits: Wait and retry

### Auto Mode Stuck/Timeout
**Issue**: Auto Mode takes too long or appears stuck

**Solution**:
1. Check backend console for progress logs
2. Each GPT-4 call takes ~10-15 seconds (normal)
3. For 30 story arcs: expect 5-8 minutes total
4. Look for error messages in console

### No Story Arcs Created
**Issue**: Auto Mode completes but `story_arcs_count: 0`

**Solution**:
1. Ensure photos are classified (check Gallery view)
2. Ensure emotions are detected (check photo details)
3. Backend logs should show "UNIFIED AI pattern detection on X photos"
4. If still failing, restart backend to reload code

### Photos Not Uploading
**Issue**: Upload fails or times out

**Solution**:
1. Check file size (max 10MB per photo)
2. Verify UPLOAD_DIR exists and has write permissions
3. Check backend logs for errors
4. Ensure photo formats are supported (JPG, PNG, JPEG)

---

## 📈 Performance Optimization

### For Large Photo Collections (1000+ photos)

1. **Batch Processing**
   - Upload in smaller batches (100-200 at a time)
   - Run Auto Mode per batch

2. **Database Indexing**
   - Indexes automatically created on foreign keys
   - Add custom indexes for frequent queries if needed

3. **Caching**
   - CLIP embeddings cached in database
   - Thumbnail generation cached

4. **API Rate Limiting**
   - GPT-4 calls throttled to avoid rate limits
   - Batch requests when possible

---

## 📝 Development

### Project Structure
```
Siva/
├── backend/              # FastAPI backend
│   ├── app/             # Application code
│   ├── venv/            # Python virtual environment
│   └── main.py          # Entry point
├── frontend/            # React frontend
│   ├── src/             # Source code
│   └── package.json     # Dependencies
├── uploads/             # Uploaded photos (gitignored)
├── thumbnails/          # Generated thumbnails (gitignored)
├── FUTURE_IMPROVEMENTS.md  # Enhancement suggestions
└── README.md            # This file
```

### Adding New Features

1. **Backend Changes**
   - Add routes in `app/routers/`
   - Add business logic in `app/services/`
   - Update models in `app/models.py` if needed

2. **Frontend Changes**
   - Create components in `src/components/`
   - Update App.jsx for routing/state

3. **Database Changes**
   - Modify models in `app/models.py`
   - Alembic migrations (if needed)

### Code Style
- Backend: PEP 8 (Python)
- Frontend: ESLint + Prettier (JavaScript/React)
- Comments: Docstrings for functions, inline for complex logic

---

## 🎯 Quick Reference

### Start Everything
```bash
# Terminal 1 - Redis
redis-server

# Terminal 2 - Celery Worker (optional)
cd backend
venv\Scripts\activate
celery -A app.celery_app worker --loglevel=info --pool=solo

# Terminal 3 - Backend
cd backend
venv\Scripts\activate
python main.py

# Terminal 4 - Frontend
cd frontend
npm run dev
```

### Access Points
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Key Commands
```bash
# Restart backend (if stuck)
taskkill /F /IM python.exe
cd backend && python main.py

# Clear uploads (fresh start)
# Admin Panel → Delete All Photos

# Check backend logs
# Watch backend terminal for detailed progress
```
