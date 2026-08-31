import { Route, Routes } from "react-router-dom";
import { entityConfigList } from "./features/admin/entityConfig";
import { CrudPage } from "./features/admin/CrudPage";
import { ProtectedRoute } from "./features/auth/ProtectedRoute";
import { AdminLayout } from "./layouts/AdminLayout";
import { PublicLayout } from "./layouts/PublicLayout";
import { AdminDashboardPage } from "./pages/AdminDashboardPage";
import { AcademicOverviewPage } from "./pages/AcademicOverviewPage";
import { ChatPage } from "./pages/ChatPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { OrientationMatrixPage } from "./pages/OrientationMatrixPage";
import { RagStatusPage } from "./pages/RagStatusPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<PublicLayout />}>
        <Route index element={<ChatPage />} />
      </Route>
      <Route path="/admin/connexion" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboardPage />} />
          <Route path="academic-overview" element={<AcademicOverviewPage />} />
          <Route path="orientation-matrix" element={<OrientationMatrixPage />} />
          {entityConfigList.map((config) => (
            <Route
              key={config.resource}
              path={config.resource}
              element={<CrudPage key={config.resource} config={config} />}
            />
          ))}
          <Route path="rag" element={<RagStatusPage />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
