# API Documentation

Interactive Swagger documentation is available at `http://localhost:8000/docs`.

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Bearer token authorization header:
```http
Authorization: Bearer <access_token>
```

---

## Endpoints

### 1. Authentication (`/auth`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/login` | Public | Authenticate with email and password to receive JWT tokens. |
| `POST` | `/auth/refresh` | Public | Refresh expired access token with refresh token. |
| `GET` | `/auth/me` | Authenticated | Retrieve profile and role of currently logged in user. |
| `POST` | `/auth/change-password` | Authenticated | Update user password. |

### 2. User Management (`/users`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/users` | `ADMIN` | List all system users. |
| `POST` | `/users` | `ADMIN` | Create new admin, faculty, or student user. |
| `GET` | `/users/{id}` | `ADMIN` | Retrieve user details by ID. |
| `PUT` | `/users/{id}` | `ADMIN` | Update user details or role. |
| `DELETE` | `/users/{id}` | `ADMIN` | Delete user account. |

### 3. Student Management (`/students`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/students` | `FACULTY`, `ADMIN` | Search and filter student directory. |
| `POST` | `/students` | `FACULTY`, `ADMIN` | Register new student profile. |
| `GET` | `/students/{id}` | `FACULTY`, `ADMIN` | Retrieve student details with enrollment status. |
| `PUT` | `/students/{id}` | `FACULTY`, `ADMIN` | Update student profile. |
| `DELETE` | `/students/{id}` | `ADMIN` | Delete student and all associated face embeddings. |

### 4. Subjects & Classes (`/subjects`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/subjects` | Authenticated | List all active academic subjects. |
| `POST` | `/subjects` | `ADMIN` | Create new subject course. |
| `GET` | `/subjects/{id}` | Authenticated | Retrieve subject course details. |
| `POST` | `/subjects/{id}/enroll` | `FACULTY`, `ADMIN` | Enroll list of students into subject course. |
| `GET` | `/subjects/{id}/students` | Authenticated | List students enrolled in subject. |

### 5. Intelligent Face Enrollment (`/enrollment`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/enrollment/sample` | `FACULTY`, `ADMIN` | Submit camera frame sample for student face enrollment. Checks pose, quality, and duplicate identity. |
| `GET` | `/enrollment/status/{student_id}` | `FACULTY`, `ADMIN` | Retrieve multi-pose sample count and status. |
| `POST` | `/enrollment/reset` | `FACULTY`, `ADMIN` | Wipe stored face embeddings for student re-enrollment. |

### 6. Attendance Verification Pipeline (`/attendance`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/attendance/challenge` | Public / Kiosk | Generate randomized anti-spoofing challenge (`BLINK`, `TURN_LEFT`, `TURN_RIGHT`, `SMILE`). |
| `POST` | `/attendance/mark` | `FACULTY`, `ADMIN` | Full 7-step attendance verification pipeline. Rejects duplicates, spoofs, and low-quality frames. |
| `GET` | `/attendance/today` | Authenticated | Retrieve attendance logs marked today. |
| `GET` | `/attendance/history` | Authenticated | Search historical attendance records by date range and subject. |
| `GET` | `/attendance/export` | `FACULTY`, `ADMIN` | Download attendance records as CSV spreadsheet. |

### 7. Analytics & Monitoring (`/analytics`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/analytics/overview` | `FACULTY`, `ADMIN` | High-level metrics (students, attendance %, rejections). |
| `GET` | `/analytics/subjects` | `FACULTY`, `ADMIN` | Per-subject attendance rate breakdown. |
| `GET` | `/analytics/trends` | `FACULTY`, `ADMIN` | Multi-day attendance trend histogram data. |
| `GET` | `/analytics/pipeline-latency` | `FACULTY`, `ADMIN` | Sub-system latency benchmark measurements. |

### 8. System Configuration & Thresholds (`/settings`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/settings` | Authenticated | Retrieve active AI and pipeline thresholds. |
| `PUT` | `/settings` | `ADMIN` | Dynamically update match thresholds and sensitivity in memory and database. |
