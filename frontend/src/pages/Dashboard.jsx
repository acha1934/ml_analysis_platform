import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  FaPlus, FaSearch, FaTrash, FaEllipsisV,
  FaStar, FaRegStar, FaUserCircle, FaSignOutAlt,
  FaFolderOpen, FaUsers, FaShieldAlt, FaCode, FaUser,
} from "react-icons/fa";
import "../styles/dashboard.css";

const API_URL = "http://localhost:8000";

// Role badge config
const ROLE_CONFIG = {
  admin:      { label: "Admin",     color: "#667eea", icon: <FaShieldAlt /> },
  developer:  { label: "Developer", color: "#43cea2", icon: <FaCode />      },
  guest_user: { label: "Guest",     color: "#9e9e9e", icon: <FaUser />      },
};

// What each role can do
const CAN = {
  createProject: ["admin", "developer"],
  deleteProject: ["admin", "developer"],
  uploadData:    ["admin", "developer"],
  runAnalysis:   ["admin", "developer", "guest_user"],
  manageUsers:   ["admin"],
};

function canDo(action, role) {
  return CAN[action]?.includes(role) ?? false;
}

function authHeaders() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function Dashboard() {
  const navigate  = useNavigate();
  const role      = localStorage.getItem("role")     || "guest_user";
  const username  = localStorage.getItem("username") || "User";

  const [search,        setSearch]        = useState("");
  const [activeMenu,    setActiveMenu]    = useState(null);
  const [showUserMenu,  setShowUserMenu]  = useState(false);
  const [projects,      setProjects]      = useState([]);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState(null);
  const [deleteDialog,  setDeleteDialog]  = useState({ show: false, projectId: null, projectName: "" });

  useEffect(() => { fetchProjects(); }, []);

  // ── API ────────────────────────────────────────────────────────────────────
  const fetchProjects = async () => {
    try {
      setLoading(true);
      const res  = await fetch(`${API_URL}/projects`, { headers: authHeaders() });
      if (res.status === 401) { handleLogout(); return; }
      const data = await res.json();

      if (data.projects.length === 0 && canDo("createProject", role)) {
        await createDefaultProject();
      } else {
        setProjects(data.projects);
      }
    } catch (err) {
      setError("Failed to load projects. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const createDefaultProject = async () => {
    const res  = await fetch(`${API_URL}/projects`, {
      method:  "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        name:        "Untitled Project",
        date:        new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
        sourceCount: 0,
        starred:     false,
      }),
    });
    const data = await res.json();
    if (data.success) setProjects([data.project]);
  };

  const handleNewProject = async () => {
    if (!canDo("createProject", role)) return;
    const res  = await fetch(`${API_URL}/projects`, {
      method:  "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        name:        "Untitled Project",
        date:        new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
        sourceCount: 0,
        starred:     false,
      }),
    });
    const data = await res.json();
    if (data.success) setProjects([...projects, data.project]);
  };

  const handleNameChange = async (id, value) => {
    if (!canDo("createProject", role)) return;
    setProjects(projects.map(p => p.id === id ? { ...p, name: value } : p));
    await fetch(`${API_URL}/projects/${id}`, {
      method:  "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body:    JSON.stringify({ name: value }),
    });
  };

  const handleDelete = (id) => {
    if (!canDo("deleteProject", role)) return;
    const project = projects.find(p => p.id === id);
    setDeleteDialog({ show: true, projectId: id, projectName: project.name });
    setActiveMenu(null);
  };

  const confirmDelete = async () => {
    const res  = await fetch(`${API_URL}/projects/${deleteDialog.projectId}`, {
      method:  "DELETE",
      headers: authHeaders(),
    });
    const data = await res.json();
    if (data.success) {
      setProjects(projects.filter(p => p.id !== deleteDialog.projectId));
      setDeleteDialog({ show: false, projectId: null, projectName: "" });
    }
  };

  const handleStar = async (id) => {
    const project      = projects.find(p => p.id === id);
    const newStarred   = !project.starred;
    setProjects(projects.map(p => p.id === id ? { ...p, starred: newStarred } : p));
    await fetch(`${API_URL}/projects/${id}`, {
      method:  "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body:    JSON.stringify({ starred: newStarred }),
    });
  };

  const handleOpen = (project) => navigate(`/project/${project.id}`);

  const handleLogout = () => {
    localStorage.clear();
    navigate("/");
  };

  const roleCfg = ROLE_CONFIG[role] || ROLE_CONFIG.guest_user;
  const filtered = projects.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  // ── Loading / error ────────────────────────────────────────────────────────
  if (loading) return (
    <div className="dashboard-container">
      <div className="loading-message">Loading projects...</div>
    </div>
  );
  if (error) return (
    <div className="dashboard-container">
      <div className="error-message">{error}</div>
      <button onClick={fetchProjects} className="retry-btn">Retry</button>
    </div>
  );

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="dashboard-container">

      {/* Delete dialog */}
      {deleteDialog.show && (
        <div className="dialog-overlay" onClick={() => setDeleteDialog({ show: false })}>
          <div className="dialog-box" onClick={e => e.stopPropagation()}>
            <div className="dialog-header"><h3>Delete project?</h3></div>
            <div className="dialog-body">
              <p>Are you sure you want to delete <strong>"{deleteDialog.projectName}"</strong>?</p>
              <p className="dialog-warning">This action cannot be undone.</p>
            </div>
            <div className="dialog-actions">
              <button className="dialog-btn cancel-btn" onClick={() => setDeleteDialog({ show: false })}>Cancel</button>
              <button className="dialog-btn delete-btn" onClick={confirmDelete}>Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-left">
          <div className="logo">
            <span className="logo-icon">📓</span>
            <span className="logo-text">ML Platform</span>
          </div>
        </div>
        <div className="header-right">
          {/* Role badge */}
          <div className="role-badge" style={{ borderColor: roleCfg.color, color: roleCfg.color }}>
            {roleCfg.icon}&nbsp;{roleCfg.label}
          </div>
          <span className="header-username">{username}</span>

          {/* User menu */}
          <div className="user-menu-container">
            <FaUserCircle className="user-icon" onClick={() => setShowUserMenu(!showUserMenu)} />
            {showUserMenu && (
              <div className="user-dropdown-menu">
                {canDo("manageUsers", role) && (
                  <button onClick={() => navigate("/users")}>
                    <FaUsers /> Manage Users
                  </button>
                )}
                <button onClick={handleLogout}>
                  <FaSignOutAlt /> Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="dashboard-content">
        <div className="top-section">
          <div className="search-container">
            <FaSearch className="search-icon" />
            <input
              className="search-input"
              type="text"
              placeholder="Search projects..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          {canDo("createProject", role) && (
            <button className="new-notebook-btn" onClick={handleNewProject}>
              <FaPlus className="btn-icon" /> New Project
            </button>
          )}
        </div>

        <div className="notebooks-section">
          <h2 className="section-title">Your Projects</h2>

          {filtered.length === 0 && (
            <p style={{ color: "rgba(255,255,255,0.7)", marginTop: 20 }}>
              {role === "admin"
                ? "No projects yet. Click \"New Project\" to get started."
                : "No shared projects yet. Ask your admin to star a project to make it visible here."}
            </p>
          )}

          <div className="notebooks-grid">
            {filtered.map((project, index) => (
              <div
                key={project.id}
                className="notebook-card"
                style={{ "--card-accent": `var(--accent-${index % 6})` }}
                onClick={() => handleOpen(project)}
              >
                <div className="card-accent-bar" />
                <div className="card-header">
                  <div className="card-icon">
                    {["📘","📗","📙","📕","📓","📔"][index % 6]}
                  </div>
                  <div className="card-actions">
                    {canDo("createProject", role) && (
                      <button className="star-btn" onClick={e => { e.stopPropagation(); handleStar(project.id); }}>
                        {project.starred ? <FaStar className="star-filled" /> : <FaRegStar className="star-empty" />}
                      </button>
                    )}
                    <button className="menu-btn" onClick={e => { e.stopPropagation(); setActiveMenu(activeMenu === project.id ? null : project.id); }}>
                      <FaEllipsisV />
                    </button>
                  </div>
                  {activeMenu === project.id && (
                    <div className="dropdown-menu">
                      <button onClick={e => { e.stopPropagation(); handleOpen(project); }}>
                        <FaFolderOpen /> Open
                      </button>
                      {canDo("createProject", role) && (
                        <button onClick={e => { e.stopPropagation(); handleStar(project.id); }}>
                          {project.starred ? <FaStar /> : <FaRegStar />}
                          {project.starred ? "Unstar" : "Star"}
                        </button>
                      )}
                      {canDo("deleteProject", role) && (
                        <button className="delete-option" onClick={e => { e.stopPropagation(); handleDelete(project.id); }}>
                          <FaTrash /> Delete
                        </button>
                      )}
                    </div>
                  )}
                </div>
                <div className="card-body">
                  <input
                    type="text"
                    className="notebook-title"
                    value={project.name}
                    readOnly={!canDo("createProject", role)}
                    onChange={e => { e.stopPropagation(); handleNameChange(project.id, e.target.value); }}
                    onClick={e => e.stopPropagation()}
                  />
                  <div className="card-footer">
                    <span className="meta-badge">{project.sourceCount} sources</span>
                    <span className="meta-date">{project.date}</span>
                    {role !== "admin" && (
                      <span className="shared-badge">⭐ Shared</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
