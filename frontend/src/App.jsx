import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login          from "./pages/login";
import Dashboard      from "./pages/Dashboard";
import UserManagement from "./pages/UserManagement";
import ProjectPage    from "./pages/ProjectPage";

// ── Auth guard ────────────────────────────────────────────────────────────────
function Protected({ children, requiredRole }) {
  const token = localStorage.getItem("token");
  const role  = localStorage.getItem("role");

  if (!token) return <Navigate to="/" replace />;
  if (requiredRole && role !== requiredRole) return <Navigate to="/dashboard" replace />;
  return children;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>

        <Route path="/" element={<Login />} />

        <Route
          path="/dashboard"
          element={
            <Protected>
              <Dashboard />
            </Protected>
          }
        />

        <Route
          path="/users"
          element={
            <Protected requiredRole="admin">
              <UserManagement />
            </Protected>
          }
        />

        <Route
          path="/project/:id"
          element={
            <Protected>
              <ProjectPage />
            </Protected>
          }
        />

        {/* Catch-all → login */}
        <Route path="*" element={<Navigate to="/" replace />} />

      </Routes>
    </BrowserRouter>
  );
}

export default App;
