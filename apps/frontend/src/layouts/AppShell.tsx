import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/services", label: "Services" },
  { to: "/docker", label: "Docker" },
  { to: "/backups", label: "Backups" },
  { to: "/logs", label: "Logs" },
  { to: "/health", label: "Health" },
  { to: "/users", label: "Users" },
  { to: "/settings", label: "Settings" }
];

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <h1>Homelab CP</h1>
          <p>Operations control plane</p>
        </div>
        <nav>
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className="nav-link"
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="topbar-label">Signed in as</span>
            <strong>{user?.email ?? "unknown"}</strong>
          </div>
          <button className="btn btn-secondary" onClick={onLogout}>
            Logout
          </button>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
