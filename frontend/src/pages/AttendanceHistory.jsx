import React, { useState, useEffect } from "react";
import { api } from "../api";
import { History, Search, Download, Calendar, Filter } from "lucide-react";

export const AttendanceHistory = () => {
  const [records, setRecords] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [selectedSubjectId, setSelectedSubjectId] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const params = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      if (selectedSubjectId) params.subject_id = selectedSubjectId;
      const data = await api.getAttendanceHistory(params);
      setRecords(data);
    } catch (err) {
      console.error("Failed to load history:", err);
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
    fetchHistory();
  }, [startDate, endDate, selectedSubjectId]);

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
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      subject_id: selectedSubjectId || undefined,
    });
    window.open(url, "_blank");
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2 className="page-title">Attendance History</h2>
          <p className="page-subtitle">Search, audit, and analyze historical attendance sessions</p>
        </div>

        <button className="btn-primary" onClick={handleExportCsv}>
          <Download size={16} />
          <span>Export Filtered CSV</span>
        </button>
      </div>

      <div className="filter-bar" style={{ flexWrap: "wrap" }}>
        <div className="search-input-wrapper">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            placeholder="Search student or code..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="date-filter-group">
          <Calendar size={18} className="text-muted" />
          <input
            type="date"
            className="filter-input-date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            placeholder="Start Date"
          />
          <span className="text-muted">to</span>
          <input
            type="date"
            className="filter-input-date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            placeholder="End Date"
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
        <div className="loading-state">Loading historical records...</div>
      ) : filteredRecords.length === 0 ? (
        <div className="empty-state-card">
          <History size={36} />
          <p>No historical records matching the filter criteria.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Time</th>
                <th>Roll No</th>
                <th>Student Name</th>
                <th>Subject Course</th>
                <th>Confidence</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredRecords.map((rec) => (
                <tr key={rec.id}>
                  <td className="font-mono">{rec.session_date}</td>
                  <td>{rec.session_time}</td>
                  <td className="font-mono text-bold">{rec.student_code}</td>
                  <td className="text-bold">{rec.student_name}</td>
                  <td>
                    <span className="subject-code-pill">{rec.subject_code}</span>{" "}
                    {rec.subject_name}
                  </td>
                  <td>{(rec.confidence * 100).toFixed(0)}%</td>
                  <td>
                    <span className="badge-status-enrolled">{rec.status}</span>
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
