import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [healthStatus, setHealthStatus] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    // Phase 0: Call backend health endpoint
    fetch('http://localhost:5000/api/health')
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok')
        }
        return response.json()
      })
      .then(data => setHealthStatus(data))
      .catch(err => setError(err.message))
  }, [])

  return (
    <div className="App">
      <header className="App-header">
        <h1>Clean Air & Climate Resilience Platform</h1>
        <p>Phase 0: Project Foundation</p>
        
        <div className="status-box">
          <h2>Backend Connection Status:</h2>
          {error ? (
            <div className="error">
              <p>❌ Error connecting to backend:</p>
              <p>{error}</p>
              <small>Is the Flask server running on port 5000?</small>
            </div>
          ) : healthStatus ? (
            <div className="success">
              <p>✅ Backend is connected!</p>
              <pre>{JSON.stringify(healthStatus, null, 2)}</pre>
            </div>
          ) : (
            <p>⏳ Checking backend status...</p>
          )}
        </div>
      </header>
    </div>
  )
}

export default App
