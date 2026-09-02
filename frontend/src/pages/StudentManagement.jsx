import React, { useState, useEffect } from "react";
import { api } from "../api";
import {
  Users,
  Search,
  Plus,
  Trash2,
  Edit2,
  CheckCircle,
  XCircle,
  Camera,
  AlertCircle,
  X
} from "lucide-react";

export const StudentManagement = ({ onEnrollStudent }) => {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // New Student Form state
  const [formData, setFormData] = useState({
    student_code: "",
    name: "",
    email: "",
    department: "Computer Science",
    year: 1,
    section: "A",
  });

  const fetchStudents = async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (deptFilter) params.department = deptFilter;
      const data = await api.getStudents(params);
      setStudents(data);
    } catch (err) {
      console.error("Failed to load students:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, [search, deptFilter]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    setSubmitting(true);
    try {
      await api.createStudent(formData);
      setShowModal(false);
      setFormData({
        student_code: "",
        name: "",
        email: "",
        department: "Computer Science",
        year: 1,
        section: "A",
      });
      fetchStudents();
    } catch (err) {
      setFormError(err.message || "Failed to create student.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id, name) => {
    if (window.confirm(`Are you sure you want to delete student "${name}"? This removes all face embeddings.`)) {
      try {
        await api.deleteStudent(id);
        fetchStudents();
      } catch (err) {
        alert(err.message || "Failed to delete student.");
      }
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2 className="page-title">Student Directory</h2>
          <p className="page-subtitle">Manage student enrollment, profiles, and biometric face records</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={18} />
          <span>Add New Student</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        <div className="search-input-wrapper">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            placeholder="Search by name, roll number, or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          className="filter-select"
          value={deptFilter}
          onChange={(e) => setDeptFilter(e.target.value)}
        >
          <option value="">All Departments</option>
          <option value="Computer Science">Computer Science</option>
          <option value="Electrical Engineering">Electrical Engineering</option>
          <option value="Mechanical Engineering">Mechanical Engineering</option>
          <option value="Information Technology">Information Technology</option>
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <div className="loading-state">Loading students...</div>
      ) : students.length === 0 ? (
        <div className="empty-state-card">
          <Users size={36} />
          <p>No students found. Add a student to begin enrollment.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Roll No / Code</th>
                <th>Full Name</th>
                <th>Email Address</th>
                <th>Department</th>
                <th>Year</th>
                <th>Biometric Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <tr key={s.id}>
                  <td className="font-mono text-bold">{s.student_code}</td>
                  <td className="text-bold">{s.name}</td>
                  <td className="text-muted">{s.email}</td>
                  <td>{s.department}</td>
                  <td>Year {s.year}</td>
                  <td>
                    {s.is_enrolled_face ? (
                      <span className="badge-status-enrolled">
                        <CheckCircle size={14} />
                        <span>Enrolled ({s.embedding_count} poses)</span>
                      </span>
                    ) : (
                      <span className="badge-status-pending">
                        <XCircle size={14} />
                        <span>Not Enrolled</span>
                      </span>
                    )}
                  </td>
                  <td>
                    <div className="table-actions">
                      <button
                        className="btn-table-action btn-enroll"
                        title="Enroll Face Data"
                        onClick={() => onEnrollStudent(s.id)}
                      >
                        <Camera size={16} />
                        <span>{s.is_enrolled_face ? "Re-Enroll" : "Enroll Face"}</span>
                      </button>
                      <button
                        className="btn-table-action btn-delete"
                        title="Delete Student"
                        onClick={() => handleDelete(s.id, s.name)}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Student Modal */}
      {showModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h3>Register New Student</h3>
              <button className="btn-close" onClick={() => setShowModal(false)}>
                <X size={20} />
              </button>
            </div>

            {formError && (
              <div className="alert-error" style={{ margin: "16px 24px 0" }}>
                <AlertCircle size={18} />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="modal-form">
              <div className="form-row">
                <div className="input-group">
                  <label>Student Code / Roll Number *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. CS2026001"
                    value={formData.student_code}
                    onChange={(e) => setFormData({ ...formData, student_code: e.target.value })}
                  />
                </div>
                <div className="input-group">
                  <label>Full Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Jane Doe"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>
              </div>

              <div className="input-group">
                <label>Email Address *</label>
                <input
                  type="email"
                  required
                  placeholder="e.g. jane.doe@attendance.edu"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>

              <div className="form-row">
                <div className="input-group">
                  <label>Department *</label>
                  <select
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                  >
                    <option value="Computer Science">Computer Science</option>
                    <option value="Electrical Engineering">Electrical Engineering</option>
                    <option value="Mechanical Engineering">Mechanical Engineering</option>
                    <option value="Information Technology">Information Technology</option>
                  </select>
                </div>
                <div className="input-group">
                  <label>Year</label>
                  <select
                    value={formData.year}
                    onChange={(e) => setFormData({ ...formData, year: parseInt(e.target.value) })}
                  >
                    <option value={1}>1st Year</option>
                    <option value={2}>2nd Year</option>
                    <option value={3}>3rd Year</option>
                    <option value={4}>4th Year</option>
                  </select>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? "Saving..." : "Create Student"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
