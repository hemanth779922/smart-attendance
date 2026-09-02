import React, { useState, useEffect } from "react";
import { api } from "../api";
import {
  Users,
  UserCheck,
  BookOpen,
  Camera,
  ShieldCheck,
  SunMedium,
  TrendingUp,
  ArrowUpRight,
  AlertTriangle,
  Clock,
  Sparkles
} from "lucide-react";

export const Dashboard = ({ onNavigate }) => {
  const [metrics, setMetrics] = useState(null);
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [overviewData, subjectStats] = await Promise.all([
          api.getOverviewMetrics().catch(() => null),
          api.getSubjectStats().catch(() => []),
        ]);
        setMetrics(overviewData);
        setSubjects(subjectStats);
      } catch (err) {
        console.error("Failed to load dashboard:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboardData();
  }, []);

  if (loading) {
    return <div className="loading-state">Loading dashboard analytics...</div>;
  }

  return (
    <div className="dashboard-container">
      {/* Welcome Banner */}
      <div className="welcome-banner">
        <div>
          <h2 className="banner-title">Smart Attendance System 2.0</h2>
          <p className="banner-subtext">
            Enterprise Face Recognition with Low-Light CLAHE Enhancement, Multi-Signal Anti-Spoofing & pgvector Similarity Search.
          </p>
        </div>
        <div className="banner-actions">
          <button className="btn-action-primary" onClick={() => onNavigate("take-attendance")}>
            <Camera size={18} />
            <span>Launch Attendance Kiosk</span>
          </button>
          <button className="btn-action-secondary" onClick={() => onNavigate("enrollment")}>
            <Users size={18} />
            <span>Enroll Student</span>
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Total Students</span>
            <div className="metric-icon-box bg-blue">
              <Users size={20} />
            </div>
          </div>
          <div className="metric-value">{metrics?.total_students ?? 0}</div>
          <div className="metric-footer">
            <span className="text-highlight">{metrics?.enrolled_students ?? 0} enrolled with face data</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Today's Attendance</span>
            <div className="metric-icon-box bg-green">
              <UserCheck size={20} />
            </div>
          </div>
          <div className="metric-value">{metrics?.today_attendance_count ?? 0}</div>
          <div className="metric-footer">
            <span className="text-success">{metrics?.overall_attendance_rate ?? 0}% overall rate</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Spoofs Blocked</span>
            <div className="metric-icon-box bg-purple">
              <ShieldCheck size={20} />
            </div>
          </div>
          <div className="metric-value">{metrics?.spoof_rejection_count ?? 0}</div>
          <div className="metric-footer">
            <span className="text-purple">LBP & Frequency checks</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Active Subjects</span>
            <div className="metric-icon-box bg-amber">
              <BookOpen size={20} />
            </div>
          </div>
          <div className="metric-value">{metrics?.total_subjects ?? 0}</div>
          <div className="metric-footer">
            <span className="text-muted">Managed curriculum</span>
          </div>
        </div>
      </div>

      {/* Subject Attendance Breakdown */}
      <div className="dashboard-section">
        <div className="section-header">
          <div>
            <h3 className="section-title">Today's Subject Attendance</h3>
            <p className="section-subtitle">Real-time attendance rates per course session</p>
          </div>
          <button className="btn-link" onClick={() => onNavigate("today-attendance")}>
            <span>View Full Log</span>
            <ArrowUpRight size={16} />
          </button>
        </div>

        {subjects.length === 0 ? (
          <div className="empty-state-card">
            <Clock size={32} />
            <p>No active subjects registered yet.</p>
          </div>
        ) : (
          <div className="subjects-grid">
            {subjects.map((s) => (
              <div key={s.subject_id} className="subject-stat-card">
                <div className="subject-stat-header">
                  <div>
                    <span className="subject-code-pill">{s.subject_code}</span>
                    <h4 className="subject-stat-name">{s.subject_name}</h4>
                  </div>
                  <span className="subject-pct-badge">{s.attendance_percentage}%</span>
                </div>

                <div className="progress-bar-bg">
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${Math.min(100, s.attendance_percentage)}%` }}
                  ></div>
                </div>

                <div className="subject-stat-footer">
                  <span>Present: {s.present_today} / {s.total_enrolled} enrolled</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* AI Pipeline Architecture Status */}
      <div className="ai-status-card">
        <div className="ai-status-header">
          <Sparkles className="icon-ai-glow" size={22} />
          <div>
            <h4>AI / Computer Vision Verification Engine Status</h4>
            <p>Pipeline: Quality Check → Low-Light Enhancement → YuNet Face Detection → Anti-Spoofing Challenge → SFace Embedding → pgvector Similarity</p>
          </div>
        </div>
        <div className="ai-pipeline-tags">
          <span className="ai-tag tag-active">✓ Low-Light CLAHE Adaptive</span>
          <span className="ai-tag tag-active">✓ LBP Micro-Texture Analysis</span>
          <span className="ai-tag tag-active">✓ FFT Frequency Moiré Check</span>
          <span className="ai-tag tag-active">✓ Randomized Challenge-Response</span>
          <span className="ai-tag tag-active">✓ SFace 128-d L2 Vector</span>
          <span className="ai-tag tag-active">✓ Database-Level Unique Constraint</span>
        </div>
      </div>
    </div>
  );
};
