import { useState } from 'react'
import './AssistantPanel.css'

function AssistantPanel({ isOpen, onClose, onFeatureRequest }) {
  const [activeCategory, setActiveCategory] = useState('info')

  const features = {
    navigation: [
      { id: 'navigate', icon: '🧭', title: 'Navigate', description: 'Get turn-by-turn directions' }
    ],
    info: [
      { id: 'weather', icon: '🌤️', title: 'Current Weather', description: 'Get weather conditions' },
      { id: 'forecast', icon: '🌦️', title: 'Weather Forecast', description: 'Check upcoming weather' },
      { id: 'time', icon: '🕐', title: 'Time & Date', description: 'Get current time and date' }
    ],
    news: [
      { id: 'headlines', icon: '📰', title: 'Top Headlines', description: 'Latest news headlines' },
      { id: 'search_news', icon: '🔍', title: 'Search News', description: 'Find specific news topics' }
    ],
    safety: [
      { id: 'emergency', icon: '🚨', title: 'Emergency Info', description: 'Emergency numbers and help' },
      { id: 'safety_tips', icon: '💡', title: 'Safety Tips', description: 'Context-specific safety advice' }
    ]
  }

  const categories = [
    { id: 'info', icon: 'ℹ️', label: 'Information' },
    { id: 'news', icon: '📰', label: 'News' },
    { id: 'navigation', icon: '🧭', label: 'Navigation' },
    { id: 'safety', icon: '🛡️', label: 'Safety' }
  ]

  if (!isOpen) return null

  return (
    <div className="assistant-overlay" onClick={onClose}>
      <div className="assistant-panel" onClick={(e) => e.stopPropagation()}>
        <div className="panel-header">
          <h2>🤖 AI Assistant</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="category-tabs">
          {categories.map(cat => (
            <button
              key={cat.id}
              className={`category-tab ${activeCategory === cat.id ? 'active' : ''}`}
              onClick={() => setActiveCategory(cat.id)}
            >
              <span className="tab-icon">{cat.icon}</span>
              <span className="tab-label">{cat.label}</span>
            </button>
          ))}
        </div>

        <div className="features-grid">
          {features[activeCategory].map(feature => (
            <button
              key={feature.id}
              className="feature-card"
              onClick={() => {
                onFeatureRequest(feature.id)
                onClose()
              }}
            >
              <div className="feature-icon">{feature.icon}</div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-description">{feature.description}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default AssistantPanel
