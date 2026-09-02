import React, { useState, useEffect } from "react";
import { api } from "../api";
import { Sliders, Save, CheckCircle, AlertCircle, RefreshCw } from "lucide-react";

export const SettingsPage = () => {
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState({ type: "", text: "" });

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const data = await api.getSettings();
      setSettings(data);
    } catch (err) {
      console.error("Failed to fetch settings:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleChange = (key, val) => {
    setSettings((prev) => ({ ...prev, [key]: val }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMsg({ type: "", text: "" });
    try {
      await api.updateSettings(settings);
      setMsg({ type: "success", text: "AI & Pipeline thresholds updated successfully!" });
    } catch (err) {
      setMsg({ type: "error", text: err.message || "Failed to update settings." });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="loading-state">Loading AI thresholds...</div>;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2 className="page-title">AI Engine & Pipeline Thresholds</h2>
          <p className="page-subtitle">Configure real-time computer vision thresholds, anti-spoofing sensitivity, and quality filters</p>
        </div>
      </div>

      {msg.text && (
        <div className={msg.type === "success" ? "alert-success" : "alert-error"} style={{ marginBottom: "20px" }}>
          {msg.type === "success" ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
          <span>{msg.text}</span>
        </div>
      )}

      <form onSubmit={handleSave}>
        <div className="settings-grid">
          {/* Face Recognition Threshold */}
          <div className="card-box">
            <div className="setting-header">
              <span className="setting-title">Face Match Threshold (Cosine Similarity)</span>
              <span className="font-mono text-bold text-highlight">{settings.FACE_MATCH_THRESHOLD}</span>
            </div>
            <p className="setting-desc">
              Minimum cosine similarity required to confirm student identity. Higher values require stricter visual similarity.
            </p>
            <input
              type="range"
              min="0.40"
              max="0.95"
              step="0.01"
              className="slider-input"
              value={settings.FACE_MATCH_THRESHOLD || 0.65}
              onChange={(e) => handleChange("FACE_MATCH_THRESHOLD", parseFloat(e.target.value))}
            />
          </div>

          {/* Low-Light Enhancement Trigger */}
          <div className="card-box">
            <div className="setting-header">
              <span className="setting-title">Low-Light Luminance Threshold</span>
              <span className="font-mono text-bold text-highlight">{settings.LOW_LIGHT_THRESHOLD}</span>
            </div>
            <p className="setting-desc">
              Luminance value (0-255) below which adaptive CLAHE and Gamma enhancement are automatically activated.
            </p>
            <input
              type="range"
              min="20"
              max="90"
              step="1"
              className="slider-input"
              value={settings.LOW_LIGHT_THRESHOLD || 45}
              onChange={(e) => handleChange("LOW_LIGHT_THRESHOLD", parseFloat(e.target.value))}
            />
          </div>

          {/* Blur Sharpness Threshold */}
          <div className="card-box">
            <div className="setting-header">
              <span className="setting-title">Blur / Sharpness Threshold (Laplacian)</span>
              <span className="font-mono text-bold text-highlight">{settings.BLUR_THRESHOLD}</span>
            </div>
            <p className="setting-desc">
              Minimum Laplacian variance required for an image frame. Frames below this threshold are rejected as blurred.
            </p>
            <input
              type="range"
              min="20"
              max="150"
              step="5"
              className="slider-input"
              value={settings.BLUR_THRESHOLD || 40}
              onChange={(e) => handleChange("BLUR_THRESHOLD", parseFloat(e.target.value))}
            />
          </div>

          {/* Anti-Spoofing Sensitivity */}
          <div className="card-box">
            <div className="setting-header">
              <span className="setting-title">Max Allowable Spoof Probability</span>
              <span className="font-mono text-bold text-highlight">{settings.SPOOF_THRESHOLD}</span>
            </div>
            <p className="setting-desc">
              Upper bound threshold for LBP texture and Fourier frequency moiré spoof detection. Frames with higher spoof probability are rejected.
            </p>
            <input
              type="range"
              min="0.20"
              max="0.80"
              step="0.01"
              className="slider-input"
              value={settings.SPOOF_THRESHOLD || 0.45}
              onChange={(e) => handleChange("SPOOF_THRESHOLD", parseFloat(e.target.value))}
            />
          </div>

          {/* Enrollment Samples Required */}
          <div className="card-box">
            <div className="setting-header">
              <span className="setting-title">Enrollment Required Samples</span>
              <span className="font-mono text-bold text-highlight">{settings.ENROLLMENT_MIN_SAMPLES}</span>
            </div>
            <p className="setting-desc">
              Number of distinct high-quality facial poses required to complete student face enrollment.
            </p>
            <input
              type="number"
              min="3"
              max="15"
              className="filter-select"
              style={{ width: "100%", marginTop: "8px" }}
              value={settings.ENROLLMENT_MIN_SAMPLES || 5}
              onChange={(e) => handleChange("ENROLLMENT_MIN_SAMPLES", parseInt(e.target.value))}
            />
          </div>
        </div>

        <div style={{ marginTop: "24px", display: "flex", gap: "12px" }}>
          <button type="submit" className="btn-primary" disabled={saving}>
            <Save size={18} />
            <span>{saving ? "Updating Thresholds..." : "Save AI Configuration"}</span>
          </button>
          <button type="button" className="btn-secondary" onClick={fetchSettings}>
            <RefreshCw size={18} />
            <span>Reset to Saved</span>
          </button>
        </div>
      </form>
    </div>
  );
};
