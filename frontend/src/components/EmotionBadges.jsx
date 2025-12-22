import React from 'react'
import './EmotionBadges.css'

function EmotionBadges({ emotions }) {
  if (!emotions || emotions.length === 0) {
    return null
  }

  // Emotion colors matching HSEmotion emotions in database
  const emotionColors = {
    'Anger': '#FF6B6B',
    'Contempt': '#E17055',
    'Disgust': '#6C5CE7',
    'Fear': '#A29BFE',
    'Happiness': '#FFD93D',
    'Neutral': '#95E1D3',
    'Sadness': '#74B9FF',
    'Surprise': '#FD79A8'
  }

  // Sort by confidence and take top 2
  const topEmotions = emotions
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 2)

  return (
    <div className="emotion-badges">
      {topEmotions.map((emotion, index) => {
        const color = emotionColors[emotion.emotion] || '#95A5A6'
        const confidence = (emotion.confidence * 100).toFixed(0)

        return (
          <div
            key={index}
            className="emotion-badge"
            style={{ backgroundColor: color }}
            title={`${emotion.emotion} - ${confidence}% confidence`}
          >
            <span className="emotion-name">{emotion.emotion}</span>
            <span className="emotion-confidence">{confidence}%</span>
          </div>
        )
      })}
    </div>
  )
}

export default EmotionBadges
