# Smart Attendance System 2.0

> Enterprise AI-Powered Face Recognition Attendance Platform with Low-Light Enhancement, Multi-Signal Anti-Spoofing, and PostgreSQL pgvector Search.

---

## 1. Overview & Solved Limitations

The Smart Attendance System 2.0 addresses the core technical vulnerabilities of traditional face recognition attendance software:

| Limitation | Legacy Architecture | Upgraded Implementation |
| :--- | :--- | :--- |
| **Low Light Failure** | Dark faces fail detection completely | Automated low-light detection with adaptive CLAHE, luminance gamma curve correction, and bilateral denoising. |
| **Spoof Vulnerability** | Static photos & phone screens fool system | Multi-signal anti-spoofing: LBP micro-texture entropy, 2D FFT moiré detection, temporal motion, and randomized challenge-response (`BLINK`, `TURN_LEFT`, `TURN_RIGHT`, `SMILE`). |
| **Blur & Poor Quality** | Degraded frames cause false matches | Real-time quality assessment of blur (Laplacian variance), illumination, contrast, and face size with actionable feedback. |
| **Unreliable Enrollment** | Single frontal photo without validation | Guided multi-pose enrollment (Frontal, Left, Right, Smile), quality thresholds, and duplicate face identity rejection. |
| **Duplicate Attendance** | CSV / Python check can race & duplicate | Database-level unique constraint `uq_student_subject_date` on `(student_id, subject_id, session_date)` guaranteeing atomic uniqueness. |
| **Linear Search Latency** | Memory-loaded $O(N)$ dot product | PostgreSQL `pgvector` indexing with cosine distance `<=>` operator for $O(\log N)$ scalability across millions of faces. |
| **Face Detector** | Legacy 20-year-old Haar Cascades | Modern deep neural network face detector (OpenCV YuNet) with 5-point landmark alignment. |
| **No Access Control** | Open or single user | Tiered Role-Based Access Control (RBAC): `ADMIN`, `FACULTY`, `STUDENT`. |

---

## 2. System Architecture

```
React/Vite Frontend (Kiosk Mode, Interactive Enrollment, Dashboards)
                           │
                           ▼ (HTTP / JSON / JWT)
FastAPI Backend (Lifespan Model Loading, RBAC, Timing Headers)
                           │
                           ▼
AI Computer Vision Pipeline (Low-Light CLAHE, Quality Assessment, YuNet, Anti-Spoof, SFace 128-d)
                           │
                           ▼
PostgreSQL + pgvector Database (Cosine Distance Search, Relational Schema, Unique Constraints)
```

For complete technical diagrams and module specifications, see [`docs/architecture.md`](docs/architecture.md).

---

## 3. Technology Stack

- **Backend**: Python 3.14, FastAPI, SQLAlchemy 2.0, Pydantic V2, Uvicorn
- **AI & CV**: OpenCV 5 (YuNet Face Detection, SFace Face Recognizer), NumPy, Scikit-learn, SciPy
- **Database**: PostgreSQL 16+ with `pgvector` extension (SQLite with vectorized dot product fallback for local testing)
- **Frontend**: React 19, Vite 8, Lucide Icons
- **Security**: Native Bcrypt password hashing, JWT access & refresh tokens
- **Testing**: Pytest, Pytest-asyncio, HTTPX

---

## 4. Getting Started & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- PostgreSQL with `pgvector` (optional for production, SQLite works out of the box for development)

### 1. Backend Setup
```bash
# Clone the repository and navigate into directory
git clone https://github.com/hemanth779922/smart-attendance.git
cd smart-attendance

# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn pydantic pydantic-settings python-jose bcrypt opencv-python sqlalchemy pgvector psycopg2-binary scikit-learn scipy pytest httpx email-validator
```

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
PROJECT_NAME="Smart Attendance System"
PROJECT_VERSION="2.0.0"
ENVIRONMENT="development"

# Database Configuration
# For local SQLite:
DATABASE_URL="sqlite:///./smart_attendance.db"
# For PostgreSQL + pgvector:
# DATABASE_URL="postgresql://postgres:postgres@localhost:5432/attendance_db"

# Security & JWT
SECRET_KEY="your-super-secure-production-secret-key-change-me"
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# AI & Pipeline Thresholds
FACE_MATCH_THRESHOLD=0.65
LOW_LIGHT_THRESHOLD=45.0
BLUR_THRESHOLD=40.0
MIN_FACE_SIZE=80
SPOOF_THRESHOLD=0.45
LIVENESS_THRESHOLD=0.60
ENROLLMENT_MIN_SAMPLES=5
```

### 3. Initialize & Run Backend Server
```bash
# Run FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive API documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

Default seeded credentials:
- **Admin**: `admin@attendance.edu` / `Admin@12345`
- **Faculty**: `faculty@attendance.edu` / `Faculty@12345`

### 4. Run Frontend Application
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 5. Automated Test Suite

Run the full automated test suite covering authentication, RBAC, low-light enhancement, image quality checks, anti-spoofing, vector search, duplicate attendance prevention, enrollment, and end-to-end integration:

```bash
# Run pytest
python -m pytest app/tests -v
```

---

## 6. Detailed Documentation
- [System Architecture](docs/architecture.md)
- [AI & Computer Vision Pipeline](docs/ai_pipeline.md)
- [Database Schema & pgvector Guide](docs/database.md)
- [API Reference](docs/api.md)

---

## 7. Limitations & Future Scope

### Realistic Anti-Spoofing Statement
> [!NOTE]
> No facial recognition or anti-spoofing pipeline can claim 100% immunity against sophisticated presentation attacks. This system implements multi-signal defense-in-depth (LBP micro-texture, 2D FFT moiré detection, temporal motion, and interactive randomized challenges).

### Future Roadmap
1. **Infrared / 3D Depth Sensing**: Integration with Intel RealSense or stereo depth cameras for hardware-level sub-millimeter liveness verification.
2. **Multi-Camera Edge Deployment**: Support for streaming RTSP IP camera inputs across multiple campus lecture halls simultaneously.
3. **Automated Absence Notifications**: Email / SMS alerts sent to students or advisors for consecutive absences.
