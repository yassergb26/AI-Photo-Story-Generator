import React from 'react'
import './EmotionBadge.css'

function EmotionBadge({ emotion, percentage, showPercentage = true, size = 'medium' }) {
  const getEmotionIcon = (emotionName) => {
    const icons = {
      happy: '😊',
      excited: '🤩',
      love: '❤️',
      joy: '😄',
      sad: '😢',
      surprised: '😮',
      neutral: '😐',
      reflective: '🤔'
    }
    return icons[emotionName?.toLowerCase()] || '😐'
  }

  const getEmotionColor = (emotionName) => {
    const colors = {
      happy: '#FFD700',
      excited: '#FF6B6B',
      love: '#FF1493',
      joy: '#FFA500',
      sad: '#4682B4',
      surprised: '#9370DB',
      neutral: '#808080',
      reflective: '#5F9EA0'
    }
    return colors[emotionName?.toLowerCase()] || '#808080'
  }

  if (!emotion) {
    return null
  }

  const emotionName = typeof emotion === 'string' ? emotion : emotion.name
  const emotionPercentage = percentage || emotion.percentage || 0

  return (
    <div
      className={`emotion-badge emotion-badge-${size}`}
      style={{ borderColor: getEmotionColor(emotionName) }}
      title={`${emotionName}: ${emotionPercentage.toFixed(0)}%`}
    >
      <span className="emotion-icon">{getEmotionIcon(emotionName)}</span>
      <span className="emotion-name">{emotionName}</span>
      {showPercentage && (
        <span
          className="emotion-percentage"
          style={{ color: getEmotionColor(emotionName) }}
        >
          {emotionPercentage.toFixed(0)}%
        </span>
      )}
    </div>
  )
}

export default EmotionBadge
