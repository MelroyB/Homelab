import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./layouts/AppShell";
import { useAuth } from "./hooks/useAuth";
import { BackupsPage } from "./pages/BackupsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DockerManagerPage } from "./pages/DockerManagerPage";
import { HealthPage } from "./pages/HealthPage";
import { LoginPage } from "./pages/LoginPage";
import { LogsPage } from "./pages/LogsPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { ServiceDetailPage } from "./pages/ServiceDetailPage";
import { ServicesPage } from "./pages/ServicesPage";
import { SettingsPage } from "./pages/SettingsPage";
import { UsersPage } from "./pages/UsersPage";

function ProtectedRoutes() {
  const { loading, user, bootstrapRequired } = useAuth();

  if (loading) {
    return <div className="app-loading">Loading...</div>;
  }

  if (bootstrapRequired) {
    return <Navigate to="/onboarding" replace />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <AppShell />;
}

export default function App() {
  const { bootstrapRequired } = useAuth();

  return (
    <Routes>
      <Route path="/onboarding" element={<OnboardingPage />} />
      <Route
        path="/login"
        element={
          bootstrapRequired ? (
            <Navigate to="/onboarding" replace />
          ) : (
            <LoginPage />
          )
        }
      />

      <Route path="/" element={<ProtectedRoutes />}>
        <Route index element={<DashboardPage />} />
        <Route path="services" element={<ServicesPage />} />
        <Route path="services/:slug" element={<ServiceDetailPage />} />
        <Route path="docker" element={<DockerManagerPage />} />
        <Route path="backups" element={<BackupsPage />} />
        <Route path="logs" element={<LogsPage />} />
        <Route path="health" element={<HealthPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="users" element={<UsersPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
