import React, { useState, useEffect } from "react";
import "../styles/login.css";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Clear messages when switching modes
  useEffect(() => {
    setError("");
    setSuccess("");
  }, [isRegisterMode]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    const endpoint = isRegisterMode ? "/auth/register" : "/auth/login";
    const requestBody = isRegisterMode 
      ? { username, password, email }
      : { username, password };

    try {
      const res = await fetch(`http://localhost:8845${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || (isRegisterMode ? "Registration failed" : "Invalid username or password"));
        setLoading(false);
        return;
      }
      
      if (isRegisterMode) {
        setSuccess("Registration successful! You can now login.");
        setIsRegisterMode(false);
        setUsername("");
        setPassword("");
        setEmail("");
      } else {
        if (data.access_token) {
          onLogin({ username, token: data.access_token });
        } else {
          setError("Login failed: No token received");
        }
      }

    } catch (err) {
      setError("Network error. Please try again.");
    }
    setLoading(false);
  }

  return (
    <div className="login-outer">
      <form 
        className={`login-form ${mounted ? 'mounted' : ''}`} 
        onSubmit={handleSubmit} 
        autoComplete="off"
      >
        <div className="logo-container">
          <img
            src="/futuretec-logo.png"
            alt="FutureTEC"
            className="logo"
          />
        </div>
        
        <div className="title-container">
          <h2>
            <span className="welcome-text">Welcome to</span>
            <br />
            <span className="brand-text">FutureTec</span>
            <br />
            <span className="ai-text">Sales AI</span>
          </h2>
          <div className="login-desc">
            <span className="desc-icon">🤖</span>
            {isRegisterMode ? "Join the future of sales analytics" : "Sign in to unlock the future of sales"}
          </div>
        </div>

        <div className="input-container">
          <div className="input-wrapper">
            <input
              className="login-input"
              type="text"
              placeholder="Username"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            <div className="input-focus-line"></div>
          </div>
          
          {isRegisterMode && (
            <div className="input-wrapper">
              <input
                className="login-input"
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <div className="input-focus-line"></div>
            </div>
          )}
          
          <div className="input-wrapper">
            <input
              className="login-input"
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <div className="input-focus-line"></div>
          </div>
        </div>

        {error && (
          <div className="login-error">
            <span className="error-icon">⚠️</span>
            {error}
          </div>
        )}

        {success && (
          <div className="login-success">
            <span className="success-icon">✅</span>
            {success}
          </div>
        )}

        <button
          className={`login-btn ${loading ? 'loading' : ''}`}
          type="submit"
          disabled={loading}
        >
          {loading ? (
            <div className="login-spinner">
              <div className="spinner"></div>
              <span>{isRegisterMode ? "Creating Account..." : "Signing In..."}</span>
            </div>
          ) : (
            <>
              <span className="btn-icon">{isRegisterMode ? "👥" : "🔐"}</span>
              {isRegisterMode ? "Create Account" : "Sign In"}
            </>
          )}
        </button>

        <div className="mode-toggle">
          <button
            type="button"
            className="toggle-btn"
            onClick={() => setIsRegisterMode(!isRegisterMode)}
          >
            {isRegisterMode 
              ? "Already have an account? Sign in" 
              : "Don't have an account? Register"}
          </button>
        </div>

        <div className="footer-text">
          Powered by <span className="footer-brand">Joud AI</span>
        </div>
      </form>
    </div>
  );
}