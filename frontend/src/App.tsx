import './App.css'

function App() {
  return (
    <main className="app-shell">
      <section className="workspace" aria-labelledby="workspace-title">
        <header className="workspace-header">
          <div>
            <h1 id="workspace-title">Adaptive RAG</h1>
          </div>
          <span className="status">Local</span>
        </header>

        <div className="workspace-grid">
          <section className="panel panel-primary" aria-labelledby="chat-title">
            <div>
              <p className="panel-label">Chat</p>
              <h2 id="chat-title">Workspace</h2>
            </div>
            <div className="message-card">
              <span className="message-role">Assistant</span>
              <p>No response yet.</p>
            </div>
          </section>

          <aside className="panel" aria-labelledby="history-title">
            <div>
              <p className="panel-label">History</p>
              <h2 id="history-title">Sessions</h2>
            </div>
            <ul className="session-list" aria-label="Session placeholders">
              <li>
                <span>No sessions yet</span>
                <strong>Empty</strong>
              </li>
            </ul>
          </aside>
        </div>
      </section>
    </main>
  )
}

export default App
