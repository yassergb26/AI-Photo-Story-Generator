import React, { useState } from 'react'
import './ExportManager.css'

function ExportManager({ userId = 1 }) {
  const [exporting, setExporting] = useState(false)
  const [exportType, setExportType] = useState(null)

  const handleExportPhotosJSON = async () => {
    setExporting(true)
    setExportType('photos-json')

    try {
      const response = await fetch(`/api/exports/photos/json?user_id=${userId}&include_metadata=true`)
      const data = await response.json()

      // Download JSON file
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `photos_export_${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)

    } catch (error) {
      console.error('Error exporting photos as JSON:', error)
      alert('Failed to export photos as JSON')
    } finally {
      setExporting(false)
      setExportType(null)
    }
  }

  const handleExportPhotosPDF = async () => {
    setExporting(true)
    setExportType('photos-pdf')

    try {
      // Use direct download link approach to bypass fetch timeout issues
      // This allows the browser to handle the download natively without JavaScript timeout limits
      const downloadUrl = `/api/exports/photos/pdf?user_id=${userId}&include_metadata=true`

      // Create a hidden link and trigger download
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = `photo_album_${new Date().toISOString().split('T')[0]}.pdf`
      a.style.display = 'none'
      document.body.appendChild(a)
      a.click()

      // Clean up after a delay
      setTimeout(() => {
        document.body.removeChild(a)
      }, 100)

      // Show success message after a delay (PDF generation takes ~13 seconds)
      setTimeout(() => {
        alert('PDF generation started! The download will begin automatically when ready (may take 10-15 seconds for large albums).')
      }, 500)

    } catch (error) {
      console.error('Error exporting photos as PDF:', error)
      alert(`Failed to export photos as PDF: ${error.message}`)
    } finally {
      // Keep the loading state for a bit longer to indicate processing
      setTimeout(() => {
        setExporting(false)
        setExportType(null)
      }, 2000)
    }
  }

  const handleExportStoriesJSON = async () => {
    setExporting(true)
    setExportType('stories-json')

    try {
      const response = await fetch(`/api/exports/stories/json?user_id=${userId}`)
      const data = await response.json()

      // Download JSON file
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `stories_export_${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)

    } catch (error) {
      console.error('Error exporting stories as JSON:', error)
      alert('Failed to export stories as JSON')
    } finally {
      setExporting(false)
      setExportType(null)
    }
  }

  const handleExportLifeEventsJSON = async () => {
    setExporting(true)
    setExportType('life-events-json')

    try {
      const response = await fetch(`/api/exports/life-events/json?user_id=${userId}`)
      const data = await response.json()

      // Download JSON file
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `life_events_export_${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)

    } catch (error) {
      console.error('Error exporting life events as JSON:', error)
      alert('Failed to export life events as JSON')
    } finally {
      setExporting(false)
      setExportType(null)
    }
  }

  return (
    <div className="export-manager">
      <div className="export-header">
        <h2>📦 Export Your Data</h2>
        <p className="subtitle">Download your photos, stories, and life events in various formats</p>
      </div>

      <div className="export-cards">
        {/* Photos Export */}
        <div className="export-card">
          <div className="export-card-icon">📸</div>
          <h3>Photo Collection</h3>
          <p>Export all your photos with metadata</p>

          <div className="export-buttons">
            <button
              className="export-btn json-btn"
              onClick={handleExportPhotosJSON}
              disabled={exporting}
            >
              {exporting && exportType === 'photos-json' ? (
                <>
                  <span className="spinner-small"></span> Exporting...
                </>
              ) : (
                '📄 Export as JSON'
              )}
            </button>

            <button
              className="export-btn pdf-btn"
              onClick={handleExportPhotosPDF}
              disabled={exporting}
            >
              {exporting && exportType === 'photos-pdf' ? (
                <>
                  <span className="spinner-small"></span> Generating PDF...
                </>
              ) : (
                '📕 Export as PDF Album'
              )}
            </button>
          </div>

          <div className="export-info">
            <span className="info-badge">🔹 Includes EXIF data</span>
            <span className="info-badge">🔹 GPS coordinates</span>
            <span className="info-badge">🔹 Capture dates</span>
          </div>
        </div>

        {/* Stories Export */}
        <div className="export-card">
          <div className="export-card-icon">📖</div>
          <h3>Story Collection</h3>
          <p>Export your auto-generated stories</p>

          <div className="export-buttons">
            <button
              className="export-btn json-btn"
              onClick={handleExportStoriesJSON}
              disabled={exporting}
            >
              {exporting && exportType === 'stories-json' ? (
                <>
                  <span className="spinner-small"></span> Exporting...
                </>
              ) : (
                '📄 Export as JSON'
              )}
            </button>
          </div>

          <div className="export-info">
            <span className="info-badge">🔹 Story narratives</span>
            <span className="info-badge">🔹 Photo references</span>
            <span className="info-badge">🔹 Timestamps</span>
          </div>
        </div>

        {/* Life Events Export */}
        <div className="export-card">
          <div className="export-card-icon">🎉</div>
          <h3>Life Events</h3>
          <p>Export your important life milestones</p>

          <div className="export-buttons">
            <button
              className="export-btn json-btn"
              onClick={handleExportLifeEventsJSON}
              disabled={exporting}
            >
              {exporting && exportType === 'life-events-json' ? (
                <>
                  <span className="spinner-small"></span> Exporting...
                </>
              ) : (
                '📄 Export as JSON'
              )}
            </button>
          </div>

          <div className="export-info">
            <span className="info-badge">🔹 Event details</span>
            <span className="info-badge">🔹 Locations</span>
            <span className="info-badge">🔹 Photo links</span>
          </div>
        </div>
      </div>

      <div className="export-footer">
        <div className="export-note">
          <strong>💡 Note:</strong> JSON files can be used to backup your data or import into other applications.
          PDF albums are perfect for sharing and printing.
        </div>
      </div>
    </div>
  )
}

export default ExportManager
