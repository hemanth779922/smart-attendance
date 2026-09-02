# Database Schema & pgvector Setup

## Overview
The Smart Attendance System has completely migrated away from flat CSV and `.npy` files to PostgreSQL with the `pgvector` extension. A high-performance vectorized SQLite engine is also included for out-of-the-box local development and automated testing.

---

## 1. Enabling pgvector in PostgreSQL
Run the following SQL commands in your PostgreSQL database instance:

```sql
-- Connect to your PostgreSQL database
\c attendance_db;

-- Enable the pgvector vector similarity extension
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## 2. Table Definitions

### `users`
System accounts and role permissions.
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'FACULTY', -- 'ADMIN', 'FACULTY', 'STUDENT'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX ix_users_email ON users(email);
```

### `students`
Student roster and demographic records.
```sql
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    student_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    department VARCHAR(100) NOT NULL,
    year INTEGER NOT NULL DEFAULT 1,
    section VARCHAR(10),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX ix_students_code ON students(student_code);
CREATE INDEX ix_students_department ON students(department);
```

### `subjects`
Academic courses and assigned faculty instructors.
```sql
CREATE TABLE subjects (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    department VARCHAR(100) NOT NULL,
    semester INTEGER NOT NULL DEFAULT 1,
    faculty_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX ix_subjects_code ON subjects(code);
```

### `student_subjects`
Course enrollment association table.
```sql
CREATE TABLE student_subjects (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_student_subject_enrollment UNIQUE (student_id, subject_id)
);
```

### `face_embeddings`
Stores multi-pose facial feature vectors (128 dimensions).
```sql
CREATE TABLE face_embeddings (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    embedding vector(128) NOT NULL, -- pgvector 128-dimensional L2 normalized vector
    pose VARCHAR(50) NOT NULL DEFAULT 'frontal', -- 'frontal', 'left', 'right', 'smile'
    quality_score FLOAT NOT NULL DEFAULT 1.0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX ix_face_embeddings_student_id ON face_embeddings(student_id);

-- Cosine Distance HNSW Index for O(log N) similarity search
CREATE INDEX ix_face_embeddings_vector_hnsw ON face_embeddings 
USING hnsw (embedding vector_cosine_ops);
```

### `attendance`
Attendance event logs with cryptographic and quality verification metrics.
```sql
CREATE TABLE attendance (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
    session_date DATE NOT NULL DEFAULT CURRENT_DATE,
    session_time TIME NOT NULL DEFAULT CURRENT_TIME,
    status VARCHAR(50) NOT NULL DEFAULT 'PRESENT',
    confidence FLOAT NOT NULL DEFAULT 1.0,
    spoof_score FLOAT NOT NULL DEFAULT 0.0,
    image_quality_score FLOAT NOT NULL DEFAULT 1.0,
    verified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    verification_method VARCHAR(50) NOT NULL DEFAULT 'FACE_RECOGNITION',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- CRITICAL: Database-level unique constraint prevents duplicate attendance per session/date
    CONSTRAINT uq_student_subject_date UNIQUE (student_id, subject_id, session_date)
);
CREATE INDEX ix_attendance_date ON attendance(session_date);
CREATE INDEX ix_attendance_student ON attendance(student_id);
CREATE INDEX ix_attendance_subject ON attendance(subject_id);
```

### `audit_logs` & `system_settings`
```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT,
    ip_address VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 3. Nearest-Neighbor Similarity Query
Using pgvector's cosine distance operator `<=>`:

```sql
SELECT fe.id, fe.student_id, fe.pose, s.name, s.student_code,
       1 - (fe.embedding <=> :query_embedding) AS similarity
FROM face_embeddings fe
JOIN students s ON fe.student_id = s.id
WHERE fe.is_active = true AND s.is_active = true
ORDER BY fe.embedding <=> :query_embedding
LIMIT 1;
```
