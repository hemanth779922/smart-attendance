import React from "react";
import { useAuth } from "../context/AuthContext";
import { LogOut, User as UserIcon, Shield, Sparkles } from "lucide-react";

export const Navbar = () => {
  const { user, logout } = useAuth();

  const getRoleBadge = (role) => {
    switch (role) {
      case "ADMIN":
        return "badge-admin";
      case "FACULTY":
        return "badge-faculty";
      default:
        return "badge-student";
    }
  };

  return (
    <header className="navbar">
      <div className="navbar-left">
        <div className="logo-icon">
          <Sparkles className="icon-glow" size={22} />
        </div>
        <div>
          <h1 className="logo-title">SmartAttendance</h1>
          <span className="logo-subtitle">AI & pgvector 2.0</span>
        </div>
      </div>

      <div className="navbar-right">
        {user && (
          <div className="user-profile">
            <div className="user-avatar">
              <UserIcon size={18} />
            </div>
            <div className="user-info">
              <span className="user-name">{user.full_name}</span>
              <span className={`user-role-badge ${getRoleBadge(user.role)}`}>
                <Shield size={12} style={{ marginRight: "4px" }} />
                {user.role}
              </span>
            </div>
            <button className="btn-logout" onClick={logout} title="Sign Out">
              <LogOut size={18} />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
