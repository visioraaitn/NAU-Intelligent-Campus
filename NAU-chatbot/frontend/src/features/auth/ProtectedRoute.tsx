import { Navigate, Outlet, useLocation } from "react-router-dom";
import { LoadingScreen } from "../../components/LoadingScreen";
import { useAuth } from "./AuthContext";

export function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "checking") {
    return <LoadingScreen label="Vérification de la session…" />;
  }
  if (status !== "authenticated") {
    return <Navigate to="/admin/connexion" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}
