import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

export function IndexRedirect() {
  const { isAuthenticated } = useAuth();
  return <Navigate to={isAuthenticated ? "/app" : "/login"} replace />;
}
