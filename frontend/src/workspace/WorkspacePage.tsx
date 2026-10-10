import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { SessionSidebar } from "./SessionSidebar";
import { ChatPanel } from "./ChatPanel";
import { ChartPanel } from "./ChartPanel";
import { useWorkspace } from "./WorkspaceContext";

export function WorkspacePage() {
  const { logout } = useAuth();
  const { loading, error, clearError } = useWorkspace();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="workspace workspace--tech">
      <header className="workspace-top">
        <div className="brand">
          <span className="brand-mark">IDAS</span>
          <span className="brand-tag">Intelligent Data Analysis System</span>
        </div>
        <button type="button" className="btn-ghost" onClick={handleLogout}>
          退出登录
        </button>
      </header>
      {error && !loading ? (
        <div className="workspace-banner error workspace-banner--top" role="alert">
          <span>{error}</span>
          <button type="button" className="btn-ghost" onClick={clearError}>
            关闭
          </button>
        </div>
      ) : null}
      {loading ? (
        <div className="workspace-loading">正在加载会话…</div>
      ) : (
        <div className="workspace-grid">
          <SessionSidebar />
          <ChatPanel />
          <ChartPanel />
        </div>
      )}
    </div>
  );
}
