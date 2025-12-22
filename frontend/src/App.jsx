import React, { useState, useEffect } from 'react'
import ImageUpload from './components/ImageUpload'
import ImageGallery from './components/ImageGallery'
import PatternsDashboard from './components/PatternsDashboard'
import StoriesLibrary from './components/StoriesLibrary'
import Timeline from './components/Timeline'
import MapView from './components/MapView'
import AdvancedSearch from './components/AdvancedSearch'
import ImageDetailModal from './components/ImageDetailModal'
import LifeEventsManager from './components/LifeEventsManager'
import ExportManager from './components/ExportManager'
import ChapterView from './components/ChapterView'
import AdminPanel from './components/AdminPanel'
import './App.css'

function App() {
  const [images, setImages] = useState([])
  const [loading, setLoading] = useState(false)
  const [autoProcessing, setAutoProcessing] = useState(false)
  const [processingMessage, setProcessingMessage] = useState('')
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [imageEmotions, setImageEmotions] = useState({})
  const [activeView, setActiveView] = useState('gallery') // 'gallery' or 'timeline'
  const [searchFilters, setSearchFilters] = useState(null)
  const [selectedImage, setSelectedImage] = useState(null)

  // Fetch images on mount
  useEffect(() => {
    fetchImages()
  }, [])

  // Fetch emotions for all images when images change
  useEffect(() => {
    const fetchAllEmotions = async () => {
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
      fetchAllEmotions()
    }
  }, [images])

  // Apply all filters (emotion + advanced search)
  const applyFilters = (imagesList) => {
    let filtered = imagesList

    // Apply advanced search filters
    if (searchFilters) {
      // Text search
      if (searchFilters.searchText) {
        const searchLower = searchFilters.searchText.toLowerCase()
        filtered = filtered.filter(image =>
          image.filename.toLowerCase().includes(searchLower)
        )
      }

      // Date range filter
      if (searchFilters.dateFrom || searchFilters.dateTo) {
        filtered = filtered.filter(image => {
          const imageDate = new Date(image.capture_date || image.upload_date)
          const fromDate = searchFilters.dateFrom ? new Date(searchFilters.dateFrom) : null
          const toDate = searchFilters.dateTo ? new Date(searchFilters.dateTo) : null

          if (fromDate && imageDate < fromDate) return false
          if (toDate && imageDate > toDate) return false
          return true
        })
      }

      // Emotion filters
      if (searchFilters.emotions && searchFilters.emotions.length > 0) {
        filtered = filtered.filter(image => {
          const emotions = imageEmotions[image.id]
          if (!emotions || emotions.length === 0) return false
          // Case-insensitive emotion matching
          return emotions.some(e =>
            searchFilters.emotions.some(filterEmotion =>
              filterEmotion.toLowerCase() === e.emotion.toLowerCase()
            )
          )
        })
      }

      // Category filters
      if (searchFilters.categories && searchFilters.categories.length > 0) {
        filtered = filtered.filter(image => {
          if (!image.image_categories || image.image_categories.length === 0) return false
          return image.image_categories.some(cat =>
            searchFilters.categories.includes(cat.name || cat.category_name)
          )
        })
      }
    }

    return filtered
  }

  const filteredImages = applyFilters(images)

  const handleFilterChange = (filters) => {
    setSearchFilters(filters)
  }

  const handleResetFilters = () => {
    setSearchFilters(null)
  }

  const fetchImages = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/photos')
      const data = await response.json()

      // Extract images array from response object
      const imagesList = data.images || []

      // Fetch image categories for each image
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
    } catch (error) {
      console.error('Error fetching images:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUploadSuccess = async () => {
    // Simply refresh images to show newly uploaded images
    // No auto-processing - user will click "Run Auto Mode" button when ready
    await fetchImages()
    setRefreshTrigger(prev => prev + 1)
  }

  const handleDeleteSuccess = () => {
    // Refresh images after delete
    fetchImages()
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>📸 Image Event Categorization</h1>
        <p>Upload your photos to organize and discover patterns</p>
      </header>

      <main className="App-main">
        <ImageUpload onUploadSuccess={handleUploadSuccess} />

        {autoProcessing && (
          <div className="auto-processing-banner">
            <div className="spinner"></div>
            <span>{processingMessage}</span>
          </div>
        )}

        <div className="patterns-section">
          <PatternsDashboard userId={1} refreshTrigger={refreshTrigger} />
        </div>

        <div className="stories-section">
          <StoriesLibrary userId={1} refreshTrigger={refreshTrigger} />
        </div>

        <div className="life-events-section">
          <LifeEventsManager onRefresh={fetchImages} />
        </div>

        <div className="export-section">
          <ExportManager userId={1} />
        </div>

        <div className="view-toggle-section">
          <div className="view-toggle-buttons">
            <button
              className={`view-toggle-btn ${activeView === 'gallery' ? 'active' : ''}`}
              onClick={() => setActiveView('gallery')}
            >
              📷 Gallery View
            </button>
            <button
              className={`view-toggle-btn ${activeView === 'timeline' ? 'active' : ''}`}
              onClick={() => setActiveView('timeline')}
            >
              📅 Timeline View
            </button>
            <button
              className={`view-toggle-btn ${activeView === 'map' ? 'active' : ''}`}
              onClick={() => setActiveView('map')}
            >
              🗺️ Map View
            </button>
            <button
              className={`view-toggle-btn ${activeView === 'chapters' ? 'active' : ''}`}
              onClick={() => setActiveView('chapters')}
            >
              📚 Chapters
            </button>
            <button
              className={`view-toggle-btn ${activeView === 'admin' ? 'active' : ''}`}
              onClick={() => setActiveView('admin')}
            >
              ⚙️ Admin
            </button>
          </div>
        </div>

        {/* Advanced Search */}
        {!loading && images.length > 0 && (
          <AdvancedSearch
            onFilterChange={handleFilterChange}
            onReset={handleResetFilters}
          />
        )}

        {activeView === 'gallery' ? (
          <div className="gallery-section">
            <h2>Your Photos ({filteredImages.length} of {images.length})</h2>
            {searchFilters && (
              <div className="filter-info">
                Advanced filters active • Showing {filteredImages.length} of {images.length} images
              </div>
            )}
            {loading ? (
              <div className="loading">Loading images...</div>
            ) : (
              <ImageGallery
                images={filteredImages}
                onDeleteSuccess={handleDeleteSuccess}
                onRefresh={fetchImages}
                onImageClick={setSelectedImage}
              />
            )}
          </div>
        ) : activeView === 'timeline' ? (
          <div className="timeline-section">
            <Timeline userId={1} />
          </div>
        ) : activeView === 'map' ? (
          <div className="map-section">
            <MapView userId={1} onImageClick={setSelectedImage} />
          </div>
        ) : activeView === 'chapters' ? (
          <div className="chapters-section">
            <ChapterView userId={1} refreshTrigger={refreshTrigger} />
          </div>
        ) : (
          <div className="admin-section">
            <AdminPanel userId={1} />
          </div>
        )}

        {/* Image Detail Modal */}
        {selectedImage && (
          <ImageDetailModal
            image={selectedImage}
            onClose={() => setSelectedImage(null)}
            onDelete={() => {
              setSelectedImage(null)
              fetchImages()
            }}
          />
        )}
      </main>
    </div>
  )
}

export default App
