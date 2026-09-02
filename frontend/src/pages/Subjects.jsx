import React, { useState, useEffect } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import { BookOpen, Plus, Users, UserPlus, X, Check, AlertCircle } from "lucide-react";

export const Subjects = () => {
  const { isAdmin } = useAuth();
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEnrollModal, setShowEnrollModal] = useState(false);
  const [activeSubject, setActiveSubject] = useState(null);

  // Add Subject Form
  const [formData, setFormData] = useState({
    code: "",
    name: "",
    department: "Computer Science",
    semester: 1,
  });

  // Enroll Students state
  const [allStudents, setAllStudents] = useState([]);
  const [enrolledStudentIds, setEnrolledStudentIds] = useState([]);
  const [selectedStudentIds, setSelectedStudentIds] = useState([]);
  const [savingEnrollment, setSavingEnrollment] = useState(false);

  const fetchSubjects = async () => {
    setLoading(true);
    try {
      const list = await api.getSubjects();
      setSubjects(list);
    } catch (err) {
      console.error("Failed to load subjects:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubjects();
  }, []);

  const handleCreateSubject = async (e) => {
    e.preventDefault();
    try {
      await api.createSubject(formData);
      setShowAddModal(false);
      setFormData({ code: "", name: "", department: "Computer Science", semester: 1 });
      fetchSubjects();
    } catch (err) {
      alert(err.message || "Failed to create subject.");
    }
  };

  const openEnrollModal = async (subject) => {
    setActiveSubject(subject);
    try {
      const [studentsList, enrolledList] = await Promise.all([
        api.getStudents(),
        api.getSubjectStudents(subject.id),
      ]);
      setAllStudents(studentsList);
      const enrolledIds = enrolledList.map((s) => s.id);
      setEnrolledStudentIds(enrolledIds);
      setSelectedStudentIds(enrolledIds);
      setShowEnrollModal(true);
    } catch (err) {
      alert("Failed to load subject enrollment: " + err.message);
    }
  };

  const toggleStudentSelection = (studentId) => {
    setSelectedStudentIds((prev) =>
      prev.includes(studentId) ? prev.filter((id) => id !== studentId) : [...prev, studentId]
    );
  };

  const handleSaveEnrollment = async () => {
    if (!activeSubject) return;
    setSavingEnrollment(true);
    try {
      await api.enrollStudents(activeSubject.id, selectedStudentIds);
      setShowEnrollModal(false);
      fetchSubjects();
    } catch (err) {
      alert("Failed to save enrollment: " + err.message);
    } finally {
      setSavingEnrollment(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2 className="page-title">Subjects & Academic Classes</h2>
          <p className="page-subtitle">Configure courses, assign faculty instructors, and enroll students</p>
        </div>

        {isAdmin && (
          <button className="btn-primary" onClick={() => setShowAddModal(true)}>
            <Plus size={18} />
            <span>Create New Subject</span>
          </button>
        )}
      </div>

      {loading ? (
        <div className="loading-state">Loading subjects...</div>
      ) : subjects.length === 0 ? (
        <div className="empty-state-card">
          <BookOpen size={36} />
          <p>No subjects registered yet. Create your first course to begin taking attendance.</p>
        </div>
      ) : (
        <div className="subjects-grid">
          {subjects.map((s) => (
            <div key={s.id} className="subject-card">
              <div className="subject-card-top">
                <span className="subject-code-pill">{s.code}</span>
                <span className="text-muted" style={{ fontSize: "13px" }}>
                  Sem {s.semester}
                </span>
              </div>
              <h3 className="subject-card-title">{s.name}</h3>
              <p className="subject-card-dept">{s.department}</p>

              <div className="subject-card-stats">
                <div className="stat-item">
                  <Users size={16} />
                  <span>{s.enrolled_student_count} Enrolled Students</span>
                </div>
              </div>

              <div className="subject-card-actions">
                <button
                  className="btn-secondary btn-block"
                  onClick={() => openEnrollModal(s)}
                >
                  <UserPlus size={16} />
                  <span>Manage Enrolled Students</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Subject Modal */}
      {showAddModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h3>Add New Subject Course</h3>
              <button className="btn-close" onClick={() => setShowAddModal(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleCreateSubject} className="modal-form">
              <div className="input-group">
                <label>Course Code *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. CS401"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                />
              </div>

              <div className="input-group">
                <label>Subject Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Deep Learning & Neural Networks"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
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
                    <option value="Information Technology">Information Technology</option>
                  </select>
                </div>
                <div className="input-group">
                  <label>Semester</label>
                  <input
                    type="number"
                    min={1}
                    max={8}
                    value={formData.semester}
                    onChange={(e) => setFormData({ ...formData, semester: parseInt(e.target.value) })}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowAddModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create Subject
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Enroll Students Modal */}
      {showEnrollModal && activeSubject && (
        <div className="modal-backdrop">
          <div className="modal-dialog modal-large">
            <div className="modal-header">
              <h3>Enroll Students into {activeSubject.name} ({activeSubject.code})</h3>
              <button className="btn-close" onClick={() => setShowEnrollModal(false)}>
                <X size={20} />
              </button>
            </div>

            <div className="modal-body">
              <p className="text-muted" style={{ marginBottom: "16px" }}>
                Select the students enrolled in this course to permit automated attendance logging:
              </p>

              <div className="students-checklist">
                {allStudents.map((st) => {
                  const isChecked = selectedStudentIds.includes(st.id);
                  return (
                    <div
                      key={st.id}
                      className={`checklist-item ${isChecked ? "checked" : ""}`}
                      onClick={() => toggleStudentSelection(st.id)}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => {}}
                      />
                      <div className="checklist-info">
                        <span className="checklist-name">{st.name}</span>
                        <span className="font-mono text-muted">{st.student_code} ({st.department})</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="modal-footer">
              <span className="text-muted" style={{ marginRight: "auto" }}>
                {selectedStudentIds.length} students selected
              </span>
              <button type="button" className="btn-secondary" onClick={() => setShowEnrollModal(false)}>
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={handleSaveEnrollment}
                disabled={savingEnrollment}
              >
                {savingEnrollment ? "Saving..." : "Save Enrollment"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
