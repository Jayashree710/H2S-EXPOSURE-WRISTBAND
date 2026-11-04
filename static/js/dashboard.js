/**
 * Industrial Exposure Admin Dashboard Controller
 * Integrates Chart.js 4.x with live REST telemetry updates.
 * Styled for Clinical Industrial Light Theme.
 */

document.addEventListener('DOMContentLoaded', () => {
    let trendChartInstance = null;
    let riskChartInstance = null;
    let workerChartInstance = null;

    const btnRefresh = document.getElementById('btnRefreshStats');

    async function fetchAndUpdateDashboard() {
        try {
            const resp = await fetch('/api/dashboard/stats');
            const data = await resp.json();

            if (!data.success) {
                console.error("Failed to load dashboard statistics.");
                return;
            }

            // 1. Update KPI Card Values
            const activeElem = document.getElementById('statActiveWorkers');
            const todayElem = document.getElementById('statTodayScans');
            const highElem = document.getElementById('statHighRisk');
            const totalElem = document.getElementById('statTotalExposure');

            if (activeElem) activeElem.textContent = data.metrics.active_workers;
            if (todayElem) todayElem.textContent = data.metrics.today_scans;
            if (highElem) highElem.textContent = data.metrics.high_risk_count;
            if (totalElem) totalElem.innerHTML = `${data.metrics.total_cumulative_exposure} <span class="fs-6 text-muted">units</span>`;

            // 2. Render 7-Day Trend Chart
            renderTrendChart(data.trend_7day);

            // 3. Render Risk Distribution Doughnut
            renderRiskChart(data.risk_distribution);

            // 4. Render Worker Cumulative Comparison Bar Chart
            renderWorkerChart(data.worker_comparison);

        } catch (err) {
            console.error("Dashboard sync error:", err);
        }
    }

    function renderTrendChart(trendData) {
        const ctx = document.getElementById('trendChart');
        if (!ctx) return;

        if (trendChartInstance) {
            trendChartInstance.destroy();
        }

        trendChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: trendData.labels,
                datasets: [{
                    label: 'Avg Exposure (ppm)',
                    data: trendData.values,
                    borderColor: '#0284c7',
                    backgroundColor: 'rgba(2, 132, 199, 0.12)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.35,
                    pointBackgroundColor: '#0284c7',
                    pointBorderColor: '#ffffff',
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#0f172a',
                        borderColor: '#cbd5e1',
                        borderWidth: 1,
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        titleFont: { size: 12 },
                        bodyFont: { size: 12 }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(0, 0, 0, 0.05)' },
                        ticks: { color: '#475569', font: { size: 11, weight: '500' } }
                    },
                    y: {
                        grid: { color: 'rgba(0, 0, 0, 0.05)' },
                        ticks: { color: '#475569', font: { size: 11, weight: '500' } },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    function renderRiskChart(riskDist) {
        const ctx = document.getElementById('riskDoughnutChart');
        if (!ctx) return;

        if (riskChartInstance) {
            riskChartInstance.destroy();
        }

        riskChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Safe (< 25)', 'Caution (25-50)', 'High (50-100)', 'Critical (> 100)'],
                datasets: [{
                    data: [
                        riskDist.SAFE || 0,
                        riskDist.CAUTION || 0,
                        riskDist.HIGH || 0,
                        riskDist.CRITICAL || 0
                    ],
                    backgroundColor: [
                        '#16a34a',
                        '#d97706',
                        '#ea580c',
                        '#dc2626'
                    ],
                    borderColor: '#ffffff',
                    borderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '68%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#334155',
                            boxWidth: 12,
                            font: { size: 11, weight: '500' }
                        }
                    }
                }
            }
        });
    }

    function renderWorkerChart(compData) {
        const ctx = document.getElementById('workerBarChart');
        if (!ctx) return;

        if (workerChartInstance) {
            workerChartInstance.destroy();
        }

        workerChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: compData.labels,
                datasets: [{
                    label: 'Cumulative Exposure (ppm)',
                    data: compData.values,
                    backgroundColor: compData.values.map(v => {
                        if (v > 100) return '#dc2626';
                        if (v > 50) return '#ea580c';
                        if (v > 25) return '#d97706';
                        return '#16a34a';
                    }),
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#475569', font: { size: 11, weight: '500' } }
                    },
                    y: {
                        grid: { color: 'rgba(0, 0, 0, 0.05)' },
                        ticks: { color: '#475569', font: { size: 11, weight: '500' } },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    if (btnRefresh) {
        btnRefresh.addEventListener('click', () => {
            fetchAndUpdateDashboard();
            window.H2Sense.showNotification("Telemetry synchronized with MySQL database.", "info");
        });
    }

    // Initial load
    fetchAndUpdateDashboard();
});
