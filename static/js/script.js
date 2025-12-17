// JavaScript for Normalize.io - Minimalist Black & White Theme

document.addEventListener('DOMContentLoaded', function () {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const resultsSection = document.getElementById('resultsSection');

    // Upload Form Handler
    if (uploadForm) {
        uploadForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const file = fileInput.files[0];
            if (!file) {
                showError('Please select a file to upload.');
                return;
            }
            if (!isValidFileType(file.name)) {
                showError('Invalid file type.');
                return;
            }
            uploadAndProcess(file);
        });
    }

    // File Input Visuals
    if (fileInput) {
        fileInput.addEventListener('change', function (e) {
            const file = e.target.files[0];
            if (file) updateFileInfo(file);
        });
    }
});

function isValidFileType(filename) {
    return /\.(csv|json|xlsx|xls)$/i.test(filename);
}

function updateFileInfo(file) {
    const fileSize = (file.size / (1024 * 1024)).toFixed(2);
    const fileInfo = document.querySelector('.file-info');
    if (fileInfo) {
        fileInfo.innerHTML = `<strong>${file.name}</strong> (${fileSize} MB)`;
        fileInfo.classList.remove('text-muted');
        fileInfo.classList.add('text-success');
    }
}

function uploadAndProcess(file) {
    const formData = new FormData();
    formData.append('file', file);

    // Add configuration options
    formData.append('scale_numeric', document.getElementById('scaleNumeric').checked);
    formData.append('encode_categorical', document.getElementById('encodeCategorical').checked);
    formData.append('handle_outliers', document.getElementById('handleOutliers').checked);

    showLoading();
    hideError();
    hideResults();

    fetch('/upload', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            hideLoading();
            if (data.error || data.success === false) {
                showError(data.error || 'Processing failed.');
            } else {
                showResults(data);
            }
        })
        .catch(err => {
            hideLoading();
            showError('Upload failed: ' + err.message);
        });
}

function processPublicDataset(filename) {
    const config = {
        filename: filename,
        scale_numeric: document.getElementById('scaleNumeric') ? document.getElementById('scaleNumeric').checked : true,
        encode_categorical: document.getElementById('encodeCategorical') ? document.getElementById('encodeCategorical').checked : true,
        handle_outliers: document.getElementById('handleOutliers') ? document.getElementById('handleOutliers').checked : true
    };

    showLoading();
    hideError();
    hideResults();

    fetch('/process_public', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    })
        .then(r => r.json())
        .then(data => {
            hideLoading();
            if (data.error || data.success === false) {
                showError(data.error || 'Processing failed.');
            } else {
                showResults(data);
            }
        })
        .catch(err => {
            hideLoading();
            showError('Processing failed: ' + err.message);
        });
}

function showResults(data) {
    const container = document.getElementById('resultsSection');
    if (!container) return;

    // Render Tabbed Interface
    container.innerHTML = `
        <div class="glass-card">
            <div class="glass-card-header">
                <div class="d-flex justify-content-between align-items-center">
                    <h4 class="mb-0">Analysis Results</h4>
                    <div>
                        <span class="badge bg-dark">Quality Score: ${data.analysis.quality_score || 'N/A'}</span>
                    </div>
                </div>
            </div>
            <div class="glass-card-body p-0">
                <!-- Tabs -->
                <ul class="nav nav-tabs px-3 pt-3" id="resultTabs" role="tablist">
                    <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-overview">Overview</button></li>
                    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-cleaning">Cleaning Report</button></li>
                    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-charts">Charts</button></li>
                    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-columns">Column Insights</button></li>
                    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-ai">
                        <i class="fas fa-robot me-1 text-primary"></i> AI Insights
                    </button></li>
                    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-downloads">Downloads</button></li>
                </ul>
                
                <div class="tab-content p-4">
                    <!-- Overview Tab -->
                    <div class="tab-pane fade show active" id="tab-overview">
                        ${renderOverview(data)}
                    </div>
                    
                    <!-- Cleaning Tab -->
                    <div class="tab-pane fade" id="tab-cleaning">
                        ${renderCleaningReport(data)}
                    </div>
                    
                    <!-- Charts Tab -->
                    <div class="tab-pane fade" id="tab-charts">
                        ${renderCharts(data)}
                    </div>

                    <!-- Columns Tab -->
                    <div class="tab-pane fade" id="tab-columns">
                        ${renderColumnInsights(data)}
                    </div>

                    <!-- AI Insights Tab -->
                    <div class="tab-pane fade" id="tab-ai">
                        ${renderAIInsights(data)}
                    </div>

                    <!-- Downloads Tab -->
                    <div class="tab-pane fade" id="tab-downloads">
                        ${renderDownloads(data)}
                    </div>
                </div>
            </div>
        </div>
    `;

    container.style.display = 'block';
    container.scrollIntoView({ behavior: 'smooth' });
}

function renderAIInsights(data) {
    const insights = data.analysis.smart_insights || [];
    let html = `
        <div class="row">
            <!-- Left: Narrative Insights -->
            <div class="col-lg-8">
                <h5 class="mb-4"><i class="fas fa-sparkles me-2 text-warning"></i>Smart Analysis</h5>
    `;

    if (insights.length === 0) {
        html += '<div class="alert alert-light">No specific AI insights generated for this dataset.</div>';
    } else {
        insights.forEach(insight => {
            html += `
                <div class="card mb-3 border-0 shadow-sm">
                    <div class="card-body">
                        <div class="d-flex align-items-start">
                            <div class="me-3 p-2 bg-light rounded-circle">
                                <i class="fas ${insight.icon} fa-lg text-primary"></i>
                            </div>
                            <div>
                                <h6 class="card-title fw-bold">${insight.title}</h6>
                                <div class="card-text text-muted">${insight.content}</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
    }

    html += `
            </div>
            <!-- Right: Chat Interface (Mock) -->
            <div class="col-lg-4">
                <div class="card h-100 border-0 shadow-sm bg-light">
                    <div class="card-header bg-white border-0 py-3">
                        <h6 class="mb-0"><i class="fas fa-comments me-2"></i>Ask about your data</h6>
                    </div>
                    <div class="card-body d-flex flex-column" style="height: 400px;">
                        <div class="chat-history flex-grow-1 overflow-auto mb-3 p-2" id="chatHistory">
                            <div class="chat-message bot mb-2">
                                <small class="text-muted d-block mb-1">AI Assistant</small>
                                <div class="p-2 bg-white rounded shadow-sm d-inline-block">
                                    Hello! I've analyzed your data. Ask me specifically about columns like 
                                    ${data.analysis.columns.slice(0, 3).map(c => `<b>${c.name}</b>`).join(', ')}.
                                </div>
                            </div>
                        </div>
                        <div class="mt-auto">
                            <div class="input-group">
                                <input type="text" class="form-control" id="chatInput" placeholder="Type a question...">
                                <button class="btn btn-dark" type="button" onclick="handleChatInput()">
                                    <i class="fas fa-paper-plane"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    return html;
}

function handleChatInput() {
    const input = document.getElementById('chatInput');
    const history = document.getElementById('chatHistory');
    const msg = input.value.trim();
    if (!msg) return;

    // User Message
    history.innerHTML += `
        <div class="chat-message user mb-2 text-end">
            <small class="text-muted d-block mb-1">You</small>
            <div class="p-2 bg-dark text-white rounded shadow-sm d-inline-block text-start">
               ${msg}
            </div>
        </div>
    `;

    input.value = '';
    history.scrollTop = history.scrollHeight;

    // Mock Bot Response
    setTimeout(() => {
        let response = "I'm focusing on the generated insights for now. Try exploring the charts tab for visual details!";
        if (msg.toLowerCase().includes('mean') || msg.toLowerCase().includes('average')) {
            response = "You can find detailed statistics like Mean and Median in the 'Column Insights' tab.";
        } else if (msg.toLowerCase().includes('outlier')) {
            response = "I've flagged potential distribution anomalies in the main insights panel on the left.";
        }

        history.innerHTML += `
            <div class="chat-message bot mb-2">
                <small class="text-muted d-block mb-1">AI Assistant</small>
                <div class="p-2 bg-white rounded shadow-sm d-inline-block">
                   ${response}
                </div>
            </div>
        `;
        history.scrollTop = history.scrollHeight;
    }, 600);
}

function renderOverview(data) {
    return `
        <div class="row g-4">
            <div class="col-md-3">
                <div class="stat-item">
                    <div class="stat-value">${data.original_shape[0]}</div>
                    <div class="stat-label">Rows</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-item">
                    <div class="stat-value">${data.original_shape[1]}</div>
                    <div class="stat-label">Columns</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-item">
                    <div class="stat-value">${data.analysis.quality_score}</div>
                    <div class="stat-label">Quality Score</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-item">
                    <div class="stat-value">${data.analysis.columns.length}</div>
                    <div class="stat-label">Analyzed Cols</div>
                </div>
            </div>
        </div>
        
        <div class="mt-4">
            <h5>Data Quality Summary</h5>
            <div class="row">
                <div class="col-md-6">
                    <ul class="list-group list-group-flush">
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Missing Values
                            <span class="badge bg-secondary rounded-pill">${data.analysis.missing_cells}</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Duplicate Rows
                            <span class="badge bg-secondary rounded-pill">${data.analysis.duplicate_rows}</span>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    `;
}

function renderCleaningReport(data) {
    const report = data.cleaning_report || {};
    // Before/After Missing
    const missingBefore = data.missing_before;
    const missingAfter = data.missing_after;

    let html = `
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">Impact Summary</div>
                    <div class="card-body">
                        <table class="table mb-0">
                            <thead><tr><th>Metric</th><th>Before</th><th>After</th></tr></thead>
                            <tbody>
                                <tr>
                                    <td>Missing Values</td>
                                    <td class="text-danger">${missingBefore}</td>
                                    <td class="text-success">${missingAfter}</td>
                                </tr>
                                <tr>
                                    <td>Columns</td>
                                    <td>${data.original_shape[1]}</td>
                                    <td>${data.intermediate_clean_shape[1]}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <h5>Actions Taken</h5>
        <div class="accordion" id="cleaningActions">
    `;

    if (report.numeric_scaled && report.numeric_scaled.length > 0) {
        html += `
            <div class="card mb-2">
                <div class="card-header bg-light">Scaled Numeric Columns</div>
                <div class="card-body"><small class="text-muted">${report.numeric_scaled.join(', ')}</small></div>
            </div>`;
    }

    if (report.categorical_encoded && report.categorical_encoded.length > 0) {
        html += `
            <div class="card mb-2">
                <div class="card-header bg-light">Encoded Categorical Columns</div>
                <div class="card-body"><small class="text-muted">${report.categorical_encoded.join(', ')}</small></div>
            </div>`;
    }

    if (report.datetime_columns && report.datetime_columns.length > 0) {
        html += `
            <div class="card mb-2">
                <div class="card-header bg-light">Preserved Datetime Columns</div>
                <div class="card-body"><small class="text-muted">${report.datetime_columns.join(', ')}</small></div>
            </div>`;
    }

    html += '</div>';
    return html;
}

function renderCharts(data) {
    const charts = data.analysis.charts || [];
    if (charts.length === 0) return '<div class="alert alert-info">No charts generated.</div>';

    let html = '<div class="row g-4">';
    charts.forEach(filename => {
        html += `
            <div class="col-md-6 col-lg-4">
                <div class="border rounded p-2 text-center h-100">
                    <h6 class="mb-2 text-truncate" title="${filename}">${formatChartName(filename)}</h6>
                    <img src="/analysis/images/${data.session_id}/${filename}" 
                         class="chart-thumbnail" 
                         alt="${filename}"
                         onclick="window.open(this.src, '_blank')">
                </div>
            </div>
        `;
    });
    html += '</div>';
    return html;
}

function formatChartName(filename) {
    return filename.replace('.png', '').replace(/_/g, ' ').replace('hist ', 'Histogram: ');
}

function renderColumnInsights(data) {
    const alerts = data.analysis.column_alerts || [];
    const columns = data.analysis.columns || [];

    let html = '';

    if (alerts.length > 0) {
        html += '<h5>Insights & Warnings</h5><div class="mb-4">';
        alerts.forEach(alert => {
            const color = alert.type === 'warning' ? 'warning' : 'info';
            const icon = alert.type === 'warning' ? 'exclamation-triangle' : 'info-circle';
            html += `
                <div class="alert alert-${color} d-flex align-items-center mb-2">
                    <i class="fas fa-${icon} me-3"></i>
                    <div>
                        <strong>${alert.column}</strong>: ${alert.msg}
                    </div>
                </div>
            `;
        });
        html += '</div>';
    }

    html += '<h5>Column Statistics</h5><div class="table-responsive"><table class="table table-sm">';
    html += '<thead><tr><th>Column</th><th>Type</th><th>Missing</th><th>Unique</th><th>Mean/Top</th></tr></thead><tbody>';

    columns.forEach(col => {
        let val = '-';
        if (col.type === 'numeric') val = formatNumber(col.mean);
        if (col.type === 'categorical' && col.top_values && col.top_values.length > 0) val = col.top_values[0][0];

        html += `
            <tr>
                <td>${col.name}</td>
                <td><span class="badge bg-light text-dark border">${col.type}</span></td>
                <td>${col.missing}</td>
                <td>${col.unique}</td>
                <td>${val}</td>
            </tr>
        `;
    });
    html += '</tbody></table></div>';

    return html;
}

function renderDownloads(data) {
    return `
        <div class="row">
            <div class="col-md-6 mx-auto">
                <div class="d-grid gap-3">
                    <a href="${data.download_urls.basic}" class="download-btn">
                        <i class="fas fa-file-csv"></i> Download Basic Cleaned Data
                    </a>
                    <a href="${data.download_urls.advanced}" class="download-btn">
                        <i class="fas fa-file-csv"></i> Download Advanced Cleaned Data
                    </a>
                    <a href="${data.download_urls.analysis}" class="download-btn">
                        <i class="fas fa-file-archive"></i> Download Full Analysis ZIP
                    </a>
                </div>
            </div>
        </div>
    `;
}

function showLoading() {
    const el = document.getElementById('loadingSection');
    if (el) el.style.display = 'block';
}

function hideLoading() {
    const el = document.getElementById('loadingSection');
    if (el) el.style.display = 'none';
}

function hideResults() {
    const el = document.getElementById('resultsSection');
    if (el) el.style.display = 'none';
}

function showError(msg) {
    const el = document.getElementById('errorSection');
    if (el) {
        el.style.display = 'block';
        document.getElementById('errorMessage').textContent = msg;
    }
}

function hideError() {
    const el = document.getElementById('errorSection');
    if (el) el.style.display = 'none';
}

// Drag & Drop Setup
const dropZone = document.getElementById('dropZone');
if (dropZone) {
    dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone.addEventListener('dragleave', e => { e.preventDefault(); dropZone.classList.remove('dragover'); });
    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length) {
            document.getElementById('fileInput').files = files;
            updateFileInfo(files[0]);
        }
    });
    dropZone.addEventListener('click', e => {
        if (e.target === dropZone || e.target.closest('.upload-zone')) {
            document.getElementById('fileInput').click();
        }
    });
}

function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined || isNaN(num)) return '-';
    return Number(num).toFixed(decimals);
}