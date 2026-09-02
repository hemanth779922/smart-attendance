# AI & Computer Vision Pipeline

## Pipeline Execution Flow
For every camera frame submitted for verification, the system executes an automated 7-step pipeline:

```
Camera Frame
    │
    ▼ [1. Quality Assessment]
Brightness, Laplacian Blur Score, Contrast, Face Size Check
    │  ↳ (Fails? -> POOR_IMAGE_QUALITY with actionable guidance)
    ▼ [2. Low-Light Processing]
Mean Luminance < 45.0?
    │  ↳ YES: Selective LAB/YCrCb CLAHE + Adaptive Gamma (gamma < 1.0) + Bilateral Denoising
    │  ↳ NO:  Pass original frame unaltered (avoids over-enhancement)
    ▼ [3. Face Detection & Alignment]
OpenCV YuNet Deep Neural Network Detector
    │  ↳ Detects bounding box & 5 facial landmarks (eyes, nose, mouth)
    │  ↳ Applies 2D Affine transformation to horizontally level eyes
    ▼ [4. Multi-Signal Anti-Spoofing]
    │  ↳ Micro-texture: LBP (Local Binary Pattern) histogram entropy analysis
    │  ↳ Frequency: 2D FFT magnitude spectrum to detect display screen moiré
    │  ↳ Temporal motion: Inter-frame pixel dynamics
    │  ↳ Challenge-Response: Randomized action verification (BLINK, TURN_LEFT, TURN_RIGHT, SMILE)
    │  ↳ (Fails? -> SPOOF_DETECTED with rejection score)
    ▼ [5. Face Embedding Generation]
SFace Deep Neural Network / 128-dimensional L2-normalized feature vector
    │  ↳ ||v||_2 = 1.0 (Unit vector where dot product = cosine similarity)
    ▼ [6. pgvector Nearest-Neighbor Search]
SELECT student_id, (1 - (embedding <=> query_vec)) AS similarity
FROM face_embeddings WHERE is_active = true
ORDER BY embedding <=> query_vec LIMIT 1;
    │  ↳ (Similarity < FACE_MATCH_THRESHOLD? -> UNKNOWN_FACE / LOW_CONFIDENCE)
    ▼ [7. Business & Attendance Validation]
Student Active Check + Subject Enrollment Check + DB Unique Constraint
    │  ↳ ALREADY_MARKED if record exists for (student_id, subject_id, session_date)
    │  ↳ ATTENDANCE_MARKED with atomic database transaction
```

---

## 1. Low-Light Face Recognition Pipeline
Located in `app/ai/low_light.py`.

### Detection:
- Analyzes luminance channel $Y$ in YCrCb color space.
- Calculates mean luminance $\mu_Y$ and shadow histogram percentile (percentage of pixels with intensity $< 30$).
- If $\mu_Y < \text{LOW\_LIGHT\_THRESHOLD}$ (default 45.0) or shadow clip $> 15\%$, low-light enhancement is triggered.

### Adaptive Enhancement:
1. **CLAHE**: Applied to luminance channel with `clipLimit=2.5`, `tileGridSize=(8,8)` to boost local contrast in dark facial features without washing out bright regions.
2. **Adaptive Gamma Correction**:
   $$\gamma = \text{clip}\left(0.4 + \frac{\mu_Y}{100.0} \times 0.4, 0.45, 0.85\right)$$
   Lookup Table: $I_{\text{out}} = \left(\frac{I_{\text{in}}}{255}\right)^\gamma \times 255$.
3. **Bilateral Filtering**: Preserves sharp facial boundaries while suppressing sensor noise in dark patches.
4. **Identity Preservation**: When lighting is already sufficient, enhancement is skipped entirely, preserving true facial features.

---

## 2. Multi-Signal Anti-Spoofing Architecture
Located in `app/ai/anti_spoofing.py`.

> [!NOTE]
> No anti-spoofing system can claim 100% invulnerability. The Smart Attendance System implements defense-in-depth across multiple independent physiological and physical signals.

### Signals Evaluated:
1. **Micro-Texture LBP Analysis**:
   - Computes Local Binary Patterns across $3 \times 3$ pixel neighborhoods.
   - Calculates the Shannon entropy of the LBP distribution:
     $$H = -\sum_i p_i \log_2(p_i)$$
   - Real human skin micro-texture exhibits rich entropy ($5.5 \le H \le 7.2$), while digital displays and printed media show flattened histograms or artificial spikes.
2. **Frequency Domain Fourier Transform (2D FFT)**:
   - Evaluates high-frequency spectral energy.
   - Digital screens (phones, tablets, laptops) produce periodic harmonic peaks and moiré patterns that show up as distinct high-frequency spikes.
3. **Temporal Motion Tracking**:
   - Detects inter-frame micro-motion. Static photographs or looped frozen video streams are identified when motion variance $< 0.3$.
4. **Interactive Challenge-Response**:
   - Server issues a single-use cryptographically random challenge (`BLINK`, `TURN_LEFT`, `TURN_RIGHT`, `SMILE`) with a 15-second expiration token.
   - Requires dynamic user action before marking attendance.

---

## 3. Camera Quality Assessment
Located in `app/ai/quality_assessment.py`.
Measures:
- **Sharpness / Blur**: Computed via Laplacian variance $\sigma^2(\nabla^2 I)$. If $\sigma^2 < \text{BLUR\_THRESHOLD}$ (40.0), rejects with `"Hold the camera steady"`.
- **Brightness**: If mean luminance $< 22.5$, rejects with `"Move to a brighter area"`. If $> 230$, rejects with `"Avoid direct light on camera"`.
- **Contrast**: Grayscale standard deviation. If $< 25.0$, rejects with `"Face not clear"`.
- **Face Size**: Ensures bounding box size $\ge 80\text{px}$. If smaller, rejects with `"Move closer to the camera"`.
