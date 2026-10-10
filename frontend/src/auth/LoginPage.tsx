import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (isAuthenticated) {
    return <Navigate to="/app" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username, password);
      navigate("/app", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page login-page--tech">
      <div className="login-card">
        <h1 className="login-title">NL2SQL</h1>
        <p className="login-sub">智能数据分析 · 后端鉴权</p>
        <form className="login-form" onSubmit={onSubmit}>
          {error ? <p className="login-error">{error}</p> : null}
          <label className="field">
            <span>用户名</span>
            <input
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="演示模式可任意"
            />
          </label>
          <label className="field">
            <span>密码</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="演示模式可任意"
            />
          </label>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "登录中…" : "进入系统"}
          </button>
        </form>
        <p className="login-hint">
          后端 <code>AUTH_DEMO_MODE=true</code> 时任意账号可换取 JWT；关闭后使用环境变量中的固定账号。
        </p>
      </div>
    </div>
  );
}
