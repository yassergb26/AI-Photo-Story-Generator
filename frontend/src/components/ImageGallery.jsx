import React, { useState, useEffect } from 'react'
import CategoryBadges from './CategoryBadges'
import EmotionBadges from './EmotionBadges'
import './ImageGallery.css'

function ImageGallery({ images, onDeleteSuccess, onImageClick }) {
  console.log('🔥 ImageGallery component loaded - NEW CODE v2')
  console.log('Total images received:', images.length)
  if (images.length > 0) {
    console.log('First image:', images[0])
  }

  const [deleting, setDeleting] = useState(null)
  const [imageEmotions, setImageEmotions] = useState({})

  // Fetch emotions for all images when images change
  useEffect(() => {
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

    if (images.length > 0) {
      fetchEmotions()
    }
  }, [images])

  if (images.length === 0) {
    return (
      <div className="gallery-empty">
        <p>No images uploaded yet. Upload some images to get started!</p>
      </div>
    )
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'No date'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const handleDelete = async (imageId) => {
    if (!confirm('Are you sure you want to delete this image?')) {
      return
    }

    setDeleting(imageId)
    try {
      const response = await fetch(`/api/photos/${imageId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        onDeleteSuccess()
      } else {
        alert('Failed to delete image')
      }
    } catch (error) {
      console.error('Error deleting image:', error)
      alert('Error deleting image')
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="gallery-grid">
      {images.map((image) => {
        // Use thumbnail_path if available, otherwise use file_path
        const imageUrl = image.thumbnail_path || image.file_path

        // Debug logging
        if (image.id === 284) { // photo_114.jpg
          console.log('=== IMAGE 284 DEBUG ===')
          console.log('Filename:', image.filename)
          console.log('thumbnail_path:', image.thumbnail_path)
          console.log('file_path:', image.file_path)
          console.log('Using imageUrl:', imageUrl)
        }

        return (
          <div key={image.id} className="gallery-item">
            <div
              className="image-container"
              onClick={() => onImageClick && onImageClick(image)}
              style={{ cursor: onImageClick ? 'pointer' : 'default' }}
            >
              <img
                src={imageUrl}
                alt={image.filename}
                loading="lazy"
                onError={(e) => {
                  console.error('Failed to load image:', imageUrl, 'for', image.filename)
                  e.target.style.border = '2px solid red'
                }}
              />
              <button
                className="delete-btn"
                onClick={(e) => {
                  e.stopPropagation()
                  handleDelete(image.id)
                }}
                disabled={deleting === image.id}
                title="Delete image"
              >
                {deleting === image.id ? '...' : '×'}
              </button>
            </div>
            <div className="image-info">
              <p className="image-filename">{image.filename}</p>
              {image.capture_date && (
                <p className="image-date">
                  📅 {formatDate(image.capture_date)}
                </p>
              )}
              {image.location && image.location.latitude && (
                <p className="image-location">
                  📍 {image.location.city || 'Unknown location'}
                </p>
              )}

              {/* Show categories if classified */}
              {image.image_categories && image.image_categories.length > 0 && (
                <CategoryBadges categories={image.image_categories.map(ic => ({
                  name: ic.name || 'Unknown',
                  confidence: ic.confidence || 0
                }))} />
              )}

              {/* Show emotions if detected */}
              {imageEmotions[image.id] && imageEmotions[image.id].length > 0 && (
                <EmotionBadges emotions={imageEmotions[image.id]} />
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default ImageGallery
