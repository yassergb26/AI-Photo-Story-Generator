import React, { useState, useEffect } from 'react'
import './LifeEventsManager.css'

function LifeEventsManager({ onRefresh }) {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [eventTypes, setEventTypes] = useState([])
  const [images, setImages] = useState([])
  const [formData, setFormData] = useState({
    event_type: 'birthday',
    event_name: '',
    event_date: '',
    event_location: '',
    description: '',
    image_ids: []
  })

  useEffect(() => {
    fetchEvents()
    fetchEventTypes()
    fetchImages()
  }, [])

  const fetchEvents = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/life-events/?user_id=1')
      if (response.ok) {
        const data = await response.json()
        setEvents(data)
      }
    } catch (error) {
      console.error('Error fetching life events:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchEventTypes = async () => {
    try {
      const response = await fetch('/api/life-events/types/list')
      if (response.ok) {
        const data = await response.json()
        setEventTypes(data.event_types)
      }
    } catch (error) {
      console.error('Error fetching event types:', error)
    }
  }

  const fetchImages = async () => {
    try {
      const response = await fetch('/api/photos?limit=100')
      if (response.ok) {
        const data = await response.json()
        setImages(data.images || [])
      }
    } catch (error) {
      console.error('Error fetching images:', error)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleImageSelection = (imageId) => {
    setFormData(prev => {
      const currentImages = prev.image_ids || []
      if (currentImages.includes(imageId)) {
        return { ...prev, image_ids: currentImages.filter(id => id !== imageId) }
      } else {
        return { ...prev, image_ids: [...currentImages, imageId] }
      }
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!formData.event_name.trim()) {
      alert('Please enter an event name')
      return
    }

    try {
      const response = await fetch('/api/life-events/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...formData,
          user_id: 1
        })
      })

      if (response.ok) {
        setShowCreateForm(false)
        setFormData({
          event_type: 'birthday',
          event_name: '',
          event_date: '',
          event_location: '',
          description: '',
          image_ids: []
        })
        fetchEvents()
        if (onRefresh) onRefresh()
      } else {
        const error = await response.json()
        alert(`Error creating event: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Error creating life event:', error)
      alert('Failed to create life event')
    }
  }

  const handleDelete = async (eventId) => {
    if (!window.confirm('Are you sure you want to delete this life event?')) {
      return
    }

    try {
      const response = await fetch(`/api/life-events/${eventId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        fetchEvents()
        if (onRefresh) onRefresh()
      } else {
        alert('Failed to delete event')
      }
    } catch (error) {
      console.error('Error deleting life event:', error)
      alert('Failed to delete event')
    }
  }

  const viewEventDetails = async (eventId) => {
    try {
      const response = await fetch(`/api/life-events/${eventId}`)
      if (response.ok) {
        const data = await response.json()
        setSelectedEvent(data)
      }
    } catch (error) {
      console.error('Error fetching event details:', error)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Date not set'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const getEventTypeInfo = (eventType) => {
    const type = eventTypes.find(t => t.value === eventType)
    return type || { label: eventType, icon: '📅' }
  }

  if (loading) {
    return <div className="life-events-loading">Loading life events...</div>
  }

  return (
    <div className="life-events-manager">
      <div className="life-events-header">
        <div>
          <h2>Life Events</h2>
          <p className="subtitle">Track and organize your major life milestones</p>
        </div>
        <button
          className="create-event-btn"
          onClick={() => setShowCreateForm(!showCreateForm)}
        >
          {showCreateForm ? '✕ Cancel' : '➕ Create New Event'}
        </button>
      </div>

      {showCreateForm && (
        <div className="create-event-form-container">
          <h3>Create New Life Event</h3>
          <form onSubmit={handleSubmit} className="create-event-form">
            <div className="form-group">
              <label>Event Type</label>
              <select
                name="event_type"
                value={formData.event_type}
                onChange={handleInputChange}
                className="form-select"
              >
                {eventTypes.map(type => (
                  <option key={type.value} value={type.value}>
                    {type.icon} {type.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Event Name *</label>
              <input
                type="text"
                name="event_name"
                value={formData.event_name}
                onChange={handleInputChange}
                placeholder="e.g., 30th Birthday Celebration"
                className="form-input"
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Event Date</label>
                <input
                  type="date"
                  name="event_date"
                  value={formData.event_date}
                  onChange={handleInputChange}
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label>Location</label>
                <input
                  type="text"
                  name="event_location"
                  value={formData.event_location}
                  onChange={handleInputChange}
                  placeholder="e.g., New York, NY"
                  className="form-input"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Description</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                placeholder="Add details about this event..."
                className="form-textarea"
                rows="3"
              />
            </div>

            <div className="form-group">
              <label>Select Images ({formData.image_ids.length} selected)</label>
              <div className="image-selection-grid">
                {images.slice(0, 20).map(image => (
                  <div
                    key={image.id}
                    className={`selectable-image ${formData.image_ids.includes(image.id) ? 'selected' : ''}`}
                    onClick={() => handleImageSelection(image.id)}
                  >
                    <img
                      src={`http://localhost:8000${image.file_path?.replace('./', '/')}`}
                      alt={image.filename}
                    />
                    {formData.image_ids.includes(image.id) && (
                      <div className="selection-check">✓</div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="form-actions">
              <button type="button" onClick={() => setShowCreateForm(false)} className="cancel-btn">
                Cancel
              </button>
              <button type="submit" className="submit-btn">
                Create Event
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="events-grid">
        {events.length === 0 ? (
          <div className="no-events">
            <p>No life events yet. Create your first event to get started!</p>
          </div>
        ) : (
          events.map(event => (
            <div key={event.id} className="event-card">
              <div className="event-card-header">
                <span className="event-icon">
                  {getEventTypeInfo(event.event_type).icon}
                </span>
                <div className="event-card-title">
                  <h3>{event.event_name}</h3>
                  <span className="event-type-badge">
                    {getEventTypeInfo(event.event_type).label}
                  </span>
                </div>
              </div>

              <div className="event-card-body">
                <div className="event-detail">
                  <span className="detail-icon">📅</span>
                  <span>{formatDate(event.event_date)}</span>
                </div>

                {event.event_location && (
                  <div className="event-detail">
                    <span className="detail-icon">📍</span>
                    <span>{event.event_location}</span>
                  </div>
                )}

                {event.description && (
                  <p className="event-description">{event.description}</p>
                )}

                <div className="event-meta">
                  <span className="image-count">
                    🖼️ {event.image_count} {event.image_count === 1 ? 'image' : 'images'}
                  </span>
                </div>
              </div>

              <div className="event-card-actions">
                <button
                  className="view-btn"
                  onClick={() => viewEventDetails(event.id)}
                >
                  View Details
                </button>
                <button
                  className="delete-btn"
                  onClick={() => handleDelete(event.id)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {selectedEvent && (
        <div className="event-detail-modal" onClick={() => setSelectedEvent(null)}>
          <div className="modal-content-event" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelectedEvent(null)}>×</button>

            <div className="modal-header">
              <span className="event-icon-large">
                {getEventTypeInfo(selectedEvent.event_type).icon}
              </span>
              <div>
                <h2>{selectedEvent.event_name}</h2>
                <span className="event-type-badge">
                  {getEventTypeInfo(selectedEvent.event_type).label}
                </span>
              </div>
            </div>

            <div className="modal-body">
              <div className="event-info">
                <div className="info-item">
                  <strong>Date:</strong> {formatDate(selectedEvent.event_date)}
                </div>
                {selectedEvent.event_location && (
                  <div className="info-item">
                    <strong>Location:</strong> {selectedEvent.event_location}
                  </div>
                )}
                {selectedEvent.description && (
                  <div className="info-item">
                    <strong>Description:</strong>
                    <p>{selectedEvent.description}</p>
                  </div>
                )}
              </div>

              {selectedEvent.images && selectedEvent.images.length > 0 && (
                <div className="event-images-section">
                  <h3>Event Photos ({selectedEvent.images.length})</h3>
                  <div className="event-images-grid">
                    {selectedEvent.images.map(image => (
                      <div key={image.id} className="event-image">
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

export default LifeEventsManager
