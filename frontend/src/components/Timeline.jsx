import React, { useState, useEffect } from 'react'
import EmotionBadges from './EmotionBadges'
import StoryDetail from './StoryDetail'
import ImageDetailModal from './ImageDetailModal'
import './Timeline.css'

function Timeline({ userId = 1 }) {
  const [images, setImages] = useState([])
  const [stories, setStories] = useState([])
  const [lifeEvents, setLifeEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [viewMode, setViewMode] = useState('month') // 'year', 'month', 'day'
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [timelineData, setTimelineData] = useState({})
  const [imageEmotions, setImageEmotions] = useState({})
  const [selectedStory, setSelectedStory] = useState(null)
  const [selectedImage, setSelectedImage] = useState(null)
  const [selectedLifeEvent, setSelectedLifeEvent] = useState(null)
  const [expandedPeriods, setExpandedPeriods] = useState({})

  useEffect(() => {
    fetchData()
  }, [userId])

  useEffect(() => {
    if (images.length > 0 || lifeEvents.length > 0) {
      organizeTimeline()
      fetchEmotions()
    }
  }, [images, stories, lifeEvents, viewMode])

  const fetchData = async () => {
    setLoading(true)
    try {
      // Fetch images
      const imagesResponse = await fetch('/api/photos')
      const imagesData = await imagesResponse.json()
      const imagesList = imagesData.images || []

      // Fetch categories for images
      const imagesWithCategories = await Promise.all(
        imagesList.map(async (image) => {
          try {
            const catResponse = await fetch(`/api/classifications/images/${image.id}`)
            if (catResponse.ok) {
              const catData = await catResponse.json()
              return { ...image, image_categories: catData.categories || [] }
            }
          } catch (e) {
            console.error(`Error fetching categories for image ${image.id}:`, e)
          }
          return { ...image, image_categories: [] }
        })
      )

      setImages(imagesWithCategories)

      // Fetch stories
      const storiesResponse = await fetch(`/api/stories/?user_id=${userId}`)
      const storiesData = await storiesResponse.json()
      setStories(storiesData || [])

      // Fetch life events
      const eventsResponse = await fetch(`/api/life-events/?user_id=${userId}`)
      const eventsData = await eventsResponse.json()
      setLifeEvents(eventsData || [])

    } catch (error) {
      console.error('Error fetching timeline data:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchEmotions = async () => {
    const emotionsMap = {}
    for (const image of images) {
      try {
        const response = await fetch(`/api/emotions/image/${image.id}`)
        if (response.ok) {
          const data = await response.json()
          if (data.emotions && data.emotions.length > 0) {
            emotionsMap[image.id] = data.emotions
          }
        }
      } catch (error) {
        console.error(`Error fetching emotions for image ${image.id}:`, error)
      }
    }
    setImageEmotions(emotionsMap)
  }

  const organizeTimeline = () => {
    const organized = {}

    images.forEach(image => {
      // Prefer capture_date, fall back to upload_date
      const date = image.capture_date ? new Date(image.capture_date) : new Date(image.upload_date)

      let key
      if (viewMode === 'year') {
        key = date.getFullYear().toString()
      } else if (viewMode === 'month') {
        key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
      } else {
        key = date.toISOString().split('T')[0]
      }

      if (!organized[key]) {
        organized[key] = {
          images: [],
          stories: [],
          lifeEvents: [],
          date: date,
          hasCaptureDates: false // Track if any images have real capture dates
        }
      }

      // Track if this period has actual capture dates
      if (image.capture_date) {
        organized[key].hasCaptureDates = true
      }

      organized[key].images.push(image)
    })

    // Add stories to timeline
    stories.forEach(story => {
      const date = story.start_date ? new Date(story.start_date) : new Date(story.created_at)

      let key
      if (viewMode === 'year') {
        key = date.getFullYear().toString()
      } else if (viewMode === 'month') {
        key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
      } else {
        key = date.toISOString().split('T')[0]
      }

      if (organized[key]) {
        organized[key].stories.push(story)
      }
    })

    // Add life events to timeline
    lifeEvents.forEach(event => {
      if (!event.event_date) return // Skip events without dates

      const date = new Date(event.event_date)

      let key
      if (viewMode === 'year') {
        key = date.getFullYear().toString()
      } else if (viewMode === 'month') {
        key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
      } else {
        key = date.toISOString().split('T')[0]
      }

      if (!organized[key]) {
        organized[key] = {
          images: [],
          stories: [],
          lifeEvents: [],
          date: date,
          hasCaptureDates: false
        }
      }

      organized[key].lifeEvents.push(event)
    })

    setTimelineData(organized)
  }

  const formatPeriodLabel = (key, date) => {
    if (viewMode === 'year') {
      return key
    } else if (viewMode === 'month') {
      return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long' })
    } else {
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    }
  }

  const getEmotionSummary = (images) => {
    const emotionCounts = {}
    images.forEach(image => {
      const emotions = imageEmotions[image.id]
      if (emotions && emotions.length > 0) {
        const topEmotion = emotions[0]
        emotionCounts[topEmotion.emotion] = (emotionCounts[topEmotion.emotion] || 0) + 1
      }
    })

    return Object.entries(emotionCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([emotion, count]) => ({ emotion, count }))
  }

  const handleStoryClick = async (story) => {
    try {
      const response = await fetch(`/api/stories/${story.id}`)
      if (!response.ok) throw new Error('Failed to fetch story details')
      const detailedStory = await response.json()

      // Fetch emotions for this story
      try {
        const emotionsResponse = await fetch(`/api/emotions/story/${story.id}`)
        if (emotionsResponse.ok) {
          const emotionsData = await emotionsResponse.json()
          detailedStory.emotions = emotionsData.emotions
        }
      } catch (err) {
        console.warn('Could not fetch emotions for story:', err)
      }

      setSelectedStory(detailedStory)
    } catch (error) {
      console.error('Error fetching story details:', error)
    }
  }

  const handleImageClick = (image) => {
    setSelectedImage(image)
  }

  const togglePeriodExpansion = (key) => {
    setExpandedPeriods(prev => ({
      ...prev,
      [key]: !prev[key]
    }))
  }

  const handleUpdateStory = async (storyId, updates) => {
    try {
      const response = await fetch(`/api/stories/${storyId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })
      if (!response.ok) throw new Error('Failed to update story')

      // Refresh data
      await fetchData()
      return true
    } catch (error) {
      console.error('Error updating story:', error)
      return false
    }
  }

  const handleDeleteStory = async (storyId) => {
    if (!window.confirm('Are you sure you want to delete this story?')) {
      return false
    }
    try {
      const response = await fetch(`/api/stories/${storyId}`, {
        method: 'DELETE'
      })
      if (!response.ok) throw new Error('Failed to delete story')

      setSelectedStory(null)
      await fetchData()
      return true
    } catch (error) {
      console.error('Error deleting story:', error)
      return false
    }
  }

  const handleDeleteImage = async () => {
    await fetchData()
  }

  // Sort timeline keys in reverse chronological order
  const sortedKeys = Object.keys(timelineData).sort((a, b) => {
    return new Date(timelineData[b].date) - new Date(timelineData[a].date)
  })

  return (
    <div className="timeline-container">
      <div className="timeline-header">
        <div className="timeline-title">
          <h2>📅 Your Timeline</h2>
          <p>Journey through your memories</p>
        </div>

        <div className="timeline-controls">
          <div className="view-mode-selector">
            <button
              className={`view-mode-btn ${viewMode === 'year' ? 'active' : ''}`}
              onClick={() => setViewMode('year')}
            >
              Year
            </button>
            <button
              className={`view-mode-btn ${viewMode === 'month' ? 'active' : ''}`}
              onClick={() => setViewMode('month')}
            >
              Month
            </button>
            <button
              className={`view-mode-btn ${viewMode === 'day' ? 'active' : ''}`}
              onClick={() => setViewMode('day')}
            >
              Day
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="timeline-loading">Loading your timeline...</div>
      ) : sortedKeys.length === 0 ? (
        <div className="timeline-empty">
          <p>No photos yet. Upload some photos to see your timeline!</p>
        </div>
      ) : (
        <div className="timeline-content">
          {sortedKeys.map(key => {
            const period = timelineData[key]
            const emotionSummary = getEmotionSummary(period.images)

            return (
              <div key={key} className="timeline-period">
                <div className="timeline-period-header">
                  <div className="period-date">
                    <span className="period-label">
                      {formatPeriodLabel(key, period.date)}
                    </span>
                    <span className="period-count">
                      {period.images.length} photo{period.images.length !== 1 ? 's' : ''}
                      {period.stories.length > 0 && `, ${period.stories.length} stor${period.stories.length !== 1 ? 'ies' : 'y'}`}
                      {period.lifeEvents && period.lifeEvents.length > 0 && `, ${period.lifeEvents.length} event${period.lifeEvents.length !== 1 ? 's' : ''}`}
                    </span>
                  </div>

                  {emotionSummary.length > 0 && (
                    <div className="period-emotions">
                      {emotionSummary.map(({ emotion, count }) => (
                        <span key={emotion} className="emotion-tag" title={`${count} photos`}>
                          {emotion}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Life Events in this period */}
                {period.lifeEvents && period.lifeEvents.length > 0 && (
                  <div className="timeline-life-events">
                    {period.lifeEvents.map(event => (
                      <div
                        key={event.id}
                        className="timeline-event-card"
                        onClick={async () => {
                          try {
                            const response = await fetch(`/api/life-events/${event.id}`)
                            if (response.ok) {
                              const detailedEvent = await response.json()
                              setSelectedLifeEvent(detailedEvent)
                            }
                          } catch (error) {
                            console.error('Error fetching event details:', error)
                          }
                        }}
                        style={{ cursor: 'pointer' }}
                      >
                        <div className="event-icon">
                          {event.event_type === 'birthday' && '🎂'}
                          {event.event_type === 'wedding' && '💍'}
                          {event.event_type === 'graduation' && '🎓'}
                          {event.event_type === 'vacation' && '✈️'}
                          {event.event_type === 'anniversary' && '💐'}
                          {!['birthday', 'wedding', 'graduation', 'vacation', 'anniversary'].includes(event.event_type) && '📅'}
                        </div>
                        <div className="event-info">
                          <h4>{event.event_name}</h4>
                          <p className="event-type-label">{event.event_type}</p>
                          {event.event_location && <p className="event-location">📍 {event.event_location}</p>}
                          {event.image_count > 0 && <p className="event-photo-count">🖼️ {event.image_count} photo{event.image_count !== 1 ? 's' : ''}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Stories in this period */}
                {period.stories.length > 0 && (
                  <div className="timeline-stories">
                    {period.stories.map(story => (
                      <div
                        key={story.id}
                        className="timeline-story-card"
                        onClick={() => handleStoryClick(story)}
                        style={{ cursor: 'pointer' }}
                      >
                        <div className="story-icon">📖</div>
                        <div className="story-info">
                          <h4>{story.title}</h4>
                          <p>{story.description?.substring(0, 100)}...</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Images in this period */}
                <div className="timeline-images-grid">
                  {(expandedPeriods[key] ? period.images : period.images.slice(0, 12)).map(image => {
                    const filename = image.file_path.split(/[/\\]/).pop()
                    const imageUrl = `http://localhost:8000/uploads/${filename}`
                    const emotions = imageEmotions[image.id]

                    return (
                      <div
                        key={image.id}
                        className="timeline-image-card"
                        onClick={() => handleImageClick(image)}
                        style={{ cursor: 'pointer' }}
                      >
                        <div className="timeline-image-container">
                          <img src={imageUrl} alt={image.filename} loading="lazy" />
                        </div>
                        {emotions && emotions.length > 0 && (
                          <div className="timeline-image-emotion">
                            {emotions[0].emotion}
                          </div>
                        )}
                      </div>
                    )
                  })}
                  {period.images.length > 12 && !expandedPeriods[key] && (
                    <div
                      className="timeline-image-more"
                      onClick={() => togglePeriodExpansion(key)}
                    >
                      +{period.images.length - 12} more
                    </div>
                  )}
                </div>
                {expandedPeriods[key] && period.images.length > 12 && (
                  <button
                    className="show-less-btn"
                    onClick={() => togglePeriodExpansion(key)}
                  >
                    Show Less
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Modals */}
      {selectedStory && (
        <StoryDetail
          story={selectedStory}
          onClose={() => setSelectedStory(null)}
          onUpdate={handleUpdateStory}
          onDelete={handleDeleteStory}
        />
      )}

      {selectedImage && (
        <ImageDetailModal
          image={selectedImage}
          onClose={() => setSelectedImage(null)}
          onDelete={handleDeleteImage}
        />
      )}

      {selectedLifeEvent && (
        <div className="event-detail-modal" onClick={() => setSelectedLifeEvent(null)}>
          <div className="modal-content-event" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelectedLifeEvent(null)}>×</button>

            <div className="modal-header-event">
              <span className="event-icon-large">
                {selectedLifeEvent.event_type === 'birthday' && '🎂'}
                {selectedLifeEvent.event_type === 'wedding' && '💍'}
                {selectedLifeEvent.event_type === 'graduation' && '🎓'}
                {selectedLifeEvent.event_type === 'vacation' && '✈️'}
                {selectedLifeEvent.event_type === 'anniversary' && '💐'}
                {!['birthday', 'wedding', 'graduation', 'vacation', 'anniversary'].includes(selectedLifeEvent.event_type) && '📅'}
              </span>
              <div>
                <h2>{selectedLifeEvent.event_name}</h2>
                <span className="event-type-badge">{selectedLifeEvent.event_type}</span>
              </div>
            </div>

            <div className="modal-body-event">
              <div className="event-info-detail">
                <div className="info-item">
                  <strong>Date:</strong> {new Date(selectedLifeEvent.event_date).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  })}
                </div>
                {selectedLifeEvent.event_location && (
                  <div className="info-item">
                    <strong>Location:</strong> {selectedLifeEvent.event_location}
                  </div>
                )}
                {selectedLifeEvent.description && (
                  <div className="info-item">
                    <strong>Description:</strong>
                    <p>{selectedLifeEvent.description}</p>
                  </div>
                )}
              </div>

              {selectedLifeEvent.images && selectedLifeEvent.images.length > 0 && (
                <div className="event-images-section">
                  <h3>Event Photos ({selectedLifeEvent.images.length})</h3>
                  <div className="event-images-grid">
                    {selectedLifeEvent.images.map(image => (
                      <div key={image.id} className="event-image" onClick={() => handleImageClick(image)}>
                        <img
                          src={`http://localhost:8000${image.file_path?.replace('./', '/')}`}
                          alt={image.filename}
                        />
                        {image.is_cover_image && (
                          <span className="cover-badge">Cover</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Timeline
