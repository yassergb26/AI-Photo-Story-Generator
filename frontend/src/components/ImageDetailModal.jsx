import React, { useState, useEffect } from 'react'
import EmotionBadges from './EmotionBadges'
import './ImageDetailModal.css'

function ImageDetailModal({ image, onClose, onDelete }) {
  const [emotions, setEmotions] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (image) {
      fetchImageDetails()
    }
  }, [image])

  const fetchImageDetails = async () => {
    setLoading(true)
    try {
      // Fetch emotions
      const emotionsResponse = await fetch(`/api/emotions/image/${image.id}`)
      if (emotionsResponse.ok) {
        const emotionsData = await emotionsResponse.json()
        setEmotions(emotionsData.emotions || [])
      }

      // Fetch categories
      const categoriesResponse = await fetch(`/api/classifications/images/${image.id}`)
      if (categoriesResponse.ok) {
        const categoriesData = await categoriesResponse.json()
        setCategories(categoriesData.categories || [])
      }
    } catch (error) {
      console.error('Error fetching image details:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this image?')) {
      try {
        const response = await fetch(`/api/photos/${image.id}`, {
          method: 'DELETE'
        })
        if (response.ok) {
          onDelete()
          onClose()
        }
      } catch (error) {
        console.error('Error deleting image:', error)
      }
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown'
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
  }

  if (!image) return null

  return (
    <div className="image-detail-modal" onClick={onClose}>
      <div className="modal-content-detail" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>×</button>

        <div className="modal-body-detail">
          {/* Image Section */}
          <div className="modal-image-section">
            <img
              src={`http://localhost:8000${image.file_path?.replace('./', '/')}`}
              alt={image.filename}
              className="modal-image-full"
            />
          </div>

          {/* Details Section */}
          <div className="modal-details-section">
            <h2 className="image-title">{image.filename}</h2>

            {loading ? (
              <div className="loading-details">Loading details...</div>
            ) : (
              <>
                {/* Emotions */}
                {emotions.length > 0 && (
                  <div className="detail-group">
                    <h3 className="detail-heading">Detected Emotions</h3>
                    <EmotionBadges emotions={emotions.map(e => ({
                      emotion: e.emotion,
                      confidence: e.confidence_score || e.confidence || 0
                    }))} />
                  </div>
                )}

                {/* Categories */}
                {categories.length > 0 && (
                  <div className="detail-group">
                    <h3 className="detail-heading">Categories</h3>
                    <div className="categories-list">
                      {categories.map((category, index) => (
                        <span key={index} className="category-badge">
                          {category.name || category.category_name}
                          <span className="category-confidence">
                            {((category.confidence || 0) * 100).toFixed(0)}%
                          </span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Metadata */}
                <div className="detail-group">
                  <h3 className="detail-heading">Image Information</h3>
                  <div className="metadata-grid">
                    <div className="metadata-item">
                      <span className="metadata-label">File Size:</span>
                      <span className="metadata-value">{formatFileSize(image.file_size)}</span>
                    </div>
                    <div className="metadata-item">
                      <span className="metadata-label">Upload Date:</span>
                      <span className="metadata-value">{formatDate(image.upload_date)}</span>
                    </div>
                    {image.capture_date && (
                      <div className="metadata-item">
                        <span className="metadata-label">Capture Date:</span>
                        <span className="metadata-value">{formatDate(image.capture_date)}</span>
                      </div>
                    )}
                    <div className="metadata-item">
                      <span className="metadata-label">Processed:</span>
                      <span className="metadata-value">
                        {image.processed ? '✅ Yes' : '❌ No'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="detail-actions-container">
                  <a
                    href={`http://localhost:8000${image.file_path?.replace('./', '/')}`}
                    download={image.filename}
                    className="action-btn download-btn"
                  >
                    ⬇️ Download
                  </a>
                  <button
                    className="action-btn delete-btn"
                    onClick={handleDelete}
                  >
                    🗑️ Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ImageDetailModal
