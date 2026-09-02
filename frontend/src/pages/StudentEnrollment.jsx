import React, { useState, useEffect, useRef } from "react";
import { api } from "../api";
import {
  Camera,
  CheckCircle,
  AlertCircle,
  RotateCcw,
  Sparkles,
  Sun,
  Focus,
  Maximize,
  Smile,
  ArrowLeft
} from "lucide-react";

export const StudentEnrollment = ({ initialStudentId, onBack }) => {
  const [students, setStudents] = useState([]);
  const [selectedStudentId, setSelectedStudentId] = useState(initialStudentId || "");
  const [enrollmentStatus, setEnrollmentStatus] = useState(null);
  const [targetPose, setTargetPose] = useState("frontal");
  const [capturing, setCapturing] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState("");

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  const poses = [
    { id: "frontal", label: "1. Frontal Pose", desc: "Look directly at camera" },
    { id: "left", label: "2. Slight Left", desc: "Turn head slightly to your left" },
    { id: "right", label: "3. Slight Right", desc: "Turn head slightly to your right" },
    { id: "smile", label: "4. Expression / Smile", desc: "Smile naturally" },
    { id: "any", label: "5. Additional Sample", desc: "Natural pose" },
  ];

  // Load students list
  useEffect(() => {
    const fetchStudents = async () => {
      try {
        const list = await api.getStudents();
        setStudents(list);
        if (!selectedStudentId && list.length > 0) {
          setSelectedStudentId(list[0].id);
        }
      } catch (err) {
        console.error("Failed to load students:", err);
      }
    };
    fetchStudents();
  }, []);

  // Fetch enrollment status when student changes
  useEffect(() => {
    if (!selectedStudentId) return;
    const fetchStatus = async () => {
      try {
        const res = await api.getEnrollmentStatus(selectedStudentId);
        setEnrollmentStatus(res);
      } catch (err) {
        console.error("Failed to get enrollment status:", err);
      }
    };
    fetchStatus();
  }, [selectedStudentId]);

  // Start webcam
  const startCamera = async () => {
    setCameraError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraActive(true);
    } catch (err) {
      setCameraError("Camera access denied or unavailable. Please enable webcam permissions.");
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  useEffect(() => {
    startCamera();
    return () => stopCamera();
  }, []);

  const captureFrameBase64 = () => {
    if (!videoRef.current || !canvasRef.current) return null;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.9);
  };

  const handleCaptureSample = async () => {
    if (!selectedStudentId) {
      alert("Please select a student first.");
      return;
    }

    const b64 = captureFrameBase64();
    if (!b64) return;

    setCapturing(true);
    setFeedback(null);

    try {
      const res = await api.submitEnrollmentSample({
        student_id: parseInt(selectedStudentId),
        image_base64: b64,
        target_pose: targetPose,
      });

      setFeedback(res);

      if (res.accepted) {
        // Refresh status
        const statusRes = await api.getEnrollmentStatus(selectedStudentId);
        setEnrollmentStatus(statusRes);

        // Advance to next pose
        const currentIdx = poses.findIndex((p) => p.id === targetPose);
        if (currentIdx < poses.length - 1) {
          setTargetPose(poses[currentIdx + 1].id);
        }
      }
    } catch (err) {
      setFeedback({
        accepted: false,
        feedback_message: err.message || "Failed to process sample.",
        quality_score: 0.0,
      });
    } finally {
      setCapturing(false);
    }
  };

  const handleResetEnrollment = async () => {
    if (!selectedStudentId) return;
    if (window.confirm("Reset all stored face embeddings for this student?")) {
      try {
        await api.resetEnrollment(parseInt(selectedStudentId));
        const statusRes = await api.getEnrollmentStatus(selectedStudentId);
        setEnrollmentStatus(statusRes);
        setFeedback(null);
        setTargetPose("frontal");
      } catch (err) {
        alert(err.message || "Failed to reset enrollment.");
      }
    }
  };

  const currentStudent = students.find((s) => s.id === parseInt(selectedStudentId));
  const samplesCollected = enrollmentStatus?.sample_count || 0;
  const samplesRequired = enrollmentStatus?.samples_required || 5;
  const isComplete = enrollmentStatus?.is_enrolled || false;

  return (
    <div className="page-container">
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {onBack && (
            <button className="btn-icon" onClick={onBack} title="Back">
              <ArrowLeft size={20} />
            </button>
          )}
          <div>
            <h2 className="page-title">Intelligent Face Enrollment</h2>
            <p className="page-subtitle">
              Capture multi-pose high-quality embeddings with real-time pose and lighting validation
            </p>
          </div>
        </div>
      </div>

      <div className="enrollment-grid">
        {/* Left Column: Camera Feed */}
        <div className="enrollment-camera-card">
          <div className="camera-view-container">
            {cameraError ? (
              <div className="camera-error-box">
                <AlertCircle size={40} />
                <p>{cameraError}</p>
                <button className="btn-secondary" onClick={startCamera}>
                  Retry Camera
                </button>
              </div>
            ) : (
              <>
                <video ref={videoRef} autoPlay playsInline muted className="camera-video" />
                <div className="camera-face-guide"></div>
                <canvas ref={canvasRef} style={{ display: "none" }} />
              </>
            )}

            {/* Target Pose Badge Overlay */}
            <div className="pose-target-badge">
              <Sparkles size={16} />
              <span>Target: {poses.find((p) => p.id === targetPose)?.label}</span>
            </div>
          </div>

          <div className="camera-controls">
            <button
              className="btn-primary btn-large btn-capture"
              onClick={handleCaptureSample}
              disabled={capturing || !cameraActive || isComplete}
            >
              <Camera size={20} />
              <span>{capturing ? "Analyzing Quality & Pose..." : `Capture ${targetPose.toUpperCase()} Pose`}</span>
            </button>
          </div>

          {/* Real-time Feedback Box */}
          {feedback && (
            <div className={`feedback-card ${feedback.accepted ? "feedback-success" : "feedback-warning"}`}>
              <div className="feedback-header">
                {feedback.accepted ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
                <h4>{feedback.accepted ? "Sample Accepted!" : "Sample Rejected"}</h4>
                <span className="feedback-score">Quality Score: {(feedback.quality_score * 100).toFixed(0)}%</span>
              </div>
              <p className="feedback-msg">{feedback.feedback_message}</p>
            </div>
          )}
        </div>

        {/* Right Column: Enrollment Guidance & Progress */}
        <div className="enrollment-sidebar">
          <div className="card-box">
            <h3 className="card-title">Select Student</h3>
            <div className="input-group">
              <select
                className="filter-select"
                style={{ width: "100%" }}
                value={selectedStudentId}
                onChange={(e) => setSelectedStudentId(e.target.value)}
              >
                {students.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.student_code} - {s.name} ({s.department})
                  </option>
                ))}
              </select>
            </div>

            {currentStudent && (
              <div className="student-summary">
                <div className="summary-row">
                  <span className="text-muted">Student Name:</span>
                  <span className="text-bold">{currentStudent.name}</span>
                </div>
                <div className="summary-row">
                  <span className="text-muted">Roll Number:</span>
                  <span className="font-mono text-bold">{currentStudent.student_code}</span>
                </div>
                <div className="summary-row">
                  <span className="text-muted">Department:</span>
                  <span>{currentStudent.department}</span>
                </div>
              </div>
            )}
          </div>

          {/* Progress Tracker */}
          <div className="card-box">
            <div className="progress-header">
              <h3 className="card-title">Enrollment Progress</h3>
              <span className="progress-count">
                {samplesCollected} / {samplesRequired} Samples
              </span>
            </div>

            <div className="progress-bar-bg" style={{ height: "10px", margin: "12px 0 16px" }}>
              <div
                className="progress-bar-fill"
                style={{ width: `${Math.min(100, (samplesCollected / samplesRequired) * 100)}%` }}
              ></div>
            </div>

            {isComplete ? (
              <div className="alert-success">
                <CheckCircle size={18} />
                <span>Student face enrollment is complete & active!</span>
              </div>
            ) : (
              <p className="text-muted" style={{ fontSize: "13px" }}>
                Capture 5 diverse poses to train the high-precision vector model.
              </p>
            )}

            {/* Pose Steps Checklist */}
            <div className="pose-steps-list">
              {poses.map((p) => {
                const isCurrent = targetPose === p.id;
                const isCovered = enrollmentStatus?.poses_covered?.includes(p.id);
                return (
                  <div
                    key={p.id}
                    className={`pose-step-item ${isCurrent ? "current" : ""} ${isCovered ? "covered" : ""}`}
                    onClick={() => setTargetPose(p.id)}
                  >
                    <div className="pose-step-icon">
                      {isCovered ? <CheckCircle size={16} /> : <Smile size={16} />}
                    </div>
                    <div className="pose-step-info">
                      <span className="pose-step-name">{p.label}</span>
                      <span className="pose-step-desc">{p.desc}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {samplesCollected > 0 && (
              <button
                type="button"
                className="btn-danger-outline btn-block"
                style={{ marginTop: "16px" }}
                onClick={handleResetEnrollment}
              >
                <RotateCcw size={16} />
                <span>Reset & Re-Enroll</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
