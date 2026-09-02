import React, { useState, useEffect, useRef } from "react";
import { api } from "../api";
import {
  Camera,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  Clock,
  UserCheck,
  RefreshCw,
  Sun,
  Eye,
  AlertCircle
} from "lucide-react";

export const TakeAttendance = () => {
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState("");
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const [autoScan, setAutoScan] = useState(false);

  // Pipeline execution state
  const [pipelineState, setPipelineState] = useState("Ready");
  const [verificationResult, setVerificationResult] = useState(null);
  const [challenge, setChallenge] = useState(null);
  const [challengeTimer, setChallengeTimer] = useState(0);
  const [processing, setProcessing] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const autoScanIntervalRef = useRef(null);

  // Load subjects
  useEffect(() => {
    const fetchSubjects = async () => {
      try {
        const list = await api.getSubjects();
        setSubjects(list);
        if (list.length > 0) {
          setSelectedSubjectId(list[0].id);
        }
      } catch (err) {
        console.error("Failed to fetch subjects:", err);
      }
    };
    fetchSubjects();
  }, []);

  // Request new liveness challenge
  const requestNewChallenge = async () => {
    try {
      const chal = await api.getChallenge();
      setChallenge(chal);
      setChallengeTimer(chal.expires_in_seconds || 15);
    } catch (err) {
      console.error("Failed to get challenge:", err);
    }
  };

  useEffect(() => {
    requestNewChallenge();
  }, [selectedSubjectId]);

  // Challenge countdown timer
  useEffect(() => {
    if (challengeTimer <= 0) return;
    const interval = setInterval(() => {
      setChallengeTimer((prev) => {
        if (prev <= 1) {
          requestNewChallenge();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [challengeTimer]);

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
      setCameraError("Camera permission denied or camera not available.");
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
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
    return canvas.toDataURL("image/jpeg", 0.85);
  };

  const executeAttendanceScan = async () => {
    if (!selectedSubjectId) {
      alert("Please select a subject session.");
      return;
    }
    if (processing) return;

    const b64 = captureFrameBase64();
    if (!b64) return;

    setProcessing(true);

    // Sequence of state badges
    setPipelineState("Detecting face...");
    await new Promise((r) => setTimeout(r, 80));

    setPipelineState("Checking image quality...");
    await new Promise((r) => setTimeout(r, 80));

    setPipelineState("Checking liveness...");
    await new Promise((r) => setTimeout(r, 80));

    setPipelineState("Recognizing...");

    try {
      const res = await api.markAttendance({
        subject_id: parseInt(selectedSubjectId),
        image_base64: b64,
        challenge_token: challenge?.challenge_token,
        challenge_action: challenge?.challenge_type,
      });

      setVerificationResult(res);

      // Map backend status to human-readable state badge
      switch (res.status) {
        case "ATTENDANCE_MARKED":
          setPipelineState("Attendance marked");
          requestNewChallenge();
          break;
        case "ALREADY_MARKED":
          setPipelineState("Already marked");
          break;
        case "UNKNOWN_FACE":
          setPipelineState("Unknown face");
          break;
        case "LOW_CONFIDENCE":
          setPipelineState("Low confidence");
          break;
        case "SPOOF_DETECTED":
          setPipelineState("Spoof detected");
          requestNewChallenge();
          break;
        case "POOR_IMAGE_QUALITY":
          setPipelineState("Poor lighting / quality");
          break;
        case "FACE_NOT_DETECTED":
          setPipelineState("Face not visible");
          break;
        default:
          setPipelineState(res.message);
      }
    } catch (err) {
      setVerificationResult({
        status: "ERROR",
        message: err.message || "Failed to process attendance verification.",
      });
      setPipelineState("Error in verification");
    } finally {
      setProcessing(false);
    }
  };

  // Auto-scan toggle
  useEffect(() => {
    if (autoScan) {
      autoScanIntervalRef.current = setInterval(() => {
        executeAttendanceScan();
      }, 2500);
    } else if (autoScanIntervalRef.current) {
      clearInterval(autoScanIntervalRef.current);
    }
    return () => {
      if (autoScanIntervalRef.current) clearInterval(autoScanIntervalRef.current);
    };
  }, [autoScan, selectedSubjectId, challenge]);

  const selectedSubject = subjects.find((s) => s.id === parseInt(selectedSubjectId));

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2 className="page-title">Attendance Verification Kiosk</h2>
          <p className="page-subtitle">
            7-Step secure AI recognition with active anti-spoofing challenge response
          </p>
        </div>

        <div className="session-select-wrapper">
          <label>Course Session:</label>
          <select
            className="filter-select select-subject-header"
            value={selectedSubjectId}
            onChange={(e) => setSelectedSubjectId(e.target.value)}
          >
            {subjects.map((sub) => (
              <option key={sub.id} value={sub.id}>
                {sub.code} - {sub.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="kiosk-grid">
        {/* Camera Feed & Live Status */}
        <div className="kiosk-camera-card">
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

            {/* Live Pipeline State Badge */}
            <div className={`pipeline-live-badge badge-state-${pipelineState.toLowerCase().replace(/[^a-z0-9]/g, "-")}`}>
              <Sparkles size={16} />
              <span>{pipelineState}</span>
            </div>

            {/* Anti-spoofing challenge banner */}
            {challenge && (
              <div className="kiosk-challenge-banner">
                <div className="challenge-icon-box">
                  <Eye size={20} />
                </div>
                <div className="challenge-text-box">
                  <span className="challenge-title">Active Challenge: {challenge.challenge_type}</span>
                  <span className="challenge-desc">{challenge.instruction}</span>
                </div>
                <div className="challenge-timer-box">
                  <Clock size={16} />
                  <span>{challengeTimer}s</span>
                </div>
              </div>
            )}
          </div>

          <div className="kiosk-action-bar">
            <button
              className="btn-primary btn-large btn-verify"
              onClick={executeAttendanceScan}
              disabled={processing || !cameraActive}
            >
              <Camera size={20} />
              <span>{processing ? "Evaluating Pipeline..." : "Verify & Mark Attendance"}</span>
            </button>

            <button
              className={`btn-auto-scan ${autoScan ? "active" : ""}`}
              onClick={() => setAutoScan(!autoScan)}
            >
              <RefreshCw size={18} className={autoScan ? "spin-icon" : ""} />
              <span>Auto-Scan: {autoScan ? "ON" : "OFF"}</span>
            </button>
          </div>
        </div>

        {/* Verification Result Details */}
        <div className="kiosk-result-sidebar">
          <div className="card-box">
            <h3 className="card-title">Verification Outcome</h3>

            {!verificationResult ? (
              <div className="empty-state-card" style={{ padding: "30px 16px" }}>
                <Camera size={36} />
                <p>Position face within frame and click Verify to begin.</p>
              </div>
            ) : (
              <div className="verification-details">
                <div
                  className={`result-banner ${
                    verificationResult.status === "ATTENDANCE_MARKED"
                      ? "banner-success"
                      : verificationResult.status === "ALREADY_MARKED"
                      ? "banner-info"
                      : "banner-danger"
                  }`}
                >
                  <div className="result-banner-icon">
                    {verificationResult.status === "ATTENDANCE_MARKED" ? (
                      <CheckCircle size={28} />
                    ) : verificationResult.status === "ALREADY_MARKED" ? (
                      <UserCheck size={28} />
                    ) : (
                      <AlertTriangle size={28} />
                    )}
                  </div>
                  <div>
                    <h4 className="result-status-title">{verificationResult.status}</h4>
                    <p className="result-status-msg">{verificationResult.message}</p>
                  </div>
                </div>

                {verificationResult.student_name && (
                  <div className="identified-student-card">
                    <div className="student-card-avatar">
                      {verificationResult.student_name.charAt(0)}
                    </div>
                    <div className="student-card-meta">
                      <h4 className="student-name">{verificationResult.student_name}</h4>
                      <span className="font-mono student-code">{verificationResult.student_code}</span>
                    </div>
                  </div>
                )}

                {/* Score Meters */}
                <div className="score-meters-box">
                  <div className="score-meter-row">
                    <span>Face Match Similarity:</span>
                    <span className="text-bold">{(verificationResult.similarity * 100).toFixed(1)}%</span>
                  </div>
                  <div className="score-meter-row">
                    <span>Spoof Score:</span>
                    <span className={`text-bold ${verificationResult.spoof_score > 0.45 ? "text-danger" : "text-success"}`}>
                      {(verificationResult.spoof_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="score-meter-row">
                    <span>Liveness Verified:</span>
                    <span className={verificationResult.is_live ? "text-success text-bold" : "text-danger text-bold"}>
                      {verificationResult.is_live ? "PASSED" : "FAILED"}
                    </span>
                  </div>
                </div>

                {/* Latency Breakdown */}
                {verificationResult.pipeline_latency_ms && (
                  <div className="latency-breakdown">
                    <span className="latency-title">Latency Breakdown</span>
                    <div className="latency-tags">
                      <span>Quality: {verificationResult.pipeline_latency_ms.quality_check_ms}ms</span>
                      <span>Detection: {verificationResult.pipeline_latency_ms.detection_ms}ms</span>
                      <span>Anti-Spoof: {verificationResult.pipeline_latency_ms.anti_spoof_ms}ms</span>
                      <span>Embedding: {verificationResult.pipeline_latency_ms.embedding_ms}ms</span>
                      <span>Vector Search: {verificationResult.pipeline_latency_ms.vector_search_ms}ms</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="card-box">
            <h3 className="card-title">Session Info</h3>
            <div className="summary-row">
              <span className="text-muted">Subject:</span>
              <span className="text-bold">{selectedSubject?.name || "None"}</span>
            </div>
            <div className="summary-row">
              <span className="text-muted">Course Code:</span>
              <span className="font-mono">{selectedSubject?.code || "-"}</span>
            </div>
            <div className="summary-row">
              <span className="text-muted">Department:</span>
              <span>{selectedSubject?.department || "-"}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
