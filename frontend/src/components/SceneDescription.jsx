import './SceneDescription.css'

function SceneDescription({ data }) {
  const { status, description } = data

  if (status === 'processing') {
    return (
      <div className="scene-description processing">
        <div className="spinner"></div>
        <h2>Analyzing Scene...</h2>
        <p>Please wait while AI processes the environment</p>
      </div>
    )
  }

  return (
    <div className="scene-description">
      <div className="description-header">
        <span className="icon">🔍</span>
        <h2>Scene Analysis</h2>
      </div>
      
      <div className="description-content">
        <p>{description}</p>
      </div>
      
      <div className="description-footer">
        <small>Powered by Florence-2 Vision AI</small>
      </div>
    </div>
  )
}

export default SceneDescription
