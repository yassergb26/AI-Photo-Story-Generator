import React, { useState } from 'react'
import './AdminPanel.css'

const AdminPanel = ({ userId }) => {
  const [deleting, setDeleting] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(null)

  const handleDeleteAll = async (type) => {
    if (confirmDelete !== type) {
      setConfirmDelete(type)
      setTimeout(() => setConfirmDelete(null), 5000) // Reset after 5 seconds
      return
    }

    setDeleting(type)
    try {
      let endpoint = ''
      switch (type) {
        case 'photos':
          endpoint = `/api/photos/delete-all?user_id=${userId}`
          break
        case 'stories':
          endpoint = `/api/stories/delete-all?user_id=${userId}`
          break
        case 'patterns':
          endpoint = `/api/patterns/delete-all?user_id=${userId}`
          break
        case 'chapters':
          endpoint = `/api/chapters/delete-all?user_id=${userId}`
          break
        case 'timeline':
          endpoint = `/api/life-events/delete-all?user_id=${userId}`
          break
        default:
          return
      }

      const response = await fetch(endpoint, { method: 'DELETE' })

      if (response.ok) {
        const data = await response.json()
        alert(`✅ Successfully deleted! ${data.message || ''}`)
        window.location.reload()
      } else {
        const error = await response.text()
        alert(`❌ Failed to delete: ${error}`)
      }
    } catch (error) {
      console.error(`Error deleting ${type}:`, error)
      alert(`❌ Error: ${error.message}`)
    } finally {
      setDeleting(null)
      setConfirmDelete(null)
    }
  }

  const DeleteButton = ({ type, label, icon, description }) => (
    <div className="delete-section">
      <div className="delete-info">
        <h3>{icon} {label}</h3>
        <p>{description}</p>
      </div>
      <button
        className={`btn-delete-all ${confirmDelete === type ? 'confirm-mode' : ''}`}
        onClick={() => handleDeleteAll(type)}
        disabled={deleting === type}
      >
        {deleting === type ? (
          '⏳ Deleting...'
        ) : confirmDelete === type ? (
          '⚠️ Click Again to Confirm'
        ) : (
          `🗑️ Delete All ${label}`
        )}
      </button>
    </div>
  )

  return (
    <div className="admin-panel">
      <div className="admin-header">
        <h2>⚙️ Admin Panel</h2>
        <p className="warning">⚠️ Warning: These actions cannot be undone!</p>
      </div>

      <div className="delete-sections">
        <DeleteButton
          type="photos"
          label="Photos"
          icon="📷"
          description="Delete all uploaded photos and their metadata (emotions, categories, etc.)"
        />

        <DeleteButton
          type="stories"
          label="Stories"
          icon="📖"
          description="Delete all story arcs (keeps photos)"
        />

        <DeleteButton
          type="patterns"
          label="Patterns"
          icon="🔍"
          description="Delete all detected patterns"
        />

        <DeleteButton
          type="chapters"
          label="Chapters"
          icon="📚"
          description="Delete all chapters and their story arcs"
        />

        <DeleteButton
          type="timeline"
          label="Life Events"
          icon="📅"
          description="Delete all timeline life events"
        />
      </div>
    </div>
  )
}

export default AdminPanel
