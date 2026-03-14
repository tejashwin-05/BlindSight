import { useEffect } from 'react'
import './MCPNotification.css'

function MCPNotification({ notification, onClose }) {
  useEffect(() => {
    if (notification) {
      // Auto-close after 10 seconds
      const timer = setTimeout(() => {
        onClose()
      }, 10000)
      
      return () => clearTimeout(timer)
    }
  }, [notification, onClose])

  if (!notification) return null

  const getIcon = (tool) => {
    const icons = {
      time: '🕐',
      weather: '🌤️',
      forecast: '🌦️',
      headlines: '📰',
      search_news: '🔍',
      navigate: '🧭',
      emergency: '🚨',
      safety_tips: '💡'
    }
    return icons[tool] || '✨'
  }

  return (
    <div className="mcp-notification-overlay" onClick={onClose}>
      <div className="mcp-notification" onClick={(e) => e.stopPropagation()}>
        <div className="notification-header">
          <span className="notification-icon">{getIcon(notification.tool)}</span>
          <h3 className="notification-title">
            {notification.tool.replace('_', ' ').toUpperCase()}
          </h3>
          <button className="notification-close" onClick={onClose}>✕</button>
        </div>
        
        <div className="notification-content">
          {notification.result?.error ? (
            <p className="notification-error">{notification.result.error}</p>
          ) : (
            <>
              {notification.result?.spoken_summary && (
                <p className="notification-summary">{notification.result.spoken_summary}</p>
              )}
              
              {notification.result?.articles && (
                <div className="notification-list">
                  {notification.result.articles.slice(0, 3).map((article, idx) => (
                    <div key={idx} className="notification-item">
                      <strong>{article.title}</strong>
                      {article.description && <p>{article.description}</p>}
                    </div>
                  ))}
                </div>
              )}
              
              {notification.result?.steps && (
                <div className="notification-info">
                  <p><strong>Navigation Steps:</strong> {notification.result.steps.length}</p>
                  <p><strong>Duration:</strong> {notification.result.duration_min} minutes</p>
                </div>
              )}
              
              {notification.result?.tips && (
                <ul className="notification-tips">
                  {notification.result.tips.map((tip, idx) => (
                    <li key={idx}>{tip}</li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default MCPNotification
