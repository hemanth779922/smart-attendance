import React from "react";
import { useAuth } from "../context/AuthContext";
import {
  LayoutDashboard,
  Camera,
  UserCheck,
  History,
  Users,
  UserPlus,
  BookOpen,
  BarChart3,
  UserCog,
  Sliders,
  UserCircle
} from "lucide-react";

export const Sidebar = ({ currentTab, onSelectTab }) => {
  const { user, isAdmin, isFaculty } = useAuth();

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, visible: true },
    { id: "take-attendance", label: "Take Attendance", icon: Camera, visible: isFaculty },
    { id: "today-attendance", label: "Today's Attendance", icon: UserCheck, visible: true },
    { id: "attendance-history", label: "Attendance History", icon: History, visible: true },
    { id: "students", label: "Student Directory", icon: Users, visible: isFaculty },
    { id: "enrollment", label: "Smart Enrollment", icon: UserPlus, visible: isFaculty },
    { id: "subjects", label: "Subjects & Classes", icon: BookOpen, visible: true },
    { id: "analytics", label: "Analytics & Logs", icon: BarChart3, visible: isFaculty },
    { id: "users", label: "User Management", icon: UserCog, visible: isAdmin },
    { id: "settings", label: "AI & Thresholds", icon: Sliders, visible: isAdmin },
    { id: "profile", label: "My Profile", icon: UserCircle, visible: true },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-nav">
        {navItems
          .filter((item) => item.visible)
          .map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                className={`nav-item ${isActive ? "active" : ""}`}
                onClick={() => onSelectTab(item.id)}
              >
                <Icon size={19} className="nav-icon" />
                <span className="nav-label">{item.label}</span>
              </button>
            );
          })}
      </div>

      <div className="sidebar-footer">
        <div className="system-pill">
          <span className="status-dot"></span>
          <span>CV & pgvector Active</span>
        </div>
      </div>
    </aside>
  );
};
