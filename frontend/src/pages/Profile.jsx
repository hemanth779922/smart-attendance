import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../api";
import { UserCircle, Lock, Shield, CheckCircle, AlertCircle } from "lucide-react";

export const Profile = () => {
  const { user } = useAuth();
  const [currentPass, setCurrentPass] = useState("");
  const [newPass, setNewPass] = useState("");
  const [confirmPass, setConfirmPass] = useState("");
  const [statusMsg, setStatusMsg] = useState({ type: "", text: "" });
  const [submitting, setSubmitting] = useState(false);

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setStatusMsg({ type: "", text: "" });

    if (newPass !== confirmPass) {
      setStatusMsg({ type: "error", text: "New passwords do not match." });
      return;
    }

    setSubmitting(true);
    try {
      await api.changePassword(currentPass, newPass);
      setStatusMsg({ type: "success", text: "Password changed successfully." });
      setCurrentPass("");
      setNewPass("");
      setConfirmPass("");
    } catch (err) {
      setStatusMsg({ type: "error", text: err.message || "Failed to change password." });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2 className="page-title">My User Profile</h2>
          <p className="page-subtitle">Manage your account credentials and security preferences</p>
        </div>
      </div>

      <div className="profile-grid">
        {/* User Card */}
        <div className="card-box">
          <div className="profile-badge-box">
            <div className="profile-avatar-large">
              <UserCircle size={48} />
            </div>
            <h3 className="profile-name">{user?.full_name}</h3>
            <span className="profile-email text-muted">{user?.email}</span>
            <div style={{ marginTop: "12px" }}>
              <span
                className={`user-role-badge ${
                  user?.role === "ADMIN" ? "badge-admin" : "badge-faculty"
                }`}
              >
                <Shield size={14} style={{ marginRight: "4px" }} />
                {user?.role} Privileges
              </span>
            </div>
          </div>
        </div>

        {/* Change Password Card */}
        <div className="card-box">
          <h3 className="card-title">Security & Password</h3>

          {statusMsg.text && (
            <div className={statusMsg.type === "success" ? "alert-success" : "alert-error"} style={{ marginBottom: "16px" }}>
              {statusMsg.type === "success" ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
              <span>{statusMsg.text}</span>
            </div>
          )}

          <form onSubmit={handlePasswordChange} className="login-form">
            <div className="input-group">
              <label>Current Password</label>
              <input
                type="password"
                required
                placeholder="Enter current password"
                value={currentPass}
                onChange={(e) => setCurrentPass(e.target.value)}
              />
            </div>

            <div className="input-group">
              <label>New Password</label>
              <input
                type="password"
                required
                placeholder="Enter new password"
                value={newPass}
                onChange={(e) => setNewPass(e.target.value)}
              />
            </div>

            <div className="input-group">
              <label>Confirm New Password</label>
              <input
                type="password"
                required
                placeholder="Confirm new password"
                value={confirmPass}
                onChange={(e) => setConfirmPass(e.target.value)}
              />
            </div>

            <button type="submit" className="btn-primary" disabled={submitting}>
              <Lock size={16} />
              <span>{submitting ? "Updating..." : "Update Password"}</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
