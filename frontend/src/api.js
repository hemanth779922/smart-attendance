const API_BASE_URL = "http://localhost:8000/api/v1";

export const getAuthToken = () => localStorage.getItem("access_token");
export const getRefreshToken = () => localStorage.getItem("refresh_token");

export const setTokens = (accessToken, refreshToken, user) => {
  localStorage.setItem("access_token", accessToken);
  localStorage.setItem("refresh_token", refreshToken);
  localStorage.setItem("user", JSON.stringify(user));
};

export const clearTokens = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
};

export const getStoredUser = () => {
  const user = localStorage.getItem("user");
  return user ? JSON.parse(user) : null;
};

export async function apiRequest(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // If unauthorized, clear tokens
    clearTokens();
    if (!window.location.pathname.includes("/login")) {
      window.location.href = "/login";
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message = errorData.detail || `Request failed with status ${response.status}`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }

  return response.json();
}

export const api = {
  // Auth
  login: (email, password) => apiRequest("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  getMe: () => apiRequest("/auth/me"),
  changePassword: (current_password, new_password) => apiRequest("/auth/change-password", { method: "POST", body: JSON.stringify({ current_password, new_password }) }),

  // Users (Admin)
  getUsers: () => apiRequest("/users"),
  createUser: (data) => apiRequest("/users", { method: "POST", body: JSON.stringify(data) }),
  updateUser: (id, data) => apiRequest(`/users/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteUser: (id) => apiRequest(`/users/${id}`, { method: "DELETE" }),

  // Students
  getStudents: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return apiRequest(`/students${q ? "?" + q : ""}`);
  },
  getStudent: (id) => apiRequest(`/students/${id}`),
  createStudent: (data) => apiRequest("/students", { method: "POST", body: JSON.stringify(data) }),
  updateStudent: (id, data) => apiRequest(`/students/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteStudent: (id) => apiRequest(`/students/${id}`, { method: "DELETE" }),

  // Subjects
  getSubjects: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return apiRequest(`/subjects${q ? "?" + q : ""}`);
  },
  getSubject: (id) => apiRequest(`/subjects/${id}`),
  createSubject: (data) => apiRequest("/subjects", { method: "POST", body: JSON.stringify(data) }),
  updateSubject: (id, data) => apiRequest(`/subjects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  enrollStudents: (subjectId, studentIds) => apiRequest(`/subjects/${subjectId}/enroll`, { method: "POST", body: JSON.stringify({ student_ids: studentIds }) }),
  getSubjectStudents: (subjectId) => apiRequest(`/subjects/${subjectId}/students`),

  // Enrollment
  submitEnrollmentSample: (data) => apiRequest("/enrollment/sample", { method: "POST", body: JSON.stringify(data) }),
  getEnrollmentStatus: (studentId) => apiRequest(`/enrollment/status/${studentId}`),
  resetEnrollment: (studentId) => apiRequest("/enrollment/reset", { method: "POST", body: JSON.stringify({ student_id: studentId }) }),

  // Attendance
  getChallenge: () => apiRequest("/attendance/challenge"),
  markAttendance: (data) => apiRequest("/attendance/mark", { method: "POST", body: JSON.stringify(data) }),
  getTodayAttendance: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return apiRequest(`/attendance/today${q ? "?" + q : ""}`);
  },
  getAttendanceHistory: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return apiRequest(`/attendance/history${q ? "?" + q : ""}`);
  },
  exportAttendanceCsvUrl: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return `${API_BASE_URL}/attendance/export${q ? "?" + q : ""}`;
  },

  // Analytics & Settings
  getOverviewMetrics: () => apiRequest("/analytics/overview"),
  getSubjectStats: () => apiRequest("/analytics/subjects"),
  getAttendanceTrends: (days = 7) => apiRequest(`/analytics/trends?days=${days}`),
  getPipelineLatencies: () => apiRequest("/analytics/pipeline-latency"),
  getSettings: () => apiRequest("/settings"),
  updateSettings: (data) => apiRequest("/settings", { method: "PUT", body: JSON.stringify(data) }),
};
