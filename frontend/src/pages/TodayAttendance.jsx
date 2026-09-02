import React, { useState, useEffect } from "react";
import { api } from "../api";
import { UserCheck, Search, Download, RefreshCw, Calendar, CheckCircle } from "lucide-react";

export const TodayAttendance = () => {
  const [records, setRecords] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const params = {};
      if (selectedSubjectId) params.subject_id = selectedSubjectId;
      const data = await api.getTodayAttendance(params);
      setRecords(data);
    } catch (err) {
      console.error("Failed to load today's attendance:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const loadSubjects = async () => {
      try {
        const subList = await api.getSubjects();
        setSubjects(subList);
      } catch (e) {
        console.error("Error loading subjects:", e);
      }
    };
    loadSubjects();
  }, []);

  useEffect(() => {
    fetchRecords();
  }, [selectedSubjectId]);

  const filteredRecords = records.filter((r) => {
    if (!search) return true;
    const term = search.toLowerCase();
    return (
      r.student_name?.toLowerCase().includes(term) ||
      r.student_code?.toLowerCase().includes(term) ||
      r.subject_name?.toLowerCase().includes(term)
    );
  });

  const handleExportCsv = () => {
    const url = api.exportAttendanceCsvUrl({
      subject_id: selectedSubjectId || undefined,
    });
    window.open(url, "_blank");
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2 className="page-title">Today's Attendance Logs</h2>
          <p className="page-subtitle">Real-time record of students verified during today's sessions</p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button className="btn-secondary" onClick={fetchRecords} title="Refresh">
            <RefreshCw size={16} />
            <span>Refresh</span>
          </button>
          <button className="btn-primary" onClick={handleExportCsv}>
            <Download size={16} />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      <div className="filter-bar">
        <div className="search-input-wrapper">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            placeholder="Search by student name or roll number..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          className="filter-select"
          value={selectedSubjectId}
          onChange={(e) => setSelectedSubjectId(e.target.value)}
        >
          <option value="">All Subjects</option>
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.code} - {s.name}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="loading-state">Loading today's logs...</div>
      ) : filteredRecords.length === 0 ? (
        <div className="empty-state-card">
          <UserCheck size={36} />
          <p>No attendance records marked yet today for this filter.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Roll No</th>
                <th>Student Name</th>
                <th>Subject Course</th>
                <th>Session Time</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>Method</th>
              </tr>
            </thead>
            <tbody>
              {filteredRecords.map((rec) => (
                <tr key={rec.id}>
                  <td className="font-mono text-bold">{rec.student_code}</td>
                  <td className="text-bold">{rec.student_name}</td>
                  <td>
                    <span className="subject-code-pill">{rec.subject_code}</span>{" "}
                    {rec.subject_name}
                  </td>
                  <td>{rec.session_time}</td>
                  <td>
                    <span className="text-success text-bold">
                      {(rec.confidence * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td>
                    <span className="badge-status-enrolled">
                      <CheckCircle size={14} />
                      <span>{rec.status}</span>
                    </span>
                  </td>
                  <td className="text-muted" style={{ fontSize: "12px" }}>
                    {rec.verification_method}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
