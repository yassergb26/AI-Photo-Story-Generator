import React from 'react'
import './CategoryBadges.css'

function CategoryBadges({ categories }) {
  if (!categories || categories.length === 0) {
    return null
  }

  // Category colors
  const categoryColors = {
    'Celebrations': '#FF6B6B',
    'Travel & Adventures': '#4ECDC4',
    'Family & Friends': '#45B7D1',
    'Nature & Outdoors': '#96CEB4',
    'Food & Dining': '#FFEAA7',
    'Work & Professional': '#6C5CE7',
    'Hobbies & Activities': '#FD79A8',
    'Pets & Animals': '#FF7675'
  }

  return (
    <div className="category-badges">
      {categories.map((category, index) => {
        const color = categoryColors[category.name] || '#95A5A6'
        const confidence = (category.confidence * 100).toFixed(0)

        return (
          <div
            key={index}
            className="category-badge"
            style={{ backgroundColor: color }}
            title={`${confidence}% confidence`}
          >
            <span className="category-name">{category.name}</span>
            <span className="category-confidence">{confidence}%</span>
          </div>
        )
      })}
    </div>
  )
}

export default CategoryBadges
