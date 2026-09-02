# System Architecture

## Overview
The Smart Attendance System 2.0 is an enterprise-grade AI-powered facial recognition platform. It addresses the fundamental vulnerabilities and limitations of legacy attendance systems (poor performance in dim lighting, static video/photo spoofing, frame blur/distortion, linear $O(N)$ embedding comparison, manual enrollment bottlenecks, and CSV storage limits).

```
+-------------------------------------------------------------+
|                      React / Vite UI                        |
|   (Kiosk Mode, Real-Time Feedback, Camera Feed, Dashboards)  |
+-------------------------------------------------------------+
                              |
                              v  (REST / JSON API / JWT)
+-------------------------------------------------------------+
|                      FastAPI Backend                        |
|     (Lifespan Management, RBAC Auth, Timing Middleware)     |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                    AI / CV Engine                           |
|  - Quality Assessment (Brightness, Blur, Contrast, Size)     |
|  - Low-Light CLAHE & Gamma Adaptive Enhancement             |
|  - OpenCV YuNet Deep Face Detection & 5-Point Alignment     |
|  - Multi-Signal Anti-Spoofing (LBP, FFT, Liveness Challenge)|
|  - SFace Deep Feature Embedding (128-d Normalized Vector)   |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                PostgreSQL + pgvector Database               |
|  - Cosine Distance Nearest-Neighbor Search (<=>)            |
|  - Database-Level Unique Constraint on (student,subject,date)|
|  - Relational Models: Users, Students, Subjects, Attendance |
+-------------------------------------------------------------+
```

## Architectural Layers

### 1. Presentation Layer (Frontend)
- **Framework**: React 19 with Vite 8.
- **Components**:
  - **Attendance Kiosk**: Real-time step badges (`Detecting face...`, `Checking image quality...`, `Checking liveness...`, `Recognizing...`, `Attendance marked`, etc.), active randomized challenge countdown timer, latency breakdown.
  - **Intelligent Enrollment Kiosk**: Multi-pose guidance (`Frontal`, `Slight Left`, `Slight Right`, `Smile`), live lighting & sharpness meters, duplicate face check, automatic sample accumulation.
  - **Administrative Dashboards**: Student directory, course/subject mappings, live logs with CSV export, historical analytics, user access control, dynamic AI threshold sliders.

### 2. Service & Business Layer (Backend)
- **Framework**: FastAPI (Python 3.14).
- **Lifespan Engine**: AI models (YuNet detector and SFace recognizer) are pre-warmed once at application startup as singletons, eliminating runtime re-instantiation latency.
- **RBAC**: Three distinct privilege tiers:
  - `ADMIN`: User management, student/subject CRUD, dynamic threshold configuration.
  - `FACULTY`: Taking attendance, viewing logs, managing assigned subjects, enrolling students.
  - `STUDENT`: Viewing personal profile and attendance records.
- **Security**: Native bcrypt password hashing (72-byte truncation enforced), stateless JWT bearer authentication with access and refresh tokens.

### 3. AI Computer Vision Subsystem
- **Modular Preprocessing**: Independent modules in `app/ai/` for low-light enhancement, quality checks, anti-spoofing, and facial embedding.
- **Vector Search Engine**: Employs pgvector cosine distance `<=>` nearest-neighbor indexing for $O(\log N)$ scalability across millions of face records.

### 4. Persistence Layer
- **Relational Tables**: `users`, `students`, `subjects`, `student_subjects`, `attendance`, `face_embeddings`, `audit_logs`, `system_settings`.
- **Integrity**: Enforces a database-level unique constraint `uq_student_subject_date` on `attendance(student_id, subject_id, session_date)`, guaranteeing zero duplicate attendance records even under concurrent network submissions.
