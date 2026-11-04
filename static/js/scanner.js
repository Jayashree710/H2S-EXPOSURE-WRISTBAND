/**
 * Optical Color Detection & Exposure Assessment Scanner Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const btnStartCamera = document.getElementById('btnStartCamera');
    const btnCaptureSnapshot = document.getElementById('btnCaptureSnapshot');
    const btnStopCamera = document.getElementById('btnStopCamera');
    const fileBadgeUpload = document.getElementById('fileBadgeUpload');
    const dropZone = document.getElementById('dropZone');
    const uploadPreviewBox = document.getElementById('uploadPreviewBox');
    const uploadPreviewImg = document.getElementById('uploadPreviewImg');

    const tempInput = document.getElementById('tempInput');
    const tempDisplay = document.getElementById('tempDisplay');
    const humInput = document.getElementById('humInput');
    const humDisplay = document.getElementById('humDisplay');

    const workerSelect = document.getElementById('workerSelect');
    const selectedBadgeCode = document.getElementById('selectedBadgeCode');
    const selectedBadgeValidity = document.getElementById('selectedBadgeValidity');

    const resultCard = document.getElementById('resultCard');
    const scanStatusBadge = document.getElementById('scanStatusBadge');
    const detectedColorBox = document.getElementById('detectedColorBox');
    const detectedRgbText = document.getElementById('detectedRgbText');
    const detectedLabText = document.getElementById('detectedLabText');
    const rawEstimateValue = document.getElementById('rawEstimateValue');
    const envCorrectionValue = document.getElementById('envCorrectionValue');
    const correctedEstimateValue = document.getElementById('correctedEstimateValue');
    const confidenceValue = document.getElementById('confidenceValue');
    const riskSeverityText = document.getElementById('riskSeverityText');

    const btnSaveEntry = document.getElementById('btnSaveEntry');
    const btnSaveExit = document.getElementById('btnSaveExit');
    const simFeedButtons = document.querySelectorAll('.btn-sim-feed');

    // Current State Cache
    let currentExtractedColor = {
        r: 34,
        g: 197,
        b: 94,
        lab: { l: 70.5, a: -60.2, b: 41.5 }
    };
    let currentRawExposure = 0.0;
    let currentConfidence = 0.98;

    // --- 1. Camera Control ---
    if (btnStartCamera) {
        btnStartCamera.addEventListener('click', () => {
            window.CameraManager.start(
                () => {
                    btnStartCamera.disabled = true;
                    btnCaptureSnapshot.disabled = false;
                    btnStopCamera.disabled = false;
                    window.H2Sense.showNotification("Camera activated. Align sensor well within reticle.", "info");
                },
                (errMsg) => {
                    window.H2Sense.showNotification(errMsg, "error");
                }
            );
        });

        btnCaptureSnapshot.addEventListener('click', () => {
            try {
                const base64Img = window.CameraManager.captureSnapshot();
                processImageBase64(base64Img);
            } catch (err) {
                window.H2Sense.showNotification(err.message, "error");
            }
        });

        btnStopCamera.addEventListener('click', () => {
            window.CameraManager.stop();
            btnStartCamera.disabled = false;
            btnCaptureSnapshot.disabled = true;
            btnStopCamera.disabled = true;
        });
    }

    // --- 2. Image Upload Handling ---
    if (fileBadgeUpload) {
        fileBadgeUpload.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                handleFileUpload(e.target.files[0]);
            }
        });

        // Drag & Drop
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = 'var(--primary)';
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.style.borderColor = 'rgba(255, 255, 255, 0.2)';
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = 'rgba(255, 255, 255, 0.2)';
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                handleFileUpload(e.dataTransfer.files[0]);
            }
        });
    }

    function handleFileUpload(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            uploadPreviewImg.src = e.target.result;
            uploadPreviewBox.style.display = 'block';
            processImageBase64(e.target.result);
        };
        reader.readAsDataURL(file);
    }

    // --- 3. Processing Pipeline via REST API ---
    async function processImageBase64(base64Data) {
        scanStatusBadge.textContent = "PROCESSING...";
        scanStatusBadge.className = "badge bg-info text-dark";

        try {
            const resp = await fetch('/api/detect-color', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: base64Data })
            });

            const data = await resp.json();
            if (!data.success) {
                throw new Error(data.error || "Failed to process image with Computer Vision.");
            }

            currentExtractedColor = data.color;
            await evaluateExposure(currentExtractedColor);
            window.H2Sense.showNotification("Computer Vision extracted sensor color successfully.", "success");
        } catch (err) {
            console.error(err);
            window.H2Sense.showNotification(err.message, "error");
            scanStatusBadge.textContent = "CV ERROR";
            scanStatusBadge.className = "badge-critical";
        }
    }

    async function evaluateExposure(colorData) {
        const temp = parseFloat(tempInput.value);
        const hum = parseFloat(humInput.value);

        try {
            const resp = await fetch('/api/calculate-exposure', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    color: colorData,
                    temperature: temp,
                    humidity: hum
                })
            });

            const result = await resp.json();
            if (!result.success) {
                throw new Error(result.error || "Failed to evaluate exposure.");
            }

            currentRawExposure = result.raw_exposure;
            currentConfidence = result.confidence;

            // Update UI Card
            detectedColorBox.style.backgroundColor = `rgb(${colorData.r}, ${colorData.g}, ${colorData.b})`;
            detectedColorBox.style.boxShadow = `0 0 20px ${result.classification.color_code}`;
            detectedRgbText.textContent = `RGB(${colorData.r}, ${colorData.g}, ${colorData.b})`;
            detectedLabText.textContent = `L* ${colorData.lab.l.toFixed(1)}  a* ${colorData.lab.a.toFixed(1)}  b* ${colorData.lab.b.toFixed(1)}`;

            rawEstimateValue.textContent = result.raw_exposure.toFixed(1);
            
            const envSign = result.environmental_correction >= 0 ? '+' : '';
            envCorrectionValue.textContent = `${envSign}${result.environmental_correction.toFixed(1)}`;
            correctedEstimateValue.textContent = result.corrected_exposure.toFixed(1);

            confidenceValue.textContent = `${Math.round(result.confidence * 100)}%`;
            riskSeverityText.textContent = `${result.status}: ${result.classification.display_message}`;
            riskSeverityText.className = `${result.classification.css_class} fw-bold small`;

            scanStatusBadge.textContent = `${result.status} DETECTED`;
            scanStatusBadge.className = result.classification.badge_class;

        } catch (err) {
            console.error(err);
            window.H2Sense.showNotification(err.message, "error");
        }
    }

    // --- 4. Environmental Sliders Real-time Recalculation ---
    tempInput.addEventListener('input', (e) => {
        tempDisplay.textContent = `${parseFloat(e.target.value).toFixed(1)} °C`;
        evaluateExposure(currentExtractedColor);
    });

    humInput.addEventListener('input', (e) => {
        humDisplay.textContent = `${parseFloat(e.target.value).toFixed(1)} %`;
        evaluateExposure(currentExtractedColor);
    });

    // --- 5. Simulator Bridge Buttons ---
    simFeedButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const r = parseInt(btn.dataset.r);
            const g = parseInt(btn.dataset.g);
            const b = parseInt(btn.dataset.b);
            loadDirectRgb(r, g, b);
        });
    });

    async function loadDirectRgb(r, g, b) {
        scanStatusBadge.textContent = "EVALUATING...";
        try {
            const resp = await fetch('/api/detect-color', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ r, g, b })
            });

            const data = await resp.json();
            if (data.success) {
                currentExtractedColor = data.color;
                await evaluateExposure(currentExtractedColor);
                window.H2Sense.showNotification(`Loaded simulated sensor response RGB(${r}, ${g}, ${b}).`, "info");
            }
        } catch (err) {
            console.error(err);
        }
    }

    // --- 6. Worker Selection Listener ---
    function updateSelectedWorkerInfo() {
        const opt = workerSelect.options[workerSelect.selectedIndex];
        if (opt) {
            selectedBadgeCode.textContent = opt.dataset.badgeCode || 'NONE';
            const validity = opt.dataset.validity || 'VALID';
            if (validity === 'VALID') {
                selectedBadgeValidity.innerHTML = '<span class="badge-safe">VALID</span>';
            } else if (validity === 'NEAR EXPIRY') {
                selectedBadgeValidity.innerHTML = '<span class="badge-caution">NEAR EXPIRY</span>';
            } else {
                selectedBadgeValidity.innerHTML = '<span class="badge-critical">EXPIRED</span>';
            }
        }
    }

    workerSelect.addEventListener('change', updateSelectedWorkerInfo);
    updateSelectedWorkerInfo();

    // --- 7. Save Scan Record (ENTRY or EXIT) ---
    async function saveScan(scanType) {
        const opt = workerSelect.options[workerSelect.selectedIndex];
        if (!opt) {
            window.H2Sense.showNotification("Please select an operator first.", "error");
            return;
        }

        const workerId = opt.value;
        const badgeId = opt.dataset.badgeId;
        const temp = parseFloat(tempInput.value);
        const hum = parseFloat(humInput.value);

        const payload = {
            worker_id: workerId,
            badge_id: badgeId,
            scan_type: scanType,
            color: currentExtractedColor,
            temperature: temp,
            humidity: hum,
            raw_exposure: currentRawExposure,
            confidence: currentConfidence
        };

        try {
            const resp = await fetch('/api/record-scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const res = await resp.json();
            if (!res.success) {
                throw new Error(res.error || "Failed to record scan.");
            }

            const rec = res.data.record;
            let msg = `${scanType} recorded: ${rec.corrected_exposure} ppm. Cumulative total: ${rec.cumulative_exposure} ppm.`;
            if (res.data.warning) {
                msg += ` [Note: ${res.data.warning}]`;
            }

            window.H2Sense.showNotification(msg, scanType === 'EXIT' && rec.shift_exposure > 50 ? 'warning' : 'success');

        } catch (err) {
            console.error(err);
            window.H2Sense.showNotification(err.message, "error");
        }
    }

    if (btnSaveEntry) {
        btnSaveEntry.addEventListener('click', () => saveScan('ENTRY'));
    }

    if (btnSaveExit) {
        btnSaveExit.addEventListener('click', () => saveScan('EXIT'));
    }

    // --- 8. Check Prefilled Data from Simulator ---
    if (window.PREFILL_DATA && window.PREFILL_DATA.r) {
        const r = parseInt(window.PREFILL_DATA.r);
        const g = parseInt(window.PREFILL_DATA.g);
        const b = parseInt(window.PREFILL_DATA.b);
        loadDirectRgb(r, g, b);
    } else {
        // Evaluate default green
        evaluateExposure(currentExtractedColor);
    }
});
