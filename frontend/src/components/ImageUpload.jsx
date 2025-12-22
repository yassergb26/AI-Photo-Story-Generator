import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import './ImageUpload.css'

function ImageUpload({ onUploadSuccess }) {
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [runningAutoMode, setRunningAutoMode] = useState(false)

  const handleAutoMode = async () => {
    if (!confirm('Run Auto Mode? This will:\n\n1. Spread photo dates across your lifetime\n2. Classify all images (AI categories)\n3. Detect emotions in faces\n4. Generate life story chapters\n5. Create story arcs with AI narratives\n\nThis may take a few minutes.\n\nNote: Make sure you\'ve set your birth date first!')) {
      return
    }

    setRunningAutoMode(true)
    setMessage('🤖 Running Auto Mode... Please wait...')

    try {
      const response = await fetch('/api/chapters/auto-generate?user_id=1', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      if (!response.ok) {
        const errorData = await response.json()
        setMessage(`❌ ${errorData.detail || 'Auto-generation failed'}`)
        console.error('Auto-mode error response:', errorData)
        return
      }

      const data = await response.json()
      console.log('Auto-mode result:', data)

      if (data.success) {
        setMessage(`✅ ${data.message}`)
        setTimeout(() => {
          onUploadSuccess()
          setMessage('')
        }, 3000)
      } else {
        setMessage(`❌ ${data.message || 'Auto-generation failed'}`)
      }
    } catch (error) {
      console.error('Auto-mode error:', error)
      setMessage('❌ Error running auto mode. Check console for details.')
    } finally {
      setRunningAutoMode(false)
    }
  }

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return

    setUploading(true)
    setUploadProgress(0)
    setMessage('')

    const formData = new FormData()
    acceptedFiles.forEach(file => {
      formData.append('files', file)
    })

    try {
      const response = await fetch('/api/photos/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.success) {
        // Use the message from backend which includes duplicate info
        setMessage(`✅ ${data.message}`)
        setUploadProgress(100)
        setTimeout(() => {
          onUploadSuccess()
          setMessage('')
          setUploadProgress(0)
        }, 2000)
      } else {
        // Use backend message if available, otherwise show generic error
        setMessage(`❌ ${data.message || 'Upload failed. Please try again.'}`)
      }
    } catch (error) {
      console.error('Upload error:', error)
      setMessage('❌ Error uploading images. Please try again.')
    } finally {
      setUploading(false)
    }
  }, [onUploadSuccess])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpg', '.jpeg', '.png', '.heic', '.webp']
    },
    multiple: true
  })

  return (
    <div className="upload-container">
      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'active' : ''} ${uploading ? 'uploading' : ''}`}
      >
        <input {...getInputProps()} />

        {uploading ? (
          <div className="upload-progress">
            <div className="spinner"></div>
            <p>Uploading images...</p>
          </div>
        ) : (
          <div className="dropzone-content">
            <div className="upload-icon">📤</div>
            {isDragActive ? (
              <p className="dropzone-text">Drop the images here...</p>
            ) : (
              <>
                <p className="dropzone-text">Drag & drop images here</p>
                <p className="dropzone-subtext">or click to select files</p>
                <p className="dropzone-formats">Supported: JPG, PNG, HEIC, WebP</p>
              </>
            )}
          </div>
        )}
      </div>

      {message && (
        <div className={`upload-message ${message.includes('✅') ? 'success' : 'error'}`}>
          {message}
        </div>
      )}

      <div className="auto-mode-section">
        <div className="auto-mode-info">
          <h3>🤖 Auto Mode (Full Demo Pipeline)</h3>
          <p>After uploading photos, click here to automatically process everything:</p>
          <ul>
            <li>📅 Spread dates across your lifetime (demo mode)</li>
            <li>✨ Classify images (categories)</li>
            <li>😊 Detect emotions in faces</li>
            <li>📖 Generate life story chapters</li>
            <li>🎭 Create story arcs with AI narratives</li>
          </ul>
          <p className="auto-mode-note">⚠️ <strong>Important:</strong> Set your birth date in the Chapters tab first!</p>
        </div>
        <button
          className="btn-auto-mode"
          onClick={handleAutoMode}
          disabled={runningAutoMode || uploading}
        >
          {runningAutoMode ? (
            <>
              <span className="spinner-small"></span> Processing...
            </>
          ) : (
            '🚀 Run Auto Mode'
          )}
        </button>
      </div>
    </div>
  )
}

export default ImageUpload
