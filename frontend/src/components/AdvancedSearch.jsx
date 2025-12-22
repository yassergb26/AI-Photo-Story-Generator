import React, { useState, useEffect } from 'react'
import './AdvancedSearch.css'

function AdvancedSearch({ onFilterChange, onReset }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [filters, setFilters] = useState({
    dateFrom: '',
    dateTo: '',
    emotions: [],
    categories: [],
    searchText: ''
  })
  const [availableEmotions, setAvailableEmotions] = useState([])
  const [availableCategories, setAvailableCategories] = useState([])

  useEffect(() => {
    fetchEmotions()
    fetchCategories()
  }, [])

  const fetchEmotions = async () => {
    try {
      const response = await fetch('/api/emotions/')
      if (response.ok) {
        const data = await response.json()
        // Remove duplicates
        const uniqueEmotionsMap = new Map()
        data.forEach(emotion => {
          const lowerName = emotion.name.toLowerCase()
          if (!uniqueEmotionsMap.has(lowerName)) {
            uniqueEmotionsMap.set(lowerName, emotion)
          }
        })
        setAvailableEmotions(Array.from(uniqueEmotionsMap.values()))
      }
    } catch (error) {
      console.error('Error fetching emotions:', error)
    }
  }

  const fetchCategories = async () => {
    try {
      const response = await fetch('/api/classifications/categories')
      if (response.ok) {
        const data = await response.json()
        setAvailableCategories(data)
      }
    } catch (error) {
      console.error('Error fetching categories:', error)
    }
  }

  const handleFilterChange = (field, value) => {
    const newFilters = { ...filters, [field]: value }
    setFilters(newFilters)
    onFilterChange(newFilters)
  }

  const toggleEmotion = (emotionName) => {
    const newEmotions = filters.emotions.includes(emotionName)
      ? filters.emotions.filter(e => e !== emotionName)
      : [...filters.emotions, emotionName]
    handleFilterChange('emotions', newEmotions)
  }

  const toggleCategory = (categoryName) => {
    const newCategories = filters.categories.includes(categoryName)
      ? filters.categories.filter(c => c !== categoryName)
      : [...filters.categories, categoryName]
    handleFilterChange('categories', newCategories)
  }

  const handleReset = () => {
    const resetFilters = {
      dateFrom: '',
      dateTo: '',
      emotions: [],
      categories: [],
      searchText: ''
    }
    setFilters(resetFilters)
    onReset()
  }

  const hasActiveFilters = () => {
    return filters.dateFrom || filters.dateTo ||
           filters.emotions.length > 0 ||
           filters.categories.length > 0 ||
           filters.searchText
  }

  return (
    <div className="advanced-search">
      <div className="search-header">
        <button
          className="search-toggle"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <span className="search-icon">🔍</span>
          <span>Advanced Search & Filters</span>
          <span className={`expand-icon ${isExpanded ? 'expanded' : ''}`}>▼</span>
        </button>
        {hasActiveFilters() && (
          <button className="reset-btn" onClick={handleReset}>
            Clear All
          </button>
        )}
      </div>

      {isExpanded && (
        <div className="search-content">
          {/* Text Search */}
          <div className="search-section">
            <label className="search-label">Search by filename or description</label>
            <input
              type="text"
              className="search-input"
              placeholder="Type to search..."
              value={filters.searchText}
              onChange={(e) => handleFilterChange('searchText', e.target.value)}
            />
          </div>

          {/* Date Range */}
          <div className="search-section">
            <label className="search-label">Date Range</label>
            <div className="date-range">
              <input
                type="date"
                className="date-input"
                value={filters.dateFrom}
                onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
                placeholder="From"
              />
              <span className="date-separator">to</span>
              <input
                type="date"
                className="date-input"
                value={filters.dateTo}
                onChange={(e) => handleFilterChange('dateTo', e.target.value)}
                placeholder="To"
              />
            </div>
          </div>

          {/* Emotion Filters */}
          <div className="search-section">
            <label className="search-label">
              Filter by Emotions ({filters.emotions.length} selected)
            </label>
            <div className="filter-chips">
              {availableEmotions.map((emotion) => (
                <button
                  key={emotion.id}
                  className={`filter-chip ${filters.emotions.includes(emotion.name) ? 'active' : ''}`}
                  style={{
                    borderColor: emotion.color_code,
                    backgroundColor: filters.emotions.includes(emotion.name) ? emotion.color_code : 'transparent',
                    color: filters.emotions.includes(emotion.name) ? 'white' : emotion.color_code
                  }}
                  onClick={() => toggleEmotion(emotion.name)}
                  title={emotion.description}
                >
                  {emotion.name}
                </button>
              ))}
            </div>
          </div>

          {/* Category Filters */}
          <div className="search-section">
            <label className="search-label">
              Filter by Categories ({filters.categories.length} selected)
            </label>
            <div className="filter-chips">
              {availableCategories.map((category) => (
                <button
                  key={category.id}
                  className={`filter-chip ${filters.categories.includes(category.name) ? 'active' : ''}`}
                  onClick={() => toggleCategory(category.name)}
                  title={category.description}
                >
                  {category.name}
                </button>
              ))}
            </div>
          </div>

          {/* Active Filters Summary */}
          {hasActiveFilters() && (
            <div className="active-filters-summary">
              <strong>Active Filters:</strong>
              {filters.searchText && <span className="filter-tag">Text: "{filters.searchText}"</span>}
              {filters.dateFrom && <span className="filter-tag">From: {filters.dateFrom}</span>}
              {filters.dateTo && <span className="filter-tag">To: {filters.dateTo}</span>}
              {filters.emotions.map(e => (
                <span key={e} className="filter-tag emotion-tag">{e}</span>
              ))}
              {filters.categories.map(c => (
                <span key={c} className="filter-tag category-tag">{c}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default AdvancedSearch
