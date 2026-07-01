import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FaUserCircle, FaLock, FaEye, FaEyeSlash,
  FaUser, FaEnvelope, FaSignInAlt, FaUserPlus,
} from "react-icons/fa";
import "../styles/Login.css";

const API_URL = "http://localhost:8000";

function Login() {
  const navigate = useNavigate();

  const [mode,         setMode]         = useState("login");   // "login" | "register"
  const [username,     setUsername]     = useState("");
  const [email,        setEmail]        = useState("");
  const [password,     setPassword]     = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error,        setError]        = useState("");
  const [loading,      setLoading]      = useState(false);
  const [shake,        setShake]        = useState(false);

  const triggerShake = () => {
    setShake(true);
    setTimeout(() => setShake(false), 400);
  };

  const handleSubmit = async () => {
    setError("");
    if (!username.trim() || !password.trim()) {
      setError("Username and password are required.");
      triggerShake();
      return;
    }
    if (mode === "register" && !email.trim()) {
      setError("Email is required for registration.");
      triggerShake();
      return;
    }

    setLoading(true);
    try {
      const endpoint = mode === "login" ? "/login" : "/register";
      const body     = mode === "login"
        ? { username, password }
        : { username, email, password, role: "guest_user" };

      const res  = await fetch(`${API_URL}${endpoint}`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(body),
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Something went wrong.");
        triggerShake();
        return;
      }

      // Store auth data
      localStorage.setItem("token",    data.token);
      localStorage.setItem("username", data.username);
      localStorage.setItem("role",     data.role);
      // Decode userId from token payload
      try {
        const payload = JSON.parse(atob(data.token.split(".")[1]));
        localStorage.setItem("userId", payload.sub);
      } catch (_) {}

      navigate("/dashboard");
    } catch (err) {
      setError("Could not connect to server. Is the backend running?");
      triggerShake();
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleSubmit();
  };

  return (
    <div className="login-container">
      <div className={`login-card ${shake ? "shake" : ""}`}>

        {/* Avatar */}
        <div className="avatar">
          <FaUserCircle />
        </div>

        {/* Title */}
        <h1 className="login-title">
          {mode === "login" ? "Welcome Back" : "Create Account"}
        </h1>
        <p className="login-subtitle">
          {mode === "login"
            ? "Sign in to access your projects"
            : "Register to get started"}
        </p>

        {/* Username */}
        <div className="input-box">
          <FaUser className="lock-icon" />
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => { setUsername(e.target.value); setError(""); }}
            onKeyDown={handleKeyDown}
          />
        </div>

        {/* Email — register only */}
        {mode === "register" && (
          <div className="input-box">
            <FaEnvelope className="lock-icon" />
            <input
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setError(""); }}
              onKeyDown={handleKeyDown}
            />
          </div>
        )}

        {/* Password */}
        <div className="input-box">
          <FaLock className="lock-icon" />
          <input
            type={showPassword ? "text" : "password"}
            placeholder="Password"
            value={password}
            onChange={(e) => { setPassword(e.target.value); setError(""); }}
            onKeyDown={handleKeyDown}
          />
          <button
            type="button"
            className="eye-btn"
            onClick={() => setShowPassword(!showPassword)}
          >
            {showPassword ? <FaEyeSlash /> : <FaEye />}
          </button>
        </div>

        {/* Error */}
        {error && <p className="error-msg">⚠ {error}</p>}

        {/* Submit */}
        <button
          className="admin-btn"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? (
            "Please wait..."
          ) : mode === "login" ? (
            <><FaSignInAlt /> Sign In</>
          ) : (
            <><FaUserPlus /> Register</>
          )}
        </button>

        {/* Switch mode */}
        <div className="divider">
          <span className="divider-line" />
          <span className="divider-text">
            {mode === "login" ? "No account?" : "Already registered?"}
          </span>
          <span className="divider-line" />
        </div>

        <button
          className="user-btn"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError("");
          }}
        >
          {mode === "login" ? (
            <><FaUserPlus /> Create Account</>
          ) : (
            <><FaSignInAlt /> Sign In</>
          )}
        </button>

      </div>
    </div>
  );
}

export default Login;
