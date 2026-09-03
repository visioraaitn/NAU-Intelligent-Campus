import { Route, Routes } from "react-router-dom";
import { entityConfigList } from "./features/admin/entityConfig";
import { CrudPage } from "./features/admin/CrudPage";
import { ProtectedRoute } from "./features/auth/ProtectedRoute";
import { AdminLayout } from "./layouts/AdminLayout";
import { PublicLayout } from "./layouts/PublicLayout";
import { AdminDashboardPage } from "./pages/AdminDashboardPage";
import { AcademicOverviewPage } from "./pages/AcademicOverviewPage";
import { AdmissionHubPage } from "./pages/AdmissionHubPage";
import { ChatPage } from "./pages/ChatPage";
import { CycleCataloguePage } from "./pages/CycleCataloguePage";
import { CycleWorkspacePage } from "./pages/CycleWorkspacePage";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { Navigate } from "react-router-dom";
import { NotFoundPage } from "./pages/NotFoundPage";
import { OrientationMatrixPage } from "./pages/OrientationMatrixPage";
import { RagStatusPage } from "./pages/RagStatusPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<PublicLayout />}>
        <Route index element={<Navigate to="/login" replace />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="signup" element={<SignupPage />} />
      </Route>
      <Route path="/admin/connexion" element={<LoginPage />} />
      <Route element={<ProtectedRoute roles={["USER", "ADMIN"]} />}>
        <Route path="/chat" element={<PublicLayout />}>
          <Route index element={<ChatPage />} />
          <Route path=":conversationId" element={<ChatPage />} />
        </Route>
      </Route>
      <Route element={<ProtectedRoute roles={["ADMIN"]} />}>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboardPage />} />
          <Route path="catalogue" element={<CycleCataloguePage />} />
          <Route path="cycle-workspace" element={<CycleWorkspacePage />} />
          <Route path="admission" element={<AdmissionHubPage />} />
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
