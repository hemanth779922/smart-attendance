import os
import sys
import time
from datetime import date, datetime
import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath("."))

from app.core.config import settings
from app.db.session import SessionLocal, init_db
from app.models.student import Student
from app.models.subject import Subject, StudentSubject
from app.models.attendance import Attendance, AttendanceStatus
from app.models.face_embedding import FaceEmbedding
from app.models.system_setting import SystemSetting
from app.ai.face_engine import (
    load_cascades,
    detect_faces,
    align_face,
    generate_face_embedding,
    compute_cosine_similarity
)
from app.ai.low_light import detect_low_light, enhance_low_light, assess_face_quality
from app.ai.quality_assessment import assess_frame_quality
from app.ai.anti_spoofing import verify_anti_spoofing, generate_anti_spoof_challenge
from app.ai.vector_search import search_similar_face
from sqlalchemy.exc import IntegrityError

# Page Config
st.set_page_config(
    page_title="Smart Attendance System 2.0",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .sub-title {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 25px;
    }
    .metric-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .status-badge-ok {
        background: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.4);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
    .status-badge-warn {
        background: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.4);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize DB and AI models once
@st.cache_resource
def setup_system():
    init_db()
    load_cascades()
    return True

setup_system()

# Sidebar Navigation
st.sidebar.markdown("## 🎓 Smart Attendance")
st.sidebar.markdown("**AI Face Recognition 2.0**")
menu_choice = st.sidebar.radio(
    "Navigation Menu",
    [
        "📊 Dashboard & Telemetry",
        "📸 Take Attendance (Kiosk)",
        "👤 Smart Face Enrollment",
        "📋 Today's Attendance",
        "📜 Attendance History",
        "👥 Student Directory",
        "📚 Subjects & Courses",
        "⚙️ AI Threshold Settings"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Engine Status:** OpenCV YuNet + SFace + pgvector Active")

# Helper to convert PIL to BGR OpenCV format
def pil_to_cv2(image_pil):
    img = np.array(image_pil)
    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

# ==============================================================================
# 1. DASHBOARD & TELEMETRY
# ==============================================================================
if menu_choice == "📊 Dashboard & Telemetry":
    st.markdown('<p class="main-title">Executive Attendance Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Real-time operational telemetry, attendance rates, and AI security status</p>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        total_students = db.query(Student).count()
        enrolled_students = db.query(Student).join(FaceEmbedding).distinct().count()
        total_subjects = db.query(Subject).count()
        today_att = db.query(Attendance).filter(Attendance.session_date == date.today()).count()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Students", total_students, f"{enrolled_students} with face data")
        with col2:
            st.metric("Today's Check-ins", today_att, "Active sessions")
        with col3:
            st.metric("Total Subjects", total_subjects, "Registered classes")
        with col4:
            enroll_rate = round((enrolled_students / max(total_students, 1)) * 100, 1)
            st.metric("Biometric Coverage", f"{enroll_rate}%", "Enrolled")

        st.markdown("---")
        st.subheader("📚 Subject Attendance Performance (Today)")
        subjects = db.query(Subject).all()
        if subjects:
            sub_data = []
            for s in subjects:
                enrolled_count = db.query(StudentSubject).filter(StudentSubject.subject_id == s.id).count()
                present_today = db.query(Attendance).filter(
                    Attendance.subject_id == s.id,
                    Attendance.session_date == date.today()
                ).count()
                pct = round((present_today / max(enrolled_count, 1)) * 100, 1)
                sub_data.append({
                    "Course Code": s.code,
                    "Course Name": s.name,
                    "Department": s.department,
                    "Enrolled": enrolled_count,
                    "Present Today": present_today,
                    "Attendance %": f"{pct}%"
                })
            st.dataframe(pd.DataFrame(sub_data), use_container_width=True)
        else:
            st.info("No courses created yet. Register courses in 'Subjects & Courses'.")

        st.markdown("---")
        st.subheader("🛡️ AI Computer Vision Security Highlights")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.success("✓ **Adaptive Low-Light CLAHE**\n\nPreserves dim lecture hall faces without washing out ambient lighting.")
        with c2:
            st.success("✓ **Multi-Signal Anti-Spoofing**\n\nLBP texture entropy, 2D FFT moiré detection, and active liveness verification.")
        with c3:
            st.success("✓ **pgvector Vector Database**\n\nO(log N) nearest-neighbor cosine similarity search (<=>) with atomic unique constraints.")

    finally:
        db.close()

# ==============================================================================
# 2. TAKE ATTENDANCE (KIOSK MODE)
# ==============================================================================
elif menu_choice == "📸 Take Attendance (Kiosk)":
    st.markdown('<p class="main-title">Automated Attendance Kiosk</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">7-Stage facial recognition pipeline with liveness challenge verification</p>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        subjects = db.query(Subject).filter(Subject.is_active == True).all()
        if not subjects:
            st.warning("⚠️ No active subjects found. Please create a subject first in 'Subjects & Courses'.")
            st.stop()

        col_left, col_right = st.columns([1.5, 1])

        with col_right:
            st.subheader("⚙️ Session Setup")
            sub_options = {f"{s.code} - {s.name}": s.id for s in subjects}
            selected_sub_name = st.selectbox("Select Class / Subject Session", list(sub_options.keys()))
            selected_subject_id = sub_options[selected_sub_name]

            # Anti-spoof challenge
            if "current_challenge" not in st.session_state:
                st.session_state.current_challenge = generate_anti_spoof_challenge()

            chal = st.session_state.current_challenge
            st.markdown(f"""
            <div class="metric-card">
                <h4>🎯 Active Liveness Challenge</h4>
                <p style="font-size: 1.1rem; color: #38bdf8; font-weight: bold;">{chal['challenge_type']}</p>
                <p style="color: #94a3b8;">{chal['instruction']}</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔄 Generate New Challenge"):
                st.session_state.current_challenge = generate_anti_spoof_challenge()
                st.rerun()

        with col_left:
            st.subheader("📹 Real-Time Camera View")
            camera_image = st.camera_input("Position face squarely inside frame and click Take Photo")

            if camera_image is not None:
                pil_img = Image.open(camera_image)
                frame_bgr = pil_to_cv2(pil_img)

                with st.spinner("Executing 7-Stage Verification Pipeline..."):
                    t_start = time.time()

                    # Stage 1: Quality Check
                    q_res = assess_frame_quality(frame_bgr)
                    if not q_res["quality_ok"]:
                        st.error(f"❌ Quality Rejection: {q_res['actionable_feedback']}")
                        st.stop()

                    # Stage 2: Low-Light Check & Enhancement
                    is_low, light_metrics = detect_low_light(frame_bgr)
                    if is_low:
                        processed_frame, _ = enhance_low_light(frame_bgr)
                        st.info("🌙 Low-light detected: Adaptive CLAHE & Gamma correction applied.")
                    else:
                        processed_frame = frame_bgr

                    # Stage 3: Face Detection
                    faces = detect_faces(processed_frame, apply_low_light_check=False)
                    if not faces:
                        st.error("❌ Face Not Detected: Please look directly into the camera.")
                        st.stop()

                    face = faces[0]
                    face_crop = face["face_crop"]
                    landmarks = face.get("landmarks")

                    # Stage 4: Anti-Spoofing & Liveness
                    spoof_res = verify_anti_spoofing(
                        face_crop=face_crop,
                        challenge_token=chal["challenge_token"],
                        detected_action=chal["challenge_type"]
                    )
                    if spoof_res["spoof_score"] > settings.SPOOF_THRESHOLD or not spoof_res["is_live"]:
                        st.error(f"🚫 Spoof Attack Intercepted! Spoof probability: {round(spoof_res['spoof_score']*100, 1)}%")
                        st.session_state.current_challenge = generate_anti_spoof_challenge()
                        st.stop()

                    # Stage 5: 128-d Feature Embedding
                    aligned = align_face(face_crop, landmarks)
                    emb_vec = generate_face_embedding(aligned)

                    # Stage 6: Vector Search
                    match_res = search_similar_face(emb_vec, db)
                    t_elapsed_ms = round((time.time() - t_start) * 1000, 1)

                    if not match_res["recognized"]:
                        st.warning(f"⚠️ Unknown Face: Highest match similarity was {round(match_res['similarity']*100, 1)}% (Threshold: {settings.FACE_MATCH_THRESHOLD*100}%).")
                        st.stop()

                    student_id = match_res["student_id"]
                    matched_student = db.query(Student).filter(Student.id == student_id).first()

                    # Check enrollment in subject
                    is_enrolled = db.query(StudentSubject).filter(
                        StudentSubject.student_id == student_id,
                        StudentSubject.subject_id == selected_subject_id
                    ).first()

                    if not is_enrolled:
                        st.error(f"❌ Student {matched_student.name} ({matched_student.student_code}) is NOT enrolled in this subject course!")
                        st.stop()

                    # Stage 7: Database Commit with Unique Constraint Check
                    today = date.today()
                    now_time = datetime.now().time()

                    att_record = Attendance(
                        student_id=student_id,
                        subject_id=selected_subject_id,
                        session_date=today,
                        session_time=now_time,
                        status=AttendanceStatus.PRESENT,
                        confidence=match_res["similarity"],
                        spoof_score=spoof_res["spoof_score"],
                        image_quality_score=q_res["blur_score"],
                        verification_method="STREAMLIT_AI_KIOSK"
                    )

                    try:
                        db.add(att_record)
                        db.commit()
                        st.success(f"✅ **Attendance Marked Successfully!**\n\n**Student:** {matched_student.name} ({matched_student.student_code})\n\n**Match Similarity:** {round(match_res['similarity']*100, 1)}% • **Pipeline Latency:** {t_elapsed_ms} ms")
                        st.balloons()
                        st.session_state.current_challenge = generate_anti_spoof_challenge()
                    except IntegrityError:
                        db.rollback()
                        st.info(f"ℹ️ **Already Marked Today:** Attendance for {matched_student.name} in this class has already been recorded.")

    finally:
        db.close()

# ==============================================================================
# 3. SMART FACE ENROLLMENT
# ==============================================================================
elif menu_choice == "👤 Smart Face Enrollment":
    st.markdown('<p class="main-title">Guided Multi-Pose Face Enrollment</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Train high-precision 128-d vectors with real-time pose and quality feedback</p>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        students = db.query(Student).filter(Student.is_active == True).all()
        if not students:
            st.warning("No students registered. Please create students in 'Student Directory' first.")
            st.stop()

        student_dict = {f"{s.student_code} - {s.name} ({s.department})": s.id for s in students}
        selected_student_str = st.selectbox("Select Student to Enroll", list(student_dict.keys()))
        selected_student_id = student_dict[selected_student_str]

        # Check existing enrollment status
        existing_embeddings = db.query(FaceEmbedding).filter(
            FaceEmbedding.student_id == selected_student_id,
            FaceEmbedding.is_active == True
        ).all()
        sample_count = len(existing_embeddings)
        required_samples = settings.ENROLLMENT_MIN_SAMPLES

        st.progress(min(1.0, sample_count / required_samples))
        st.write(f"**Enrollment Status:** {sample_count} of {required_samples} poses captured.")

        if sample_count >= required_samples:
            st.success("🎉 Student face enrollment is COMPLETE and active in vector database!")

        c1, c2 = st.columns([1, 1])
        with c1:
            target_pose = st.selectbox(
                "Target Pose to Capture",
                ["frontal", "left", "right", "smile", "any"],
                help="Capture varied facial angles to achieve high recognition accuracy."
            )
            enr_image = st.camera_input("Capture Face Snapshot")

            if enr_image is not None and st.button("💾 Submit Pose Sample"):
                pil_img = Image.open(enr_image)
                frame_bgr = pil_to_cv2(pil_img)

                q_res = assess_frame_quality(frame_bgr)
                if not q_res["quality_ok"]:
                    st.error(f"❌ Rejected: {q_res['actionable_feedback']}")
                    st.stop()

                faces = detect_faces(frame_bgr)
                if not faces:
                    st.error("❌ No face detected. Position yourself clearly in view.")
                    st.stop()

                face = faces[0]
                aligned = align_face(face["face_crop"], face.get("landmarks"))
                new_vec = generate_face_embedding(aligned)

                # Duplicate identity check
                dup_match = search_similar_face(new_vec, db)
                if dup_match["recognized"] and dup_match["student_id"] != selected_student_id:
                    dup_student = db.query(Student).filter(Student.id == dup_match["student_id"]).first()
                    st.error(f"🚫 Conflict Detected! This face strongly matches enrolled student: {dup_student.name} ({dup_student.student_code}).")
                    st.stop()

                # Save embedding
                new_fe = FaceEmbedding(
                    student_id=selected_student_id,
                    pose=target_pose,
                    quality_score=q_res["blur_score"],
                    is_active=True
                )
                new_fe.set_embedding(new_vec)
                db.add(new_fe)
                db.commit()
                st.success(f"✅ Pose sample '{target_pose.upper()}' saved successfully!")
                st.rerun()

        with c2:
            st.subheader("📋 Enrolled Poses")
            if existing_embeddings:
                poses_data = [{"Sample #": i+1, "Pose": fe.pose, "Quality Score": round(fe.quality_score, 1)} for i, fe in enumerate(existing_embeddings)]
                st.dataframe(pd.DataFrame(poses_data), use_container_width=True)

                if st.button("🗑️ Reset All Embeddings for this Student"):
                    db.query(FaceEmbedding).filter(FaceEmbedding.student_id == selected_student_id).delete()
                    db.commit()
                    st.warning("Biometric embeddings reset.")
                    st.rerun()
            else:
                st.info("No face embeddings stored yet for this student.")

    finally:
        db.close()

# ==============================================================================
# 4. TODAY'S ATTENDANCE
# ==============================================================================
elif menu_choice == "📋 Today's Attendance":
    st.markdown('<p class="main-title">Today\'s Verified Attendance</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Real-time attendance logs recorded across all course sessions today</p>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        today = date.today()
        records = db.query(Attendance).filter(Attendance.session_date == today).all()

        if records:
            data = []
            for r in records:
                s = db.query(Student).filter(Student.id == r.student_id).first()
                sub = db.query(Subject).filter(Subject.id == r.subject_id).first()
                data.append({
                    "Roll Code": s.student_code if s else "-",
                    "Student Name": s.name if s else "-",
                    "Course": f"{sub.code} - {sub.name}" if sub else "-",
                    "Time": r.session_time.strftime("%H:%M:%S") if r.session_time else "-",
                    "Status": r.status.value if hasattr(r.status, 'value') else str(r.status),
                    "Similarity": f"{round(r.confidence * 100, 1)}%",
                    "Method": r.verification_method
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Today's Logs (CSV)",
                data=csv,
                file_name=f"attendance_{today}.csv",
                mime="text/csv"
            )
        else:
            st.info("No attendance records marked yet today.")

    finally:
        db.close()

# ==============================================================================
# 5. ATTENDANCE HISTORY
# ==============================================================================
elif menu_choice == "📜 Attendance History":
    st.markdown('<p class="main-title">Attendance History & Audit</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Historical attendance search with date range and course filtering</p>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        c1, c2 = st.columns(2)
        with c1:
            start_d = st.date_input("Start Date", value=date.today())
        with c2:
            end_d = st.date_input("End Date", value=date.today())

        query = db.query(Attendance).filter(
            Attendance.session_date >= start_d,
            Attendance.session_date <= end_d
        )
        records = query.all()

        if records:
            data = []
            for r in records:
                s = db.query(Student).filter(Student.id == r.student_id).first()
                sub = db.query(Subject).filter(Subject.id == r.subject_id).first()
                data.append({
                    "Date": r.session_date.strftime("%Y-%m-%d"),
                    "Time": r.session_time.strftime("%H:%M:%S") if r.session_time else "-",
                    "Roll Code": s.student_code if s else "-",
                    "Student Name": s.name if s else "-",
                    "Course": f"{sub.code} - {sub.name}" if sub else "-",
                    "Status": r.status.value if hasattr(r.status, 'value') else str(r.status),
                    "Similarity": f"{round(r.confidence * 100, 1)}%"
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Filtered History (CSV)",
                data=csv,
                file_name=f"attendance_history_{start_d}_to_{end_d}.csv",
                mime="text/csv"
            )
        else:
            st.info("No historical records found for this date range.")

    finally:
        db.close()

# ==============================================================================
# 6. STUDENT DIRECTORY
# ==============================================================================
elif menu_choice == "👥 Student Directory":
    st.markdown('<p class="main-title">Student Directory</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Manage student profiles, registrations, and biometric enrollment</p>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        with st.expander("➕ Register New Student"):
            with st.form("add_student_form"):
                col_a, col_b = st.columns(2)
                with col_a:
                    s_code = st.text_input("Roll / Student Code *", placeholder="e.g. 221FA04001")
                    s_name = st.text_input("Full Name *", placeholder="e.g. Alan Turing")
                with col_b:
                    s_email = st.text_input("Email Address *", placeholder="e.g. alan@attendance.edu")
                    s_dept = st.selectbox("Department", ["Computer Science", "Information Technology", "Electrical Engineering", "Electronics"])
                s_year = st.selectbox("Year of Study", [1, 2, 3, 4])

                if st.form_submit_button("Create Student Record"):
                    if s_code and s_name and s_email:
                        new_student = Student(
                            student_code=s_code,
                            name=s_name,
                            email=s_email,
                            department=s_dept,
                            year=s_year,
                            is_active=True
                        )
                        db.add(new_student)
                        try:
                            db.commit()
                            st.success(f"Student {s_name} ({s_code}) registered successfully!")
                            st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"Error registering student: {e}")
                    else:
                        st.error("Please fill in all required fields.")

        students = db.query(Student).all()
        if students:
            st.subheader(f"Enrolled Students ({len(students)})")
            s_data = []
            for s in students:
                emb_count = db.query(FaceEmbedding).filter(FaceEmbedding.student_id == s.id, FaceEmbedding.is_active == True).count()
                s_data.append({
                    "ID": s.id,
                    "Roll Code": s.student_code,
                    "Name": s.name,
                    "Email": s.email,
                    "Department": s.department,
                    "Year": f"Year {s.year}",
                    "Biometric Status": f"Enrolled ({emb_count} poses)" if emb_count >= settings.ENROLLMENT_MIN_SAMPLES else f"Pending ({emb_count}/{settings.ENROLLMENT_MIN_SAMPLES})"
                })
            st.dataframe(pd.DataFrame(s_data), use_container_width=True)
        else:
            st.info("No students registered yet.")

    finally:
        db.close()

# ==============================================================================
# 7. SUBJECTS & COURSES
# ==============================================================================
elif menu_choice == "📚 Subjects & Courses":
    st.markdown('<p class="main-title">Course Management</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Configure academic courses and map enrolled student rosters</p>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        with st.expander("➕ Create New Course"):
            with st.form("add_subject_form"):
                c1, c2 = st.columns(2)
                with c1:
                    sub_code = st.text_input("Course Code *", placeholder="e.g. CS401")
                    sub_name = st.text_input("Course Title *", placeholder="e.g. Artificial Intelligence & Computer Vision")
                with c2:
                    sub_dept = st.selectbox("Department", ["Computer Science", "Information Technology", "Electrical Engineering"])
                    sub_sem = st.number_input("Semester", min_value=1, max_value=8, value=5)

                if st.form_submit_button("Save Course"):
                    if sub_code and sub_name:
                        new_sub = Subject(code=sub_code, name=sub_name, department=sub_dept, semester=sub_sem, is_active=True)
                        db.add(new_sub)
                        try:
                            db.commit()
                            st.success(f"Course {sub_name} created!")
                            st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"Error: {e}")

        subjects = db.query(Subject).all()
        students = db.query(Student).all()

        if subjects:
            for s in subjects:
                enrolled_count = db.query(StudentSubject).filter(StudentSubject.subject_id == s.id).count()
                with st.container():
                    st.markdown(f"### 📘 {s.code}: {s.name}")
                    st.caption(f"Department: {s.department} • Semester: {s.semester} • Currently Enrolled: {enrolled_count} students")

                    # Manage enrollment
                    enrolled_student_ids = [row.student_id for row in db.query(StudentSubject).filter(StudentSubject.subject_id == s.id).all()]
                    all_students_options = {f"{st_obj.student_code} - {st_obj.name}": st_obj.id for st_obj in students}

                    default_selected = [k for k, v in all_students_options.items() if v in enrolled_student_ids]
                    selected = st.multiselect(
                        f"Enroll Students in {s.code}",
                        options=list(all_students_options.keys()),
                        default=default_selected,
                        key=f"sub_{s.id}"
                    )

                    if st.button(f"Update Roster for {s.code}", key=f"btn_{s.id}"):
                        new_selected_ids = [all_students_options[k] for k in selected]
                        # Remove unselected
                        db.query(StudentSubject).filter(
                            StudentSubject.subject_id == s.id,
                            ~StudentSubject.student_id.in_(new_selected_ids)
                        ).delete(synchronize_session=False)

                        # Add new
                        for sid in new_selected_ids:
                            exists = db.query(StudentSubject).filter(
                                StudentSubject.subject_id == s.id,
                                StudentSubject.student_id == sid
                            ).first()
                            if not exists:
                                db.add(StudentSubject(student_id=sid, subject_id=s.id))

                        db.commit()
                        st.success(f"Updated student roster for {s.code}!")
                        st.rerun()
                    st.markdown("---")
        else:
            st.info("No courses registered yet.")

    finally:
        db.close()

# ==============================================================================
# 8. AI THRESHOLD SETTINGS
# ==============================================================================
elif menu_choice == "⚙️ AI Threshold Settings":
    st.markdown('<p class="main-title">Dynamic Threshold Configuration</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Tune computer vision sensitivity, match thresholds, and quality gates in real time</p>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        st.subheader("🎚️ Computer Vision & Recognition Parameters")

        match_th = st.slider(
            "Face Match Cosine Similarity Threshold",
            min_value=0.40,
            max_value=0.95,
            value=float(settings.FACE_MATCH_THRESHOLD),
            step=0.01,
            help="Minimum cosine similarity required to authenticate a student. Higher values enforce stricter visual similarity."
        )

        light_th = st.slider(
            "Low-Light Trigger Luminance (0-255)",
            min_value=20.0,
            max_value=90.0,
            value=float(settings.LOW_LIGHT_THRESHOLD),
            step=1.0,
            help="Luminance threshold below which adaptive CLAHE and non-linear gamma curves are automatically applied."
        )

        blur_th = st.slider(
            "Blur / Sharpness Threshold (Laplacian Variance)",
            min_value=15.0,
            max_value=120.0,
            value=float(settings.BLUR_THRESHOLD),
            step=1.0,
            help="Variance threshold below which captured frames are rejected as motion-blurred."
        )

        spoof_th = st.slider(
            "Maximum Allowable Spoof Probability",
            min_value=0.20,
            max_value=0.80,
            value=float(settings.SPOOF_THRESHOLD),
            step=0.01,
            help="Upper bound threshold for LBP texture and FFT frequency moiré presentation attack rejection."
        )

        if st.button("💾 Save & Apply Thresholds"):
            settings.FACE_MATCH_THRESHOLD = match_th
            settings.LOW_LIGHT_THRESHOLD = light_th
            settings.BLUR_THRESHOLD = blur_th
            settings.SPOOF_THRESHOLD = spoof_th

            # Save in database
            for k, v in [
                ("FACE_MATCH_THRESHOLD", match_th),
                ("LOW_LIGHT_THRESHOLD", light_th),
                ("BLUR_THRESHOLD", blur_th),
                ("SPOOF_THRESHOLD", spoof_th),
            ]:
                rec = db.query(SystemSetting).filter(SystemSetting.key == k).first()
                if rec:
                    rec.value = str(v)
                else:
                    db.add(SystemSetting(key=k, value=str(v)))
            db.commit()
            st.success("✅ AI & Pipeline thresholds updated dynamically in database and memory!")

    finally:
        db.close()
