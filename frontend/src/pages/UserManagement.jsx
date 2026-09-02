import React, { useState, useEffect } from "react";
import { api } from "../api";
import { UserCog, Plus, Shield, Trash2, X, AlertCircle } from "lucide-react";

export const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formError, setFormError] = useState("");

  const [formData, setFormData] = useState({
    email: "",
    full_name: "",
    password: "",
    role: "FACULTY",
  });

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const data = await api.getUsers();
      setUsers(data);
    } catch (err) {
      console.error("Failed to load users:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setFormError("");
    try {
      await api.createUser(formData);
      setShowModal(false);
      setFormData({ email: "", full_name: "", password: "", role: "FACULTY" });
      fetchUsers();
    } catch (err) {
      setFormError(err.message || "Failed to create user.");
    }
  };

  const handleDelete = async (id, name) => {
    if (window.confirm(`Delete user "${name}"?`)) {
      try {
        await api.deleteUser(id);
        fetchUsers();
      } catch (err) {
        alert(err.message || "Failed to delete user.");
      }
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2 className="page-title">User Management</h2>
          <p className="page-subtitle">Configure administrative, faculty, and student user access roles</p>
        </div>

        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={18} />
          <span>Add New User</span>
        </button>
      </div>

      {loading ? (
        <div className="loading-state">Loading user directory...</div>
      ) : (
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Full Name</th>
                <th>Email Address</th>
                <th>System Role</th>
                <th>Status</th>
                <th>Created Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="text-bold">{u.full_name}</td>
                  <td className="text-muted">{u.email}</td>
                  <td>
                    <span
                      className={`user-role-badge ${
                        u.role === "ADMIN" ? "badge-admin" : "badge-faculty"
                      }`}
                    >
                      <Shield size={12} style={{ marginRight: "4px" }} />
                      {u.role}
                    </span>
                  </td>
                  <td>
                    <span className="text-success text-bold">Active</span>
                  </td>
                  <td className="text-muted">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td>
                    <button
                      className="btn-table-action btn-delete"
                      onClick={() => handleDelete(u.id, u.full_name)}
                      title="Delete User"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h3>Create User Account</h3>
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

            <form onSubmit={handleCreate} className="modal-form">
              <div className="input-group">
                <label>Full Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Dr. John McCarthy"
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                />
              </div>

              <div className="input-group">
                <label>Email Address *</label>
                <input
                  type="email"
                  required
                  placeholder="name@attendance.edu"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>

              <div className="form-row">
                <div className="input-group">
                  <label>Initial Password *</label>
                  <input
                    type="password"
                    required
                    placeholder="Enter password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  />
                </div>
                <div className="input-group">
                  <label>Role *</label>
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  >
                    <option value="ADMIN">ADMIN</option>
                    <option value="FACULTY">FACULTY</option>
                    <option value="STUDENT">STUDENT</option>
                  </select>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
