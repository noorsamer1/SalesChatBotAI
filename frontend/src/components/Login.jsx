import React, { useState, useEffect } from "react";
import "../styles/login.css";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8845/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        setError("Invalid username or password");
        setLoading(false);
        return;
      }
      
      const data = await res.json();
      
      if (data.access_token) {
        onLogin({ username, token: data.access_token });
      } else {
        setError("Login failed: No token received");
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
            <span className="brand-text">FutureTEC</span>
            <br />
            <span className="ai-text">Sales AI</span>
          </h2>
          <div className="login-desc">
            <span className="desc-icon">🚀</span>
            Sign in to unlock the future of sales
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

        <button
          className={`login-btn ${loading ? 'loading' : ''}`}
          type="submit"
          disabled={loading}
        >
          {loading ? (
            <span className="loading-content">
              <span className="loading-spinner"></span>
              Signing In...
            </span>
          ) : (
            <span className="btn-content">
              <span className="btn-icon">🔐</span>
              Sign In
            </span>
          )}
        </button>

        <div className="footer-text">
          Powered by <span className="footer-brand">FutureTEC AI</span>
        </div>
      </form>
    </div>
  );
}