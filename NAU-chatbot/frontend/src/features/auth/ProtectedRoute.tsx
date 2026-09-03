import { Navigate, Outlet, useLocation } from "react-router-dom";
import { LoadingScreen } from "../../components/LoadingScreen";
import { useAuth } from "./AuthContext";
import type { UserRole } from "../../types/auth";

export function ProtectedRoute({ roles }: { roles: UserRole[] }) {
  const { status, user } = useAuth();
  const location = useLocation();

  if (status === "checking") {
    return <LoadingScreen label="Vérification de la session…" />;
  }
  if (status !== "authenticated") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (!user || !roles.includes(user.role)) {
    return <Navigate to={user?.role === "ADMIN" ? "/admin" : "/chat"} replace />;
  }
  return <Outlet />;
}
