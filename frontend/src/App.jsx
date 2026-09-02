import React, { useState } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Navbar } from "./components/Navbar";
import { Sidebar } from "./components/Sidebar";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { StudentManagement } from "./pages/StudentManagement";
import { StudentEnrollment } from "./pages/StudentEnrollment";
import { TakeAttendance } from "./pages/TakeAttendance";
import { TodayAttendance } from "./pages/TodayAttendance";
import { AttendanceHistory } from "./pages/AttendanceHistory";
import { Subjects } from "./pages/Subjects";
import { Analytics } from "./pages/Analytics";
import { UserManagement } from "./pages/UserManagement";
import { SettingsPage } from "./pages/SettingsPage";
import { Profile } from "./pages/Profile";

const AppContent = () => {
  const { isAuthenticated, loading } = useAuth();
  const [currentTab, setCurrentTab] = useState("dashboard");
  const [enrollStudentId, setEnrollStudentId] = useState(null);

  if (loading) {
    return (
      <div className="app-loader">
        <div className="loader-spinner"></div>
        <p>Loading Smart Attendance System...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  const renderContent = () => {
    switch (currentTab) {
      case "dashboard":
        return <Dashboard onNavigate={setCurrentTab} />;
      case "take-attendance":
        return <TakeAttendance />;
      case "today-attendance":
        return <TodayAttendance />;
      case "attendance-history":
        return <AttendanceHistory />;
      case "students":
        return (
          <StudentManagement
            onEnrollStudent={(studentId) => {
              setEnrollStudentId(studentId);
              setCurrentTab("enrollment");
            }}
          />
        );
      case "enrollment":
        return (
          <StudentEnrollment
            initialStudentId={enrollStudentId}
            onBack={() => setCurrentTab("students")}
          />
        );
      case "subjects":
        return <Subjects />;
      case "analytics":
        return <Analytics />;
      case "users":
        return <UserManagement />;
      case "settings":
        return <SettingsPage />;
      case "profile":
        return <Profile />;
      default:
        return <Dashboard onNavigate={setCurrentTab} />;
    }
  };

  return (
    <div className="app-layout">
      <Navbar />
      <div className="app-body">
        <Sidebar currentTab={currentTab} onSelectTab={setCurrentTab} />
        <main className="main-content">{renderContent()}</main>
      </div>
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
