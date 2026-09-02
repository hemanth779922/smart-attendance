import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { Sparkles, Shield, Lock, Mail, AlertCircle, ArrowRight, CheckCircle2 } from "lucide-react";

export const Login = () => {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err.message || "Invalid credentials. Please verify your email and password.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (demoEmail, demoPass) => {
    setEmail(demoEmail);
    setPassword(demoPass);
  };

  return (
    <div className="login-wrapper">
      <div className="login-card">
        <div className="login-header">
          <div className="login-icon-box">
            <Sparkles size={32} className="login-icon" />
          </div>
          <h2 className="login-heading">Smart Attendance</h2>
          <p className="login-subtext">AI Face Recognition & pgvector Powered Platform</p>
        </div>

        {error && (
          <div className="alert-error">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group">
            <label>Email Address</label>
            <div className="input-field-wrapper">
              <Mail size={18} className="input-icon" />
              <input
                type="email"
                placeholder="name@attendance.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="input-group">
            <label>Password</label>
            <div className="input-field-wrapper">
              <Lock size={18} className="input-icon" />
              <input
                type="password"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>

          <button type="submit" className="btn-primary btn-block" disabled={loading}>
            {loading ? "Authenticating..." : "Sign In to System"}
            <ArrowRight size={18} />
          </button>
        </form>

        <div className="demo-accounts">
          <span className="demo-label">Quick Demo Access</span>
          <div className="demo-buttons">
            <button
              type="button"
              className="btn-demo"
              onClick={() => handleQuickLogin("admin@attendance.edu", "Admin@12345")}
            >
              <Shield size={14} />
              <span>Admin Account</span>
            </button>
            <button
              type="button"
              className="btn-demo"
              onClick={() => handleQuickLogin("faculty@attendance.edu", "Faculty@12345")}
            >
              <CheckCircle2 size={14} />
              <span>Faculty Account</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
