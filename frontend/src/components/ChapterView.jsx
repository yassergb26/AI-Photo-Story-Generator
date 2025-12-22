import React, { useState, useEffect } from 'react'
import './ChapterView.css'

function ChapterView({ userId = 1, refreshTrigger = 0 }) {
  const [chapters, setChapters] = useState([])
  const [loading, setLoading] = useState(false)
  const [hasBirthDate, setHasBirthDate] = useState(false)
  const [showBirthDateModal, setShowBirthDateModal] = useState(false)
  const [birthDate, setBirthDate] = useState('')
  const [expandedChapters, setExpandedChapters] = useState(new Set())
  const [chapterPhotos, setChapterPhotos] = useState({})
  const [loadingPhotos, setLoadingPhotos] = useState({})
  const [expandedArcs, setExpandedArcs] = useState(new Set())
  const [arcPhotos, setArcPhotos] = useState({})

  useEffect(() => {
    checkBirthDate()
    loadChapters()
  }, [userId, refreshTrigger])

  const checkBirthDate = async () => {
    try {
      const response = await fetch(`/api/chapters/users/${userId}/birth-date`)
      const data = await response.json()
      setHasBirthDate(data.has_birth_date)

      if (data.birth_date) {
        const date = new Date(data.birth_date)
        setBirthDate(date.toISOString().split('T')[0])
      }
    } catch (error) {
      console.error('Error checking birth date:', error)
    }
  }

  const loadChapters = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/chapters?user_id=${userId}`)
      const data = await response.json()
      setChapters(data)
    } catch (error) {
      console.error('Error loading chapters:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveBirthDate = async () => {
    if (!birthDate) {
      alert('Please enter a valid birth date')
      return
    }

    try {
      const response = await fetch(`/api/chapters/users/${userId}/birth-date`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ birth_date: birthDate })
      })

      const data = await response.json()

      if (data.success) {
        setHasBirthDate(true)
        setShowBirthDateModal(false)
        alert('Birth date saved! Regenerating chapters with age-based grouping...')
        await handleGenerateChapters(true)
      }
    } catch (error) {
      console.error('Error saving birth date:', error)
      alert('Failed to save birth date')
    }
  }

  const loadChapterPhotos = async (chapter) => {
    if (chapterPhotos[chapter.id]) return // Already loaded

    setLoadingPhotos(prev => ({ ...prev, [chapter.id]: true }))

    try {
      // Fetch photos from this chapter's year range
      const response = await fetch(
        `/api/photos?user_id=${userId}&limit=10000`
      )
      const data = await response.json()
      const allPhotos = data.images || data // Handle both array and object response

      // Filter photos by chapter year range
      const filtered = allPhotos.filter(photo => {
        if (!photo.capture_date) return false
        const year = new Date(photo.capture_date).getFullYear()
        return year >= chapter.year_start && year <= chapter.year_end
      })

      // Debug logging
      if (filtered.length > 0) {
        console.log('ChapterView - Loaded photos for chapter:', chapter.title)
        console.log('Sample photo:', {
          id: filtered[0].id,
          filename: filtered[0].filename,
          file_path: filtered[0].file_path,
          thumbnail_path: filtered[0].thumbnail_path
        })
      }

      setChapterPhotos(prev => ({ ...prev, [chapter.id]: filtered.slice(0, 12) }))
    } catch (error) {
      console.error('Error loading chapter photos:', error)
      setChapterPhotos(prev => ({ ...prev, [chapter.id]: [] }))
    } finally {
      setLoadingPhotos(prev => ({ ...prev, [chapter.id]: false }))
    }
  }

  const toggleChapter = (chapterId) => {
    const newExpanded = new Set(expandedChapters)
    if (newExpanded.has(chapterId)) {
      newExpanded.delete(chapterId)
    } else {
      newExpanded.add(chapterId)
      // Load photos when expanding
      const chapter = chapters.find(c => c.id === chapterId)
      if (chapter) loadChapterPhotos(chapter)
    }
    setExpandedChapters(newExpanded)
  }

  const toggleArc = async (arcId, chapter) => {
    const newExpanded = new Set(expandedArcs)
    if (newExpanded.has(arcId)) {
      newExpanded.delete(arcId)
    } else {
      newExpanded.add(arcId)
      // Load arc photos when expanding
      if (!arcPhotos[arcId]) {
        try {
          // Fetch the ACTUAL photos for this specific story arc from the backend
          const response = await fetch(`/api/stories/${arcId}`)
          const data = await response.json()

          // The backend returns the story with its images
          const arcImages = data.images || []

          console.log(`Arc ${arcId} photos loaded:`, arcImages.length, 'photos')
          setArcPhotos(prev => ({ ...prev, [arcId]: arcImages }))
        } catch (error) {
          console.error('Error loading arc photos:', error)
          setArcPhotos(prev => ({ ...prev, [arcId]: [] }))
        }
      }
    }
    setExpandedArcs(newExpanded)
  }

  const getEmotionEmoji = (emotion) => {
    const emojiMap = {
      'Joy': '😊',
      'Happy': '😄',
      'Love': '❤️',
      'Excitement': '🎉',
      'Surprise': '😮',
      'Neutral': '😐',
      'Sad': '😢',
      'Angry': '😠'
    }
    return emojiMap[emotion] || '💖'
  }

  const getArcEmoji = (arcType) => {
    const emojiMap = {
      'event': '🎉',
      'trip': '🏖️',
      'milestone': '🏠',
      'tradition': '🎂'
    }
    return emojiMap[arcType] || '📸'
  }

  if (loading) {
    return (
      <div className="chapter-view">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading your life story...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="chapter-view">
      <div className="chapter-header">
        <h1>📖 Your Life Story</h1>
        <p className="chapter-subtitle">Chapters of memories, moments, and milestones</p>
      </div>

      {!hasBirthDate && chapters.length > 0 && (
        <div className="birth-date-banner">
          <div className="banner-content">
            <span className="banner-icon">🎂</span>
            <div className="banner-text">
              <strong>Set your birth date</strong> for age-based chapters like "Building a Family (Ages 28-30)"
            </div>
            <button
              className="btn-set-birth-date"
              onClick={() => setShowBirthDateModal(true)}
            >
              Set Birth Date
            </button>
          </div>
        </div>
      )}

      {chapters.length === 0 ? (
        <div className="empty-chapters">
          <div className="empty-icon">📚</div>
          <h2>No Chapters Yet</h2>
          <p>Upload photos to automatically generate your life story with chapters and story arcs</p>

          {!hasBirthDate && (
            <div className="birth-date-reminder">
              <p>💡 <strong>Tip:</strong> Set your birth date for age-based chapters</p>
              <button
                className="btn-set-birth-date"
                onClick={() => setShowBirthDateModal(true)}
              >
                🎂 Set Birth Date
              </button>
            </div>
          )}
        </div>
      ) : (
        <>

          <div className="chapters-list">
            {chapters.map((chapter) => (
              <div key={chapter.id} className="chapter-card">
                <div className="chapter-card-header">
                  <div className="chapter-title-section">
                    <h2 className="chapter-title">
                      📖 CHAPTER {chapter.sequence_order + 1}: "{chapter.title}"
                    </h2>
                    <div className="chapter-separator"></div>
                  </div>

                  <div className="chapter-meta">
                    <span className="meta-item">
                      📅 {chapter.subtitle ||
                        `${chapter.year_start}${chapter.year_end !== chapter.year_start ? `-${chapter.year_end}` : ''}`}
                    </span>
                    <span className="meta-item">
                      📷 {chapter.photo_count} photos
                    </span>
                    {chapter.dominant_emotion && (
                      <span className="meta-item">
                        {getEmotionEmoji(chapter.dominant_emotion)} Dominant: {chapter.dominant_emotion}
                      </span>
                    )}
                  </div>
                </div>

                {chapter.description && (
                  <p className="chapter-description">"{chapter.description}"</p>
                )}

                {chapter.story_arcs && chapter.story_arcs.length > 0 && (
                  <div className="story-arcs-section">
                    <h3 className="story-arcs-title">Story Arcs:</h3>
                    <div className="story-arcs-list">
                      {chapter.story_arcs.map((arc) => (
                        <div key={arc.id} className="story-arc-item-wrapper">
                          <div className="story-arc-item">
                            <div className="arc-content">
                              <span className="arc-icon">{getArcEmoji(arc.arc_type)}</span>
                              <span className="arc-title">"{arc.title}"</span>
                              <span className="arc-photos">({arc.photo_count} photos)</span>
                              {arc.is_ai_detected && (
                                <span className="arc-badge">← AI detected!</span>
                              )}
                            </div>
                            <button
                              className="btn-view-arc"
                              onClick={() => toggleArc(arc.id, chapter)}
                            >
                              {expandedArcs.has(arc.id) ? '▲ Hide Photos' : '▼ View Details'}
                            </button>
                          </div>

                          {expandedArcs.has(arc.id) && (
                            <div className="arc-photos-section">
                              {arc.description ? (
                                <p className="arc-description">"{arc.description}"</p>
                              ) : (
                                <p className="arc-description">{arc.title} - {arc.photo_count} photos captured</p>
                              )}
                              {arc.dominant_emotion && (
                                <div className="arc-emotion-info">
                                  <strong>Dominant Emotion:</strong> {arc.dominant_emotion}
                                  {arc.emotion_percentage && (
                                    <span className="emotion-percentage"> ({arc.emotion_percentage.toFixed(1)}%)</span>
                                  )}
                                </div>
                              )}
                              {arcPhotos[arc.id] && arcPhotos[arc.id].length > 0 ? (
                                <div className="arc-photos-grid">
                                  {arcPhotos[arc.id].map((photo) => (
                                    <div key={photo.id} className="arc-photo-item">
                                      <img
                                        src={photo.thumbnail_path || photo.file_path}
                                        alt={photo.filename}
                                        className="arc-thumbnail"
                                      />
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <p className="no-photos">Loading photos...</p>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {expandedChapters.has(chapter.id) && (
                  <div className="chapter-expanded-content">
                    <div className="expanded-section">
                      <h3>📸 Chapter Photos ({chapter.photo_count} total)</h3>

                      {chapter.description && (
                        <div className="chapter-narrative">
                          <h4>📖 Chapter Story</h4>
                          <p>{chapter.description}</p>
                        </div>
                      )}

                      {loadingPhotos[chapter.id] ? (
                        <div className="photos-loading">
                          <div className="spinner-small"></div>
                          <p>Loading photos...</p>
                        </div>
                      ) : chapterPhotos[chapter.id] && chapterPhotos[chapter.id].length > 0 ? (
                        <div className="chapter-photos-grid">
                          {chapterPhotos[chapter.id].map((photo) => (
                            <div key={photo.id} className="chapter-photo-item">
                              <img
                                src={photo.thumbnail_path || photo.file_path}
                                alt={photo.filename}
                                className="chapter-thumbnail"
                              />
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="no-photos">No photos available for preview</p>
                      )}

                      <div className="chapter-stats">
                        <div className="stat-item">
                          <strong>Time Span:</strong> {chapter.year_end - chapter.year_start + 1} years
                        </div>
                        <div className="stat-item">
                          <strong>Age Range:</strong> {chapter.age_start} - {chapter.age_end} years old
                        </div>
                        {chapter.dominant_emotion && (
                          <div className="stat-item">
                            <strong>Emotional Tone:</strong> {getEmotionEmoji(chapter.dominant_emotion)} {chapter.dominant_emotion}
                          </div>
                        )}
                      </div>

                      <div className="chapter-actions-buttons">
                        <button
                          className="btn-view-all-photos"
                          onClick={() => window.location.href = `/?year_start=${chapter.year_start}&year_end=${chapter.year_end}`}
                        >
                          📷 View All {chapter.photo_count} Photos
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                <div className="chapter-actions-bottom">
                  <button
                    className="btn-expand"
                    onClick={() => toggleChapter(chapter.id)}
                  >
                    {expandedChapters.has(chapter.id) ? '▲ Collapse' : '▼ Expand Chapter'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {showBirthDateModal && (
        <div className="modal-overlay" onClick={() => setShowBirthDateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>🎂 Set Your Birth Date</h2>
            <p className="modal-description">
              Get personalized chapters based on your age and life phases!
            </p>

            <div className="form-group">
              <label htmlFor="birthDate">Birth Date:</label>
              <input
                type="date"
                id="birthDate"
                value={birthDate}
                onChange={(e) => setBirthDate(e.target.value)}
                max={new Date().toISOString().split('T')[0]}
              />
            </div>

            <div className="modal-note">
              <strong>Note:</strong> Without a birth date, chapters will be organized by year instead of life phases.
            </div>

            <div className="modal-actions">
              <button
                className="btn-cancel"
                onClick={() => setShowBirthDateModal(false)}
              >
                Skip for Now
              </button>
              <button
                className="btn-save"
                onClick={handleSaveBirthDate}
              >
                Save Birth Date
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ChapterView
