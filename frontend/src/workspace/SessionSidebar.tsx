import { useWorkspace } from "./WorkspaceContext";

export function SessionSidebar() {
  const {
    sessions,
    currentSessionId,
    selectSession,
    createSession,
    deleteSession,
    loading,
  } = useWorkspace();

  return (
    <aside className="panel sidebar">
      <div className="panel-header">
        <h2>会话</h2>
        <button
          type="button"
          className="btn-ghost"
          onClick={() => void createSession()}
          disabled={loading}
        >
          新建
        </button>
      </div>
      <ul className="session-list">
        {sessions.map((s) => (
          <li key={s.id}>
            <button
              type="button"
              className={
                s.id === currentSessionId ? "session-item active" : "session-item"
              }
              onClick={() => void selectSession(s.id)}
              disabled={loading}
            >
              <span className="session-title">{s.title}</span>
            </button>
            <button
              type="button"
              className="btn-icon"
              title="删除会话"
              aria-label="删除会话"
              disabled={loading}
              onClick={(e) => {
                e.stopPropagation();
                void deleteSession(s.id);
              }}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
