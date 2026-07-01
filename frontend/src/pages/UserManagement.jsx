import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  FaArrowLeft, FaShieldAlt, FaCode, FaUser,
  FaTrash, FaSpinner, FaUsers,
} from "react-icons/fa";
import "../styles/UserManagement.css";

const API_URL = "http://localhost:8000";

const ROLES = [
  { value: "admin",      label: "Admin",     desc: "Full access + user management", icon: <FaShieldAlt />, color: "#667eea" },
  { value: "developer",  label: "Developer", desc: "Create projects + run analysis", icon: <FaCode />,      color: "#43cea2" },
  { value: "guest_user", label: "Guest",     desc: "View and run analysis only",     icon: <FaUser />,      color: "#9e9e9e" },
];

function authHeaders() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function UserManagement() {
  const navigate  = useNavigate();
  const role      = localStorage.getItem("role");
  const myId      = localStorage.getItem("userId");

  const [users,      setUsers]      = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [updating,   setUpdating]   = useState(null);  // user id being updated
  const [deleteDialog, setDeleteDialog] = useState({ show: false, userId: null, username: "" });

  // Redirect non-admins
  useEffect(() => {
    if (role !== "admin") { navigate("/dashboard"); return; }
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const res  = await fetch(`${API_URL}/users`, { headers: authHeaders() });
      const data = await res.json();
      setUsers(data.users || []);
    } catch (err) {
      console.error("Failed to fetch users:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    setUpdating(userId);
    try {
      await fetch(`${API_URL}/users/${userId}/role`, {
        method:  "PUT",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body:    JSON.stringify({ role: newRole }),
      });
      setUsers(users.map(u => u.id === userId ? { ...u, role: newRole } : u));
    } catch (err) {
      console.error("Failed to update role:", err);
    } finally {
      setUpdating(null);
    }
  };

  const confirmDelete = async () => {
    try {
      await fetch(`${API_URL}/users/${deleteDialog.userId}`, {
        method:  "DELETE",
        headers: authHeaders(),
      });
      setUsers(users.filter(u => u.id !== deleteDialog.userId));
      setDeleteDialog({ show: false, userId: null, username: "" });
    } catch (err) {
      console.error("Failed to delete user:", err);
    }
  };

  const getRoleCfg = (r) => ROLES.find(x => x.value === r) || ROLES[2];

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="um-page">

      {/* Delete dialog */}
      {deleteDialog.show && (
        <div className="dialog-overlay" onClick={() => setDeleteDialog({ show: false })}>
          <div className="dialog-box" onClick={e => e.stopPropagation()}>
            <div className="dialog-header"><h3>Delete user?</h3></div>
            <div className="dialog-body">
              <p>Permanently delete <strong>"{deleteDialog.username}"</strong>?</p>
              <p className="dialog-warning">This cannot be undone.</p>
            </div>
            <div className="dialog-actions">
              <button className="dialog-btn cancel-btn" onClick={() => setDeleteDialog({ show: false })}>Cancel</button>
              <button className="dialog-btn delete-btn" onClick={confirmDelete}>Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="um-header">
        <button className="back-btn" onClick={() => navigate("/dashboard")}>
          <FaArrowLeft /> Back
        </button>
        <div className="um-title">
          <FaUsers /> User Management
        </div>
        <div className="um-count">{users.length} user{users.length !== 1 ? "s" : ""}</div>
      </header>

      {/* Role legend */}
      <div className="um-legend">
        {ROLES.map(r => (
          <div className="legend-item" key={r.value}>
            <span className="legend-icon" style={{ color: r.color }}>{r.icon}</span>
            <div>
              <span className="legend-label">{r.label}</span>
              <span className="legend-desc">{r.desc}</span>
            </div>
          </div>
        ))}
      </div>

      {/* User table */}
      <div className="um-content">
        {loading ? (
          <div className="um-loading"><FaSpinner className="spin" /> Loading users...</div>
        ) : (
          <div className="um-table-wrap">
            <table className="um-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Joined</th>
                  <th>Current Role</th>
                  <th>Change Role</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => {
                  const cfg    = getRoleCfg(u.role);
                  const isMe   = u.id === myId;
                  const isBusy = updating === u.id;
                  return (
                    <tr key={u.id} className={isMe ? "um-row-me" : ""}>
                      <td>
                        <span className="um-username">
                          {u.username}
                          {isMe && <span className="um-you-badge">you</span>}
                        </span>
                      </td>
                      <td className="um-email">{u.email}</td>
                      <td className="um-date">
                        {u.createdAt ? new Date(u.createdAt).toLocaleDateString() : "—"}
                      </td>
                      <td>
                        <span className="um-role-badge" style={{ background: `${cfg.color}20`, color: cfg.color, borderColor: cfg.color }}>
                          {cfg.icon}&nbsp;{cfg.label}
                        </span>
                      </td>
                      <td>
                        <div className="role-selector">
                          {ROLES.map(r => (
                            <button
                              key={r.value}
                              className={`role-opt ${u.role === r.value ? "active" : ""}`}
                              style={u.role === r.value ? { background: `${r.color}20`, color: r.color, borderColor: r.color } : {}}
                              onClick={() => !isMe && handleRoleChange(u.id, r.value)}
                              disabled={isMe || isBusy}
                              title={isMe ? "Cannot change your own role" : `Set to ${r.label}`}
                            >
                              {isBusy && u.role !== r.value ? <FaSpinner className="spin" style={{ fontSize: 10 }} /> : r.icon}
                              &nbsp;{r.label}
                            </button>
                          ))}
                        </div>
                      </td>
                      <td>
                        <button
                          className="um-delete-btn"
                          onClick={() => setDeleteDialog({ show: true, userId: u.id, username: u.username })}
                          disabled={isMe}
                          title={isMe ? "Cannot delete yourself" : "Delete user"}
                        >
                          <FaTrash />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default UserManagement;
