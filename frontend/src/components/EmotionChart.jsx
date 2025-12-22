import React from 'react'
import './EmotionChart.css'

function EmotionChart({ emotions, type = 'bar', showLabels = true }) {
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

  if (!emotions || emotions.length === 0) {
    return (
      <div className="emotion-chart-empty">
        <p>No emotion data available</p>
      </div>
    )
  }

  // Sort emotions by percentage (descending)
  const sortedEmotions = [...emotions].sort((a, b) => b.percentage - a.percentage)

  // Calculate total for pie chart
  const total = sortedEmotions.reduce((sum, e) => sum + e.percentage, 0)

  if (type === 'pie') {
    let currentAngle = 0
    const segments = sortedEmotions.map((emotion) => {
      const percentage = (emotion.percentage / total) * 100
      const angle = (percentage / 100) * 360
      const segment = {
        emotion: emotion.emotion || emotion.name,
        percentage: emotion.percentage,
        startAngle: currentAngle,
        angle: angle,
        color: getEmotionColor(emotion.emotion || emotion.name)
      }
      currentAngle += angle
      return segment
    })

    return (
      <div className="emotion-chart emotion-chart-pie">
        <svg viewBox="0 0 200 200" className="pie-chart">
          {segments.map((segment, index) => {
            const startAngle = segment.startAngle - 90 // Start from top
            const endAngle = startAngle + segment.angle

            const startRad = (startAngle * Math.PI) / 180
            const endRad = (endAngle * Math.PI) / 180

            const x1 = 100 + 80 * Math.cos(startRad)
            const y1 = 100 + 80 * Math.sin(startRad)
            const x2 = 100 + 80 * Math.cos(endRad)
            const y2 = 100 + 80 * Math.sin(endRad)

            const largeArc = segment.angle > 180 ? 1 : 0

            const pathData = [
              `M 100 100`,
              `L ${x1} ${y1}`,
              `A 80 80 0 ${largeArc} 1 ${x2} ${y2}`,
              'Z'
            ].join(' ')

            return (
              <path
                key={index}
                d={pathData}
                fill={segment.color}
                stroke="white"
                strokeWidth="2"
                className="pie-segment"
              >
                <title>{`${segment.emotion}: ${segment.percentage.toFixed(1)}%`}</title>
              </path>
            )
          })}
        </svg>

        {showLabels && (
          <div className="emotion-legend">
            {sortedEmotions.map((emotion, index) => (
              <div key={index} className="legend-item">
                <span
                  className="legend-color"
                  style={{ backgroundColor: getEmotionColor(emotion.emotion || emotion.name) }}
                />
                <span className="legend-icon">{getEmotionIcon(emotion.emotion || emotion.name)}</span>
                <span className="legend-label">{emotion.emotion || emotion.name}</span>
                <span className="legend-value">{emotion.percentage.toFixed(0)}%</span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // Bar chart (default)
  const maxPercentage = Math.max(...sortedEmotions.map(e => e.percentage))

  return (
    <div className="emotion-chart emotion-chart-bar">
      <div className="bar-chart">
        {sortedEmotions.map((emotion, index) => {
          const emotionName = emotion.emotion || emotion.name
          const height = (emotion.percentage / maxPercentage) * 100

          return (
            <div key={index} className="bar-item">
              <div className="bar-container">
                <div
                  className="bar-fill"
                  style={{
                    height: `${height}%`,
                    backgroundColor: getEmotionColor(emotionName)
                  }}
                  title={`${emotionName}: ${emotion.percentage.toFixed(1)}%`}
                />
              </div>
              {showLabels && (
                <div className="bar-label">
                  <span className="bar-icon">{getEmotionIcon(emotionName)}</span>
                  <span className="bar-name">{emotionName}</span>
                  <span className="bar-percentage">{emotion.percentage.toFixed(0)}%</span>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default EmotionChart
