import React, { useState, useEffect } from 'react'
import EmotionBadges from './EmotionBadges'
import './PatternsDashboard.css'

function PatternsDashboard({ userId = 1, refreshTrigger }) {
  const [patterns, setPatterns] = useState([])
  const [loading, setLoading] = useState(false)
  const [detecting, setDetecting] = useState(false)
  const [selectedPattern, setSelectedPattern] = useState(null)
  const [message, setMessage] = useState(null)

  useEffect(() => {
    fetchPatterns()
  }, [refreshTrigger])

  const fetchPatterns = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/patterns/?user_id=${userId}`)
      if (response.ok) {
        const data = await response.json()
        setPatterns(data)
      }
    } catch (error) {
      console.error('Error fetching patterns:', error)
      setMessage({ type: 'error', text: 'Failed to fetch patterns' })
    } finally {
      setLoading(false)
    }
  }

  const detectPatterns = async () => {
    setDetecting(true)
    setMessage(null)
    try {
      const response = await fetch('/api/patterns/detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          pattern_types: ['temporal', 'spatial', 'visual']
        })
      })

      if (response.ok) {
        const data = await response.json()
        setMessage({
          type: 'success',
          text: `${data.message} - Found ${data.patterns_detected} pattern(s)!`
        })
        fetchPatterns()
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to detect patterns' })
      }
    } catch (error) {
      console.error('Error detecting patterns:', error)
      setMessage({ type: 'error', text: 'Failed to detect patterns' })
    } finally {
      setDetecting(false)
    }
  }

  const viewPatternDetails = async (patternId) => {
    try {
      const response = await fetch(`/api/patterns/${patternId}`)
      if (response.ok) {
        const data = await response.json()
        setSelectedPattern(data)
      }
    } catch (error) {
      console.error('Error fetching pattern details:', error)
    }
  }

  const deletePattern = async (patternId) => {
    if (!confirm('Are you sure you want to delete this pattern?')) return

    try {
      const response = await fetch(`/api/patterns/${patternId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'Pattern deleted successfully' })
        setSelectedPattern(null)
        fetchPatterns()
      }
    } catch (error) {
      console.error('Error deleting pattern:', error)
      setMessage({ type: 'error', text: 'Failed to delete pattern' })
    }
  }

  const getPatternTypeIcon = (type) => {
    switch (type) {
      case 'temporal': return '📅'
      case 'spatial': return '📍'
      case 'visual': return '🎨'
      default: return '🔍'
    }
  }

  const getPatternTypeName = (type) => {
    switch (type) {
      case 'temporal': return 'Temporal Pattern'
      case 'spatial': return 'Location Pattern'
      case 'visual': return 'Visual Pattern'
      default: return 'Pattern'
    }
  }

  return (
    <div className="patterns-dashboard">
      <div className="patterns-header">
        <div>
          <h2>🔍 Discovered Patterns</h2>
          <p>Find recurring events, locations, and visual themes in your photos</p>
        </div>
        <button
          className="detect-button"
          onClick={detectPatterns}
          disabled={detecting}
        >
          {detecting ? 'Detecting...' : '🔍 Detect Patterns'}
        </button>
      </div>

      {message && (
        <div className={`message message-${message.type}`}>
          {message.text}
        </div>
      )}

      {loading ? (
        <div className="loading">Loading patterns...</div>
      ) : patterns.length === 0 ? (
        <div className="empty-state">
          <p>No patterns found yet.</p>
          <p>Click "Detect Patterns" to analyze your photos!</p>
        </div>
      ) : (
        <div className="patterns-grid">
          {patterns.map((pattern) => (
            <div
              key={pattern.id}
              className="pattern-card"
              onClick={() => viewPatternDetails(pattern.id)}
            >
              <div className="pattern-header">
                <div className="pattern-type-icon">
                  {getPatternTypeIcon(pattern.pattern_type)}
                </div>
                <div className="pattern-info">
                  <h3>{getPatternTypeName(pattern.pattern_type)}</h3>
                  <p className="pattern-description">{pattern.description}</p>
                </div>
              </div>

              <div className="pattern-stats">
                <div className="stat">
                  <span className="stat-label">Images</span>
                  <span className="stat-value">{pattern.image_count}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Confidence</span>
                  <span className="stat-value">
                    {(pattern.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>
                {pattern.frequency && (
                  <div className="stat">
                    <span className="stat-label">Frequency</span>
                    <span className="stat-value">{pattern.frequency}</span>
                  </div>
                )}
              </div>

              {/* Show dominant emotions if available */}
              {pattern.pattern_metadata?.emotions && pattern.pattern_metadata.emotions.length > 0 && (
                <div className="pattern-emotions">
                  <EmotionBadges
                    emotions={pattern.pattern_metadata.emotions.slice(0, 2).map(e => ({
                      emotion: e.emotion,
                      confidence: e.percentage / 100
                    }))}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {selectedPattern && (
        <div className="modal" onClick={() => setSelectedPattern(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>
                {getPatternTypeIcon(selectedPattern.pattern_type)}{' '}
                {selectedPattern.description}
              </h2>
              <button
                className="close-button"
                onClick={() => setSelectedPattern(null)}
              >
                ×
              </button>
            </div>

            <div className="modal-body">
              <div className="pattern-details">
                <p><strong>Type:</strong> {getPatternTypeName(selectedPattern.pattern_type)}</p>
                <p><strong>Images:</strong> {selectedPattern.image_count}</p>
                <p><strong>Confidence:</strong> {(selectedPattern.confidence_score * 100).toFixed(0)}%</p>
                {selectedPattern.frequency && (
                  <p><strong>Frequency:</strong> {selectedPattern.frequency}</p>
                )}
                {selectedPattern.pattern_metadata && (
                  <div className="metadata">
                    <p><strong>Details:</strong></p>
                    <pre>{JSON.stringify(selectedPattern.pattern_metadata, null, 2)}</pre>
                  </div>
                )}
              </div>

              {selectedPattern.images && selectedPattern.images.length > 0 && (
                <div className="pattern-images">
                  <h3>Images in this pattern ({selectedPattern.images.length})</h3>
                  <div className="images-grid">
                    {selectedPattern.images.map((image) => (
                      <div key={image.id} className="pattern-image">
                        <img
                          src={`/${image.file_path}`}
                          alt={image.filename}
                          loading="lazy"
                        />
                        <div className="image-filename">{image.filename}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="modal-actions">
                <button
                  className="delete-button"
                  onClick={() => deletePattern(selectedPattern.id)}
                >
                  Delete Pattern
                </button>
                <button
                  className="close-button-secondary"
                  onClick={() => setSelectedPattern(null)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PatternsDashboard
