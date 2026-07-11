import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [apiStatus, setApiStatus] = useState<'checking' | 'ok' | 'down'>('checking')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => setApiStatus(data.status === 'ok' ? 'ok' : 'down'))
      .catch(() => setApiStatus('down'))
  }, [])

  return (
    <main className="shell">
      <h1>Hearth</h1>
      <p>Phase 0 scaffold — dashboard, accounts, and investments screens come next.</p>
      <p>API: {apiStatus}</p>
    </main>
  )
}

export default App
