import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { IndexRedirect } from "./auth/IndexRedirect";
import { LoginPage } from "./auth/LoginPage";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { WorkspaceProvider } from "./workspace/WorkspaceContext";
import { WorkspacePage } from "./workspace/WorkspacePage";

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <WorkspaceProvider>
                  <WorkspacePage />
                </WorkspaceProvider>
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<IndexRedirect />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
