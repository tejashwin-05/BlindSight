import { useState } from 'react'
import './FeatureDialog.css'

function FeatureDialog({ feature, onSubmit, onClose }) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const featureConfigs = {
    navigate: {
      title: '🧭 Navigate to Destination',
      placeholder: 'from India Gate to Red Fort',
      inputType: 'text'
    },
    weather: {
      title: '🌤️ Current Weather',
      placeholder: 'Enter city name (e.g., "London", "New York")',
      inputType: 'text'
    },
    forecast: {
      title: '🌦️ Weather Forecast',
      placeholder: 'Enter city name',
      inputType: 'text'
    },
    time: {
      title: '🕐 Current Time & Date',
      placeholder: null,
      inputType: 'none'
    },
    headlines: {
      title: '📰 Top Headlines',
      placeholder: 'Country code (e.g., us, uk, in) or leave blank',
      inputType: 'text'
    },
    search_news: {
      title: '🔍 Search News',
      placeholder: 'Enter search keywords (e.g., "technology", "sports")',
      inputType: 'text'
    },
    emergency: {
      title: '🚨 Emergency Information',
      placeholder: 'Country name (optional)',
      inputType: 'text'
    },
    safety_tips: {
      title: '💡 Safety Tips',
      placeholder: 'Context: walking, crossing, night, indoor, public_transport',
      inputType: 'text'
    }
  }

  const config = featureConfigs[feature] || {}

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    await onSubmit(feature, input)
    setLoading(false)
  }

  if (!feature) return null

  return (
    <div className="feature-dialog-overlay" onClick={onClose}>
      <div className="feature-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <h3>{config.title}</h3>
          <button className="dialog-close-btn" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit} className="dialog-form">
          {config.inputType === 'text' && (
            <input
              type="text"
              className="dialog-input"
              placeholder={config.placeholder}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              autoFocus
            />
          )}

          {config.inputType === 'none' && (
            <p className="dialog-info">Click submit to get current time and date information.</p>
          )}

          <div className="dialog-actions">
            <button
              type="button"
              className="dialog-btn cancel-btn"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="dialog-btn submit-btn"
              disabled={loading}
            >
              {loading ? 'Processing...' : 'Submit'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default FeatureDialog
