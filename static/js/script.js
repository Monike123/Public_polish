// JavaScript for Normalize.io Dataset Cleaner Application

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const loadingSection = document.getElementById('loadingSection');
    const resultsSection = document.getElementById('resultsSection');
    const errorSection = document.getElementById('errorSection');

    // Handle form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            showError('Please select a file to upload.');
            return;
        }

        if (!isValidFileType(file.name)) {
            showError('Invalid file type. Please upload CSV, JSON, XLS, or XLSX files.');
            return;
        }

        uploadAndProcess(file);
    });

    // File input change handler
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            updateFileInfo(file);
        }
    });
});

function isValidFileType(filename) {
    const validExtensions = ['.csv', '.json', '.xlsx', '.xls'];
    const fileExtension = filename.toLowerCase().substring(filename.lastIndexOf('.'));
    return validExtensions.includes(fileExtension);
}

function updateFileInfo(file) {
    const fileSize = (file.size / (1024 * 1024)).toFixed(2);
    const fileInfo = document.querySelector('.file-info');
    fileInfo.innerHTML = `
        <i class="fas fa-check-circle text-success me-2"></i>
        Selected: <strong>${file.name}</strong> (${fileSize} MB)<br>
        <small>Ready to process your dataset</small>
    `;
}

function uploadAndProcess(file) {
    const formData = new FormData();
    formData.append('file', file);

    showLoading();
    hideError();
    hideResults();

    console.log('Starting upload for file:', file.name);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('Response status:', response.status);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        hideLoading();
        console.log('Upload response received:', data);
        
        if (data.error) {
            showError(data.error);
        } else if (data.success === false) {
            showError(data.error || 'Processing failed for unknown reason');
        } else {
            showResults(data);
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Upload error:', error);
        showError('An error occurred while processing your file. Please try again.');
    });
}

function showResults(data) {
    console.log('Displaying results for session:', data.session_id);
    
    try {
        // Validate data structure
        if (!data.original_shape || !data.session_id) {
            console.error('Invalid data structure:', data);
            showError('Invalid response data structure');
            return;
        }

        // Clear and recreate results section with glassmorphism styling
        document.getElementById('resultsSection').innerHTML = `
            <div class="row">
                <!-- Summary Card -->
                <div class="col-lg-6 mb-4">
                    <div class="glass-card results-card h-100">
                        <div class="glass-card-header bg-info-glass">
                            <h4 class="mb-0 text-white">
                                <i class="fas fa-chart-bar me-2"></i>Cleaning Summary
                            </h4>
                        </div>
                        <div class="glass-card-body">
                            <div id="summaryContent">
                                ${createSummaryHTML(data)}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Download Card -->
                <div class="col-lg-6 mb-4">
                    <div class="glass-card results-card h-100">
                        <div class="glass-card-header bg-warning-glass">
                            <h4 class="mb-0 text-white">
                                <i class="fas fa-download me-2"></i>Download Results
                            </h4>
                        </div>
                        <div class="glass-card-body">
                            <div id="downloadContent">
                                ${createDownloadHTML(data)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Analysis Section -->
            <div class="row mt-4">
                <div class="col">
                    <div class="glass-card results-card">
                        <div class="glass-card-header bg-secondary-glass">
                            <h4 class="mb-0 text-white">
                                <i class="fas fa-microscope me-2"></i>Dataset Analysis
                            </h4>
                        </div>
                        <div class="glass-card-body">
                            <div id="analysisContent">
                                ${createAnalysisHTML(data)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Session Info -->
            <div class="row mt-4">
                <div class="col">
                    <div class="glass-card">
                        <div class="glass-card-body">
                            <h6 class="text-white mb-3">
                                <i class="fas fa-info-circle me-2"></i>Session Information
                            </h6>
                            <p class="mb-0">
                                <small class="text-white-50">
                                    Session ID: <code class="text-info">${data.session_id}</code><br>
                                    All your files are organized in dedicated folders for easy access.
                                </small>
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        if (data.analysis) {
          renderFullAnalysis(data.analysis);
        }
        // Show results section
        document.getElementById('resultsSection').style.display = 'block';
        
        // Smooth scroll to results
        setTimeout(() => {
            document.getElementById('resultsSection').scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }, 100);
        
        console.log('Results displayed successfully');
        
    } catch (error) {
        console.error('Error displaying results:', error);
        showError('Error displaying results: ' + error.message);
    }
}

// ---------- Chart housekeeping ----------
window._charts = window._charts || [];
function destroyAllCharts() {
    if (!window._charts) window._charts = [];
    window._charts.forEach(c => {
        try { c.destroy(); } catch (e) {}
    });
    window._charts = [];
}

// Call this from showResults (after inserting analysisContent HTML):
// if (data.analysis) renderFullAnalysis(data.analysis);

function renderFullAnalysis(analysis) {
    try {
        const analysisContainer = document.getElementById('analysisContent');
        if (!analysisContainer) return;

        // Destroy old charts
        destroyAllCharts();

        // Top: stats table
        const statsHTML = createStatsTableHTML(analysis);
        // Below: charts grid
        const chartsContainer = document.createElement('div');
        chartsContainer.className = 'charts-grid mt-3';

        // Build a column info list
        const columnInfo = analysis.column_info || {};
        const numericCols = Object.entries(columnInfo).filter(([k, v]) => v && v.stats);
        const categoricalCols = Object.entries(columnInfo).filter(([k, v]) => v && v.top_values && Object.keys(v.top_values).length > 0);

        // Add stats table
        analysisContainer.innerHTML = '';
        const statsWrapper = document.createElement('div');
        statsWrapper.innerHTML = statsHTML;
        analysisContainer.appendChild(statsWrapper);

        // Correlation heatmap
        if (analysis.correlation && Object.keys(analysis.correlation).length > 0) {
            const corrDiv = document.createElement('div');
            corrDiv.className = 'glass-card mb-3';
            corrDiv.innerHTML = `<div class="glass-card-body"><h6 class="text-white">Correlation (numeric columns)</h6><div id="corrTableContainer"></div></div>`;
            analysisContainer.appendChild(corrDiv);
            renderCorrelationTable(analysis.correlation, document.getElementById('corrTableContainer'));
        }

        // Render numeric columns charts (up to a limit)
        const MAX_NUMERIC_CHARTS = 6;
        let numericCount = 0;
        numericCols.forEach(([col, info]) => {
            if (numericCount >= MAX_NUMERIC_CHARTS) return;
            const colId = col.replace(/[^a-zA-Z0-9_-]/g, '_');

            const card = document.createElement('div');
            card.className = 'glass-card mb-3';
            card.innerHTML = `
                <div class="glass-card-body">
                    <h6 class="text-white mb-3">${col} <small class="text-white-50">${info.type || ''}</small></h6>
                    <div class="row">
                        <div class="col-md-6"><canvas id="hist_${colId}" style="height:200px;"></canvas></div>
                        <div class="col-md-6"><canvas id="cum_${colId}" style="height:200px;"></canvas></div>
                    </div>
                    <div class="row mt-3">
                        <div class="col-md-6"><canvas id="scatter_${colId}" style="height:200px;"></canvas></div>
                        <div class="col-md-6"><canvas id="radar_${colId}" style="height:200px;"></canvas></div>
                    </div>
                </div>
            `;
            chartsContainer.appendChild(card);

            // histogram & cumulative
            setTimeout(() => {
                const histCtx = document.getElementById(`hist_${colId}`).getContext('2d');
                const cumCtx = document.getElementById(`cum_${colId}`).getContext('2d');
                const scatterCtx = document.getElementById(`scatter_${colId}`).getContext('2d');
                const radarCtx = document.getElementById(`radar_${colId}`).getContext('2d');

                const hist = info.histogram && info.histogram.bins && info.histogram.counts ? info.histogram : null;
                const stats = info.stats || {};

                if (hist) {
                    const bins = hist.bins;
                    const counts = hist.counts;
                    const labels = [];
                    for (let i = 0; i < bins.length - 1; i++) {
                        const lo = bins[i], hi = bins[i+1];
                        labels.push(`${Number(lo).toFixed(2)}–${Number(hi).toFixed(2)}`);
                    }
                    const c = new Chart(histCtx, {
                        type: 'bar',
                        data: { labels: labels, datasets: [{ label: `${col} (histogram)`, data: counts, backgroundColor: 'rgba(102, 126, 234, 0.6)', borderColor: '#667eea', borderWidth: 1 }]},
                        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: 'white' } } }, scales: { x: { ticks: { color: 'white' } }, y: { ticks: { color: 'white' } } } }
                    });
                    window._charts.push(c);

                    // cumulative line
                    const cumCounts = [];
                    let acc = 0;
                    for (let v of counts) { acc += v; cumCounts.push(acc); }
                    const c2 = new Chart(cumCtx, {
                        type: 'line',
                        data: { labels: labels, datasets: [{ label: `${col} (cumulative)`, data: cumCounts, fill: false, borderColor: '#764ba2', backgroundColor: 'rgba(118, 75, 162, 0.1)' }]},
                        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: 'white' } } }, scales: { x: { ticks: { color: 'white' } }, y: { ticks: { color: 'white' } } } }
                    });
                    window._charts.push(c2);
                } else {
                    // show empty placeholder
                    cumCtx.canvas.parentElement.innerHTML = '<div class="text-white-50">No histogram available</div>';
                    histCtx.canvas.parentElement.innerHTML = '<div class="text-white-50">No histogram available</div>';
                }

                // scatter: use sample rows from analysis.sample_rows (if numeric)
                const sampleRows = analysis.sample_rows || [];
                const dots = [];
                for (let i = 0; i < sampleRows.length; i++) {
                    const row = sampleRows[i];
                    if (row && Object.prototype.hasOwnProperty.call(row, col)) {
                        const y = Number(row[col]);
                        if (!isNaN(y)) dots.push({ x: i+1, y });
                    }
                }
                if (dots.length > 0) {
                    const c3 = new Chart(scatterCtx, {
                        type: 'scatter',
                        data: { datasets: [{ label: `${col} (sample scatter)`, data: dots, backgroundColor: 'rgba(240, 147, 251, 0.6)', borderColor: '#f093fb' }]},
                        options: {
                            responsive: true, maintainAspectRatio: false,
                            plugins: { legend: { labels: { color: 'white' } } },
                            scales: { x: { title: { display: true, text: 'Row index (sample)', color: 'white' }, ticks: { color: 'white' } }, y: { title: { display: true, text: col, color: 'white' }, ticks: { color: 'white' } }}
                        }
                    });
                    window._charts.push(c3);
                } else {
                    scatterCtx.canvas.parentElement.innerHTML = '<div class="text-white-50">No sample data for scatter</div>';
                }

                // radar: visualize min,Q1,median,Q3,max scaled to 0-100 for this col
                if (stats && typeof stats.min !== 'undefined' && stats.max !== stats.min) {
                    const min = Number(stats.min), q1 = Number(stats.q1), median = Number(stats.median), q3 = Number(stats.q3), max = Number(stats.max);
                    const scale = (x) => Math.round(((x - min) / (max - min)) * 100);
                    const radarData = [scale(min), scale(q1), scale(median), scale(q3), scale(max)];
                    const c4 = new Chart(radarCtx, {
                        type: 'radar',
                        data: {
                            labels: ['min','Q1','median','Q3','max'],
                            datasets: [{ label: `${col} (distribution % of range)`, data: radarData, fill: true, backgroundColor: 'rgba(67, 233, 123, 0.2)', borderColor: '#43e97b' }]
                        },
                        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: 'white' } } }, scales: { r: { ticks: { color: 'white' }, pointLabels: { color: 'white' } } } }
                    });
                    window._charts.push(c4);
                } else {
                    radarCtx.canvas.parentElement.innerHTML = '<div class="text-white-50">Radar not available (constant or missing)</div>';
                }
            }, 30);

            numericCount++;
        });

        // Categorical charts (pie/doughnut), limit to some
        const MAX_CAT = 6;
        let catCount = 0;
        categoricalCols.forEach(([col, info]) => {
            if (catCount >= MAX_CAT) return;
            const colId = col.replace(/[^a-zA-Z0-9_-]/g, '_');

            const card = document.createElement('div');
            card.className = 'glass-card mb-3';
            card.innerHTML = `
                <div class="glass-card-body">
                    <h6 class="text-white mb-3">${col} <small class="text-white-50">${info.type || ''}</small></h6>
                    <div class="row">
                        <div class="col-md-6"><canvas id="pie_${colId}" style="height:220px;"></canvas></div>
                        <div class="col-md-6"><div id="cat_${colId}" class="small text-white-50"></div></div>
                    </div>
                </div>
            `;
            chartsContainer.appendChild(card);

            setTimeout(() => {
                const ctx = document.getElementById(`pie_${colId}`).getContext('2d');
                const top = info.top_values || {};
                const labels = Object.keys(top);
                const vals = labels.map(k => top[k]);

                if (labels.length > 0) {
                    const pie = new Chart(ctx, {
                        type: 'doughnut',
                        data: { labels, datasets: [{ data: vals, backgroundColor: ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe'] }]},
                        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { color: 'white' } } } }
                    });
                    window._charts.push(pie);

                    // list top values
                    const listDiv = document.getElementById(`cat_${colId}`);
                    listDiv.innerHTML = labels.map((lbl, idx) => `<div class="mb-1">${lbl}: <strong class="text-white">${vals[idx]}</strong></div>`).join('');
                } else {
                    ctx.canvas.parentElement.innerHTML = '<div class="text-white-50">No categorical top-values</div>';
                }
            }, 30);

            catCount++;
        });

        // Append charts container after stats
        analysisContainer.appendChild(chartsContainer);

    } catch (err) {
        console.error('renderFullAnalysis error:', err);
    }
}

// --- Stats table HTML builder (all numeric columns stats) ---
function createStatsTableHTML(analysis) {
    const colInfo = analysis.column_info || {};
    const numericCols = Object.entries(colInfo).filter(([k, v]) => v && v.stats);
    if (numericCols.length === 0) {
        return `<div class="glass-alert">No numeric columns to show statistics for.</div>`;
    }

    const headers = ['Column','Count','Mean','Std','Min','Q1','Median','Q3','Max','Skew','Kurtosis'];
    let html = `<div class="glass-card"><div class="glass-card-body"><h6 class="text-white mb-3">Descriptive Statistics</h6><div class="table-responsive"><table class="table table-sm"><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>`;
    numericCols.forEach(([col, info]) => {
        const s = info.stats || {};
        const fmt = (v) => (v === null || v === undefined) ? '-' : (typeof v === 'number' ? (Math.abs(v) >= 1e6 ? v.toExponential(2) : (Math.round((v + Number.EPSILON) * 100) / 100)) : v);
        html += `<tr>
            <td><strong>${col}</strong></td>
            <td>${fmt(s.count)}</td>
            <td>${fmt(s.mean)}</td>
            <td>${fmt(s.std)}</td>
            <td>${fmt(s.min)}</td>
            <td>${fmt(s.q1)}</td>
            <td>${fmt(s.median)}</td>
            <td>${fmt(s.q3)}</td>
            <td>${fmt(s.max)}</td>
            <td>${fmt(s.skew)}</td>
            <td>${fmt(s.kurtosis)}</td>
        </tr>`;
    });
    html += `</tbody></table></div></div></div>`;
    return html;
}

// --- Correlation table renderer (simple colored table) ---
function renderCorrelationTable(corrObj, container) {
    try {
        if (!container) return;
        const keys = Object.keys(corrObj);
        if (keys.length === 0) {
            container.innerHTML = '<div class="text-white-50">No numeric columns to compute correlation.</div>';
            return;
        }
        let html = '<div class="table-responsive"><table class="table table-sm"><thead><tr><th></th>';
        keys.forEach(k => html += `<th>${k}</th>`);
        html += '</tr></thead><tbody>';

        // flatten values and compute color scale
        for (let r of keys) {
            html += `<tr><th>${r}</th>`;
            for (let c of keys) {
                let v = corrObj[r] && corrObj[r][c] ? corrObj[r][c] : 0;
                // color: map -1..1 to red..white..green
                const t = Math.max(-1, Math.min(1, v));
                const green = Math.round(((t + 1) / 2) * 255);
                const red = Math.round(((1 - t) / 2) * 255);
                const bg = `rgba(${red},${green},120,0.18)`;
                html += `<td style="background:${bg}">${Number(v).toFixed(3)}</td>`;
            }
            html += '</tr>';
        }

        html += '</tbody></table></div>';
        container.innerHTML = html;
    } catch (e) {
        console.error('renderCorrelationTable error', e);
    }
}

function createSummaryHTML(data) {
    const originalRows = Array.isArray(data.original_shape) ? data.original_shape[0] : 0;
    const originalCols = Array.isArray(data.original_shape) ? data.original_shape[1] : 0;
    const duplicatesRemoved = data.duplicates_removed || 0;
    const missingBefore = data.missing_before || 0;
    const missingAfter = data.missing_after || 0;
    
    return `
        <div class="row g-3">
            <div class="col-6">
                <div class="stat-item">
                    <div class="stat-value">${originalRows.toLocaleString()}</div>
                    <div class="stat-label">Original Rows</div>
                </div>
            </div>
            <div class="col-6">
                <div class="stat-item">
                    <div class="stat-value">${originalCols}</div>
                    <div class="stat-label">Columns</div>
                </div>
            </div>
            <div class="col-6">
                <div class="stat-item">
                    <div class="stat-value">${duplicatesRemoved.toLocaleString()}</div>
                    <div class="stat-label">Duplicates Removed</div>
                </div>
            </div>
            <div class="col-6">
                <div class="stat-item">
                    <div class="stat-value">${(missingBefore - missingAfter).toLocaleString()}</div>
                    <div class="stat-label">Missing Values Fixed</div>
                </div>
            </div>
        </div>
        
        <div class="mt-4">
            <h6 class="text-white mb-3">
                <i class="fas fa-info-circle me-2"></i>Processing Steps Applied:
            </h6>
            <ul class="list-unstyled">
                <li class="mb-2"><i class="fas fa-check text-success me-2"></i><span class="text-white">Removed duplicate rows</span></li>
                <li class="mb-2"><i class="fas fa-check text-success me-2"></i><span class="text-white">Handled missing values (median/mode imputation)</span></li>
                <li class="mb-2"><i class="fas fa-check text-success me-2"></i><span class="text-white">Cleaned column names</span></li>
                <li class="mb-2"><i class="fas fa-check text-success me-2"></i><span class="text-white">Generated comprehensive analysis report</span></li>
                <li class="mb-2"><i class="fas fa-check text-success me-2"></i><span class="text-white">Organized files in dedicated folders</span></li>
            </ul>
        </div>
    `;
}

function createDownloadHTML(data) {
    if (!data.download_urls) {
        return '<div class="glass-alert">Download links not available</div>';
    }
    
    return `
        <div class="d-grid gap-3">
            <a href="${data.download_urls.basic}" class="download-btn">
                <i class="fas fa-download me-2"></i>Download Basic Cleaned Dataset
            </a>
            <a href="${data.download_urls.advanced}" class="download-btn">
                <i class="fas fa-download me-2"></i>Download Advanced Cleaned Dataset
            </a>
            <a href="${data.download_urls.analysis}" class="download-btn">
                <i class="fas fa-chart-bar me-2"></i>Download Analysis Report (ZIP)
            </a>
        </div>
        
        <div class="mt-3">
            <small class="text-white-50">
                <i class="fas fa-info-circle me-1"></i>
                Basic: Removes duplicates and handles basic data issues<br>
                <i class="fas fa-info-circle me-1"></i>
                Advanced: Complete preprocessing with missing value imputation<br>
                <i class="fas fa-info-circle me-1"></i>
                Analysis: Detailed report with statistics and data quality info
            </small>
        </div>
    `;
}

function createAnalysisHTML(data) {
    const finalShape = Array.isArray(data.intermediate_clean_shape) ? data.intermediate_clean_shape : [0, 0];
    
    return `
        <div class="row mb-4">
            <div class="col-md-6">
                <h6 class="text-white mb-3">
                    <i class="fas fa-table me-2"></i>Dataset Overview
                </h6>
                <div class="table-responsive">
                    <table class="table table-sm">
                        <tr><td><strong>Total Rows:</strong></td><td>${finalShape[0].toLocaleString()}</td></tr>
                        <tr><td><strong>Total Columns:</strong></td><td>${finalShape[1]}</td></tr>
                        <tr><td><strong>Missing Values Before:</strong></td><td>${data.missing_before?.toLocaleString() || 0}</td></tr>
                        <tr><td><strong>Missing Values After:</strong></td><td>${data.missing_after?.toLocaleString() || 0}</td></tr>
                        <tr><td><strong>Data Quality:</strong></td><td><span class="badge bg-success">Clean</span></td></tr>
                    </table>
                </div>
            </div>
            <div class="col-md-6">
                <h6 class="text-white mb-3">
                    <i class="fas fa-columns me-2"></i>Column Types
                </h6>
                <div class="mb-2">
                    ${createDataTypesSummary(data.data_types || {})}
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-12">
                <div class="glass-alert">
                    <h6 class="text-white mb-3">
                        <i class="fas fa-lightbulb me-2"></i>Analysis Complete!
                    </h6>
                    <p class="mb-0 text-white">
                        Your dataset has been thoroughly cleaned and analyzed. All files are organized in 
                        dedicated folders:
                    </p>
                    <ul class="mb-0 mt-2 text-white">
                        <li><strong>Cleaned Datasets:</strong> Basic and advanced versions ready for analysis</li>
                        <li><strong>Analysis Report:</strong> Detailed statistics and data quality information</li>
                        <li><strong>Organized Structure:</strong> Each processing session has its own folder</li>
                    </ul>
                </div>
            </div>
        </div>
    `;
}

function createDataTypesSummary(dataTypes) {
    if (!dataTypes || Object.keys(dataTypes).length === 0) {
        return '<div class="text-white-50">No data type information available</div>';
    }
    
    const typeCounts = {};
    Object.values(dataTypes).forEach(type => {
        typeCounts[type] = (typeCounts[type] || 0) + 1;
    });
    
    return Object.entries(typeCounts)
        .map(([type, count]) => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span class="badge" style="background: rgba(255,255,255,0.2); color: white;">${type}</span>
                <span class="text-white-50">${count} column${count !== 1 ? 's' : ''}</span>
            </div>
        `).join('');
}

function showLoading() {
    document.getElementById('loadingSection').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loadingSection').style.display = 'none';
}

function hideResults() {
    document.getElementById('resultsSection').style.display = 'none';
}

function showError(message) {
    const errorSection = document.getElementById('errorSection');
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    errorSection.style.display = 'block';
    
    // Scroll to error
    errorSection.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
    });
}

function hideError() {
    document.getElementById('errorSection').style.display = 'none';
}

// Drag and drop functionality (completed)
document.addEventListener('DOMContentLoaded', function() {
  const fileInput = document.getElementById('fileInput');
  const uploadForm = document.getElementById('uploadForm'); // your form element
  const dropZone = document.getElementById('dropZone') || uploadForm; // optional drop zone element, fallback to form

  if (!fileInput || !uploadForm) {
    // Nothing to wire up
    return;
  }

  // Prevent default behaviour for a set of events
  const preventDefaults = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  // Add highlight class for visual feedback
  const highlight = (e) => {
    if (dropZone) dropZone.classList.add('dragover');
  };

  const unhighlight = (e) => {
    if (dropZone) dropZone.classList.remove('dragover');
  };

  // When files are dropped, assign them to the file input and update UI
  const handleDrop = (e) => {
    preventDefaults(e);
    unhighlight(e);

    const dt = e.dataTransfer;
    if (!dt) return;

    const files = dt.files;
    if (!files || files.length === 0) return;

    // Set files to the input (this is supported in modern browsers)
    try {
      fileInput.files = files;
    } catch (err) {
      // Some older browsers may not allow assignment; fallback to user prompt
      console.warn('Could not assign files to input programmatically:', err);
    }

    // Update UI with first file
    updateFileInfo(files[0]);
  };

  // Handle paste (optional): allow users to paste files from clipboard
  const handlePaste = (e) => {
    const items = e.clipboardData && e.clipboardData.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === 'file') {
        const blob = item.getAsFile();
        if (blob) {
          // create a DataTransfer to set fileInput.files (works in modern browsers)
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(blob);
          fileInput.files = dataTransfer.files;
          updateFileInfo(blob);
          break;
        }
      }
    }
  };

  // Click anywhere in dropZone opens file picker
  if (dropZone) {
    dropZone.addEventListener('click', (e) => {
      // Only trigger if clicking on the dropZone itself, not child elements like buttons
      if (e.target === dropZone || e.target.closest('.upload-zone')) {
        fileInput.click();
      }
    });
  }

  // Wire drag events
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach((eventName) => {
    (dropZone || document).addEventListener(eventName, preventDefaults, false);
  });

  ['dragenter', 'dragover'].forEach((eventName) => {
    (dropZone || document).addEventListener(eventName, highlight, false);
  });

  ['dragleave', 'drop'].forEach((eventName) => {
    (dropZone || document).addEventListener(eventName, unhighlight, false);
  });

  // Attach drop handler
  (dropZone || document).addEventListener('drop', handleDrop, false);

  // Attach paste handler to the document so users can paste screenshots/files
  document.addEventListener('paste', handlePaste, false);

  // Also update info when user picks via file dialog
  fileInput.addEventListener('change', function (e) {
    const file = e.target.files && e.target.files[0];
    if (file) updateFileInfo(file);
  });

  // Optional: allow pressing Enter on focused dropZone to open file picker
  if (dropZone) {
    dropZone.setAttribute('tabindex', '0'); // make focusable
    dropZone.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        fileInput.click();
      }
    });
  }
});