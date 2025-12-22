import React, { useState, useEffect } from 'react'
import './EmotionFilter.css'

function EmotionFilter({ onFilterChange }) {
  const [selectedEmotion, setSelectedEmotion] = useState('all')
  const [emotions, setEmotions] = useState([])

  useEffect(() => {
    // Fetch available emotions from backend
    const fetchEmotions = async () => {
      try {
        const response = await fetch('/api/emotions/')
        if (response.ok) {
          const data = await response.json()

          // Remove duplicates by creating a Map with lowercase names as keys
          const uniqueEmotionsMap = new Map()
          data.forEach(emotion => {
            const lowerName = emotion.name.toLowerCase()
            if (!uniqueEmotionsMap.has(lowerName)) {
              uniqueEmotionsMap.set(lowerName, emotion)
            }
          })

          // Convert Map back to array
          const uniqueEmotions = Array.from(uniqueEmotionsMap.values())
          setEmotions(uniqueEmotions)
        }
      } catch (error) {
        console.error('Error fetching emotions:', error)
      }
    }

    fetchEmotions()
  }, [])

  const handleEmotionClick = (emotionName) => {
    const newEmotion = emotionName === selectedEmotion ? 'all' : emotionName
    setSelectedEmotion(newEmotion)
    onFilterChange(newEmotion)
  }

  return (
    <div className="emotion-filter">
      <div className="filter-header">
        <span className="filter-icon">😊</span>
        <span className="filter-label">Filter by Emotion:</span>
      </div>
      <div className="emotion-buttons">
        <button
          className={`emotion-filter-btn ${selectedEmotion === 'all' ? 'active' : ''}`}
          onClick={() => handleEmotionClick('all')}
        >
          All Images
        </button>
        {emotions.map((emotion) => (
          <button
            key={emotion.id}
            className={`emotion-filter-btn ${selectedEmotion === emotion.name ? 'active' : ''}`}
            style={{
              backgroundColor: selectedEmotion === emotion.name ? emotion.color_code : 'transparent',
              borderColor: emotion.color_code,
              color: selectedEmotion === emotion.name ? 'white' : emotion.color_code
            }}
            onClick={() => handleEmotionClick(emotion.name)}
            title={emotion.description}
          >
            {emotion.name}
          </button>
        ))}
      </div>
    </div>
  )
}

export default EmotionFilter
