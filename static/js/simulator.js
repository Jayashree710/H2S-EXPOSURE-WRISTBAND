/**
 * Digital H₂S Sensor Simulator Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    const points = window.CALIBRATION_POINTS || [
        { exposure_value: 0.0, r: 34, g: 197, b: 94, lab_l: 70.5, lab_a: -60.2, lab_b: 41.5 },
        { exposure_value: 10.0, r: 95, g: 207, b: 72, lab_l: 74.2, lab_a: -49.6, lab_b: 53.1 },
        { exposure_value: 25.0, r: 163, g: 230, b: 53, lab_l: 83.1, lab_a: -38.4, lab_b: 68.2 },
        { exposure_value: 50.0, r: 234, g: 179, b: 8, lab_l: 75.3, lab_a: 6.2, lab_b: 76.4 },
        { exposure_value: 75.0, r: 249, g: 115, b: 22, lab_l: 63.1, lab_a: 48.2, lab_b: 65.5 },
        { exposure_value: 100.0, r: 239, g: 68, b: 68, lab_l: 53.2, lab_a: 67.1, lab_b: 48.8 },
        { exposure_value: 150.0, r: 185, g: 28, b: 28, lab_l: 37.4, lab_a: 61.5, lab_b: 43.2 },
        { exposure_value: 200.0, r: 127, g: 29, b: 29, lab_l: 26.8, lab_a: 44.9, lab_b: 28.6 }
    ];

    // DOM Elements
    const sensorColorArea = document.getElementById('sensorColorArea');
    const exposureDisplay = document.getElementById('exposureDisplay');
    const statusDisplay = document.getElementById('statusDisplay');
    const displayBadge = document.getElementById('displayBadge');
    const rgbDisplay = document.getElementById('rgbDisplay');
    const hexDisplay = document.getElementById('hexDisplay');
    const labDisplay = document.getElementById('labDisplay');
    const slider = document.getElementById('continuousSlider');
    const sliderValuePill = document.getElementById('sliderValuePill');
    const presetButtons = document.querySelectorAll('.btn-preset');
    const btnSendToScanner = document.getElementById('btnSendToScanner');
    const btnDownloadSwatch = document.getElementById('btnDownloadSwatch');

    let currentExposure = 0;
    let currentColor = { r: 34, g: 197, b: 94 };

    function rgbToHex(r, g, b) {
        return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
    }

    function interpolateColor(expVal) {
        // Sort points by exposure
        const sorted = points.slice().sort((a, b) => a.exposure_value - b.exposure_value);

        if (expVal <= sorted[0].exposure_value) {
            const p = sorted[0];
            return { r: p.r, g: p.g, b: p.b, l: p.lab_l, a: p.lab_a, b_val: p.lab_b };
        }
        if (expVal >= sorted[sorted.length - 1].exposure_value) {
            const p = sorted[sorted.length - 1];
            return { r: p.r, g: p.g, b: p.b, l: p.lab_l, a: p.lab_a, b_val: p.lab_b };
        }

        for (let i = 0; i < sorted.length - 1; i++) {
            const p1 = sorted[i];
            const p2 = sorted[i + 1];
            if (expVal >= p1.exposure_value && expVal <= p2.exposure_value) {
                const range = p2.exposure_value - p1.exposure_value;
                const ratio = range === 0 ? 0 : (expVal - p1.exposure_value) / range;
                
                const r = Math.round(p1.r + (p2.r - p1.r) * ratio);
                const g = Math.round(p1.g + (p2.g - p1.g) * ratio);
                const b = Math.round(p1.b + (p2.b - p1.b) * ratio);
                const l = (p1.lab_l + (p2.lab_l - p1.lab_l) * ratio).toFixed(1);
                const a = (p1.lab_a + (p2.lab_a - p1.lab_a) * ratio).toFixed(1);
                const b_val = (p1.lab_b + (p2.lab_b - p1.lab_b) * ratio).toFixed(1);

                return { r, g, b, l, a, b_val };
            }
        }
    }

    function getRiskInfo(expVal) {
        if (expVal <= 25) {
            return { status: 'SAFE', label: 'SAFE / BASELINE', color: 'var(--color-safe)', glow: 'rgba(34, 197, 94, 0.5)', badgeClass: 'badge-safe' };
        } else if (expVal <= 50) {
            return { status: 'CAUTION', label: 'CAUTION / ELEVATED', color: 'var(--color-caution)', glow: 'rgba(234, 179, 8, 0.5)', badgeClass: 'badge-caution' };
        } else if (expVal <= 100) {
            return { status: 'HIGH', label: 'HIGH RISK EXPOSURE', color: 'var(--color-high)', glow: 'rgba(249, 115, 22, 0.5)', badgeClass: 'badge-high' };
        } else {
            return { status: 'CRITICAL', label: 'CRITICAL EVACUATION LEVEL', color: 'var(--color-critical)', glow: 'rgba(239, 68, 68, 0.6)', badgeClass: 'badge-critical' };
        }
    }

    function updateSimulation(expVal) {
        currentExposure = Number(expVal);
        const color = interpolateColor(currentExposure);
        currentColor = color;
        const hex = rgbToHex(color.r, color.g, color.b);
        const risk = getRiskInfo(currentExposure);

        // Update DOM
        sensorColorArea.style.backgroundColor = `rgb(${color.r}, ${color.g}, ${color.b})`;
        sensorColorArea.style.setProperty('--current-glow', risk.glow);
        exposureDisplay.innerHTML = `${currentExposure.toFixed(1)} <span class="fs-5 text-muted">units</span>`;
        statusDisplay.textContent = risk.label;
        statusDisplay.style.color = risk.color;

        displayBadge.textContent = risk.status;
        displayBadge.className = risk.badgeClass;

        rgbDisplay.textContent = `rgb(${color.r}, ${color.g}, ${color.b})`;
        hexDisplay.textContent = hex;
        labDisplay.textContent = `L: ${color.l}  a: ${color.a}  b: ${color.b_val}`;

        sliderValuePill.textContent = `${currentExposure} ppm`;
        slider.value = currentExposure;
    }

    // Preset button event listeners
    presetButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            presetButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const exp = parseFloat(btn.dataset.exp);
            updateSimulation(exp);
        });
    });

    // Slider event listener
    slider.addEventListener('input', (e) => {
        presetButtons.forEach(b => b.classList.remove('active'));
        updateSimulation(e.target.value);
    });

    // Send to Scanner Workstation bridge
    if (btnSendToScanner) {
        btnSendToScanner.addEventListener('click', () => {
            const url = `/scanner?r=${currentColor.r}&g=${currentColor.g}&b=${currentColor.b}&exposure=${currentExposure}`;
            window.location.href = url;
        });
    }

    // Save/Download simulated test badge image
    if (btnDownloadSwatch) {
        btnDownloadSwatch.addEventListener('click', () => {
            const canvas = document.createElement('canvas');
            canvas.width = 400;
            canvas.height = 400;
            const ctx = canvas.getContext('2d');

            // Draw industrial badge card background
            ctx.fillStyle = '#0f172a';
            ctx.fillRect(0, 0, 400, 400);

            // Draw outer border & badge header
            ctx.strokeStyle = '#38bdf8';
            ctx.lineWidth = 4;
            ctx.strokeRect(10, 10, 380, 380);

            ctx.fillStyle = '#f8fafc';
            ctx.font = 'bold 20px sans-serif';
            ctx.fillText('H2SENSE OPTICAL BADGE', 60, 50);

            // Center sensor well
            ctx.beginPath();
            ctx.arc(200, 210, 100, 0, Math.PI * 2);
            ctx.fillStyle = `rgb(${currentColor.r}, ${currentColor.g}, ${currentColor.b})`;
            ctx.fill();
            ctx.lineWidth = 6;
            ctx.strokeStyle = '#334155';
            ctx.stroke();

            // Footnote
            ctx.fillStyle = '#94a3b8';
            ctx.font = '14px monospace';
            ctx.fillText(`Simulated: ${currentExposure} ppm`, 110, 360);

            const link = document.createElement('a');
            link.download = `h2sense_simulated_${currentExposure}units.png`;
            link.href = canvas.toDataURL('image/png');
            link.click();
            window.H2Sense.showNotification(`Saved test image for ${currentExposure} ppm.`, 'success');
        });
    }

    // Initialize with 0 ppm
    updateSimulation(0);
});
