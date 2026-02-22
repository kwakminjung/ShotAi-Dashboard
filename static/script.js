// Configuration
const MAX_DATA_POINTS = 60; // Keep last 60 seconds
const WS_URL = `ws://${window.location.host}/ws`;
const TRITON_API_URL = '/api/triton/metrics/latest';
const INFERENCE_API_URL = '/api/inference/latest';

// Global Chart Instances
let charts = {};

// Common Chart Options (Grafana Style)
const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 0 }, // Disable animation for real-time performance
    interaction: {
        mode: 'index',
        intersect: false,
    },
    plugins: {
        legend: {
            display: true,
            labels: { color: '#ccccdc', boxWidth: 10, font: { size: 10 } }
        },
        tooltip: {
            backgroundColor: '#111217',
            titleColor: '#fff',
            bodyColor: '#ccccdc',
            borderColor: '#2c3235',
            borderWidth: 1
        }
    },
    scales: {
        x: {
            display: false, // Hide X-axis labels for clean look
            grid: { display: false }
        },
        y: {
            grid: { color: '#2c3235' },
            ticks: { color: '#8e8e8e', font: { size: 10 } },
            beginAtZero: true
        }
    },
    elements: {
        point: { radius: 0, hoverRadius: 4 }, // Hide points, show on hover
        line: { tension: 0.3, borderWidth: 2 } // Smooth curves
    }
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    connectWebSocket();
    startTritonPolling();
    startInferencePolling();
});

function initCharts() {
    charts.sbcCpu = createChart('sbcCpuChart', ['CPU %'], ['#73bf69']);
    charts.sbcTemp = createChart('sbcTempChart', ['Temp °C'], ['#ff9900']);
    charts.sbcMem = createChart('sbcMemChart', ['Mem %'], ['#5794f2']);
    charts.sbcNet = createChart('sbcNetChart', ['RX (Mbps)', 'TX (Mbps)'], ['#fade2a', '#5794f2']);
    charts.sbcLatency = createChart('sbcLatencyChart', ['RTT (ms)', 'Jitter (ms)'], ['#f2495c', '#8e8e8e']);
    charts.sbcGpu = createChart('sbcGpuChart', ['GPU %'], ['#73bf69']);
    charts.sbcDisk = createChart('sbcDiskChart', ['Disk (%)'], ['#fade2a']);

    charts.tritonUtil = createChart('tritonUtilChart', ['GPU Util %', 'CPU Util %'], ['#73bf69', '#5794f2']);
    charts.tritonMem = createChart('tritonMemChart', ['VRAM %', 'RAM %'], ['#73bf69', '#5794f2']);
    charts.tritonPower = createChart('tritonPowerChart', ['GPU Power (W)'], ['#ff9900']);
}

function createChart(canvasId, labels, colors) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    const datasets = labels.map((label, index) => ({
        label: label,
        data: [],
        borderColor: colors[index],
        backgroundColor: colors[index] + '20', // transparent fill
        fill: true,
        borderWidth: 2
    }));

    return new Chart(ctx, {
        type: 'line',
        data: { labels: [], datasets: datasets },
        options: commonOptions
    });
}

// --- Data Management ---
function updateChartData(chart, timestamp, newValues) {
    const data = chart.data;
    
    // Add new label (timestamp)
    const timeStr = new Date(timestamp).toLocaleTimeString('ko-KR', {hour12: false});
    data.labels.push(timeStr);
    
    // Add new data points
    newValues.forEach((val, idx) => {
        if (data.datasets[idx]) {
            data.datasets[idx].data.push(val);
        }
    });

    // Shift if too many points
    if (data.labels.length > MAX_DATA_POINTS) {
        data.labels.shift();
        data.datasets.forEach(ds => ds.data.shift());
    }

    chart.update('none'); // Update without animation
}

// --- WebSocket for SBC Metrics ---
function connectWebSocket() {
    const statusEl = document.getElementById('connection-status');
    const socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        console.log("WS Connected");
        statusEl.textContent = "Connected (Live)";
        statusEl.className = "status-badge connected";
    };

    socket.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            
            // Only handle "monitor" type data
            if (msg.type === 'monitor' && msg.content) {
                processSbcData(msg.content, msg.timestamp);
            }
        } catch (e) {
            console.error("WS Parse Error", e);
        }
    };

    socket.onclose = () => {
        statusEl.textContent = "Disconnected";
        statusEl.className = "status-badge disconnected";
        setTimeout(connectWebSocket, 3000); // Reconnect
    };
}

function processSbcData(content, timestamp) {
    const comp = content.computing_resource || {};
    const net = content.network_resource || {};
    const mem = comp.memory || {};

    if (charts.sbcCpu) updateChartData(charts.sbcCpu, timestamp, [comp.cpu || 0]);
    if (charts.sbcTemp) updateChartData(charts.sbcTemp, timestamp, [comp.temperature || 0]);
    if (charts.sbcMem) updateChartData(charts.sbcMem, timestamp, [mem.percent || 0]);
    if (charts.sbcGpu) updateChartData(charts.sbcGpu, timestamp, [comp.gpu_percent || 0]);
    if (charts.sbcDisk) updateChartData(charts.sbcDisk, timestamp, [comp.disk || 0]);
    if (charts.sbcNet) updateChartData(charts.sbcNet, timestamp, [net.rx_rate || 0, net.tx_rate || 0]);
    if (charts.sbcLatency) updateChartData(charts.sbcLatency, timestamp, [net.rtt || 0, net.jitter || 0]);

    const setSafeText = (id, value) => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = value;
        } else {
            console.warn(`Element with ID '${id}' not found in HTML.`);
        }
    };

    setSafeText('sbc-temp-val', (comp.temperature || 0).toFixed(1) + '°C');
    setSafeText('sbc-cpu-val', (comp.cpu || 0).toFixed(1) + '%');
    setSafeText('sbc-mem-used', (mem.used_gb || 0).toFixed(1) + ' GB');
    setSafeText('sbc-mem-percent', (mem.percent || 0).toFixed(1) + '%');
    setSafeText('sbc-mem-total', (mem.total_gb || 0).toFixed(1) + ' GB');
    setSafeText('sbc-gpu-percent', (comp.gpu_percent || 0).toFixed(1) + '%');
    setSafeText('sbc-disk-percent', (comp.disk || 0).toFixed(1) + '%');
    setSafeText('sbc-loss-val', (net.packet_loss || 0).toFixed(2) + '%');

    if (comp.proc_top) {
        updateProcTable(comp.proc_top);
    }
    
    updateDockerTable(comp.docker_top || []);
}

function updateProcTable(procList) {
    const tbody = document.getElementById('proc-table-body');
    // Assume procList is an array of objects. Take top 5.
    // If it's a raw string, might need parsing. Assuming JSON array here.
    let rows = '';
    
    // Sort by CPU (desc) just in case
    const sorted = Array.isArray(procList) ? procList : []; 
    
    sorted.slice(0, 5).forEach(p => {
        rows += `
            <tr>
                <td>${p.pid || '-'}</td>
                <td>${(p.name || 'unknown').substring(0, 15)}</td>
                <td class="text-orange">${p.cpu || 0}%</td>
                <td class="text-blue">${p.mem || 0}%</td>
            </tr>
        `;
    });
    tbody.innerHTML = rows;
}

// --- Polling for Triton Metrics ---
function startTritonPolling() {
    setInterval(async () => {
        try {
            const res = await fetch(TRITON_API_URL);
            if (!res.ok) return;
            const data = await res.json();
            
            if (data && !data.error) {
                processTritonData(data);
            }
        } catch (e) {
            console.error("Triton Fetch Error", e);
        }
    }, 2000); // Poll every 2 seconds
}

function startInferencePolling() {
    // 1초마다 추론 결과 갱신 (필요에 따라 시간 조절)
    setInterval(async () => {
        try {
            const res = await fetch(INFERENCE_API_URL);
            if (!res.ok) return;
            const data = await res.json();
            
            if (data && !data.error) {
                processInferenceData(data);
            }
        } catch (e) {
            console.error("Inference Fetch Error", e);
        }
    }, 1000);
}

function processTritonData(data) {
    const ts = data.timestamp || new Date().toISOString();

    if (charts.tritonUtil) {
        updateChartData(charts.tritonUtil, ts, [
            data.gpu_utilization || 0, 
            data.cpu_utilization || 0
        ]);
    }

    if (charts.tritonMem) {
        updateChartData(charts.tritonMem, ts, [
            data.gpu_memory_percent || 0, 
            data.cpu_memory_percent || 0
        ]);
    }

    if (charts.tritonPower) {
        updateChartData(charts.tritonPower, ts, [
            data.gpu_power_usage_watts || 0
        ]);
    }
    const setSafeText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };

    setSafeText('triton-cpu-util', (data.cpu_utilization || 0).toFixed(1) + '%');
    setSafeText('triton-cpu-mem-percent', (data.cpu_memory_percent || 0).toFixed(1) + '%');
    setSafeText('triton-cpu-mem-total', (data.cpu_memory_total_gb || 0).toFixed(1) + ' GB');
    setSafeText('triton-cpu-mem-used', (data.cpu_memory_used_gb || 0).toFixed(1) + ' GB');

    setSafeText('triton-gpu-util', (data.gpu_utilization || 0).toFixed(1) + '%');
    setSafeText('triton-gpu-mem-percent', (data.gpu_memory_percent || 0).toFixed(1) + '%');
    setSafeText('triton-gpu-mem-total', (data.gpu_memory_total_gb || 0).toFixed(1) + ' GB');
    setSafeText('triton-gpu-mem-used', (data.gpu_memory_used_gb || 0).toFixed(1) + ' GB');
    
    setSafeText('triton-gpu-power-usage', (data.gpu_power_usage_watts || 0).toFixed(0) + ' W');
    setSafeText('triton-gpu-power-limit', (data.gpu_power_limit_watts || 0).toFixed(0) + ' W');
}

function processInferenceData(data) {
    const setSafeText = (id, value) => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = value;
        }
    };
    const pck = data.pck !== null ? (data.pck * 100).toFixed(1) : '0.0';
    
    const pckEl = document.getElementById('inf-pck');
    if (pckEl) {
        pckEl.textContent = pck + '%';
        if (data.pck >= 0.9) pckEl.className = "stat-value text-green";
        else if (data.pck >= 0.7) pckEl.className = "stat-value text-yellow";
        else pckEl.className = "stat-value text-red";
    }

    setSafeText('inf-thresh', (data.pck_thresh_px || 0).toFixed(1));
    setSafeText('inf-mae', (data.mae_px || 0).toFixed(2) + ' px');
    setSafeText('inf-rmse', (data.rmse_px || 0).toFixed(2) + ' px');
    setSafeText('inf-time', (data.elapsed_sec || 0).toFixed(3) + ' s');
    setSafeText('inf-total-frames', data.frames_total || 0);
    setSafeText('inf-pred-frames', data.frames_pred || 0);
    setSafeText('inf-vis-frames', data.frames_visible || 0);
    setSafeText('inf-client-id', data.client_id || 'Unknown');
    setSafeText('inf-gt-fmt', data.gt_format || '-');
    setSafeText('inf-pred-fmt', data.pred_format || '-');
    
    if (data.timestamp) {
        const date = new Date(data.timestamp);
        setSafeText('inf-timestamp', date.toLocaleString('ko-KR'));
    }
}

function updateDockerTable(dockerList) {
    const tbody = document.getElementById('docker-table-body');
    if (!tbody) return;

    let rows = '';
    const list = Array.isArray(dockerList) ? dockerList : [];

    if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#8e8e8e;">No Active Containers</td></tr>';
        return;
    }

    list.forEach(c => {
        const isUp = (c.status && c.status.toLowerCase().includes('up'));
        const statusClass = isUp ? 'text-green' : 'text-red';
        
        rows += `
            <tr>
                <td style="color: #fff;">${(c.name || 'unknown').substring(0, 18)}</td>
                <td class="${statusClass}" style="font-size: 0.8rem;">${c.status || '-'}</td>
                <td class="text-orange">${c.cpu_percent || 0}%</td>
                <td class="text-blue">${c.memory_percent || 0}%</td>
            </tr>
        `;
    });
    tbody.innerHTML = rows;
}