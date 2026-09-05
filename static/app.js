let currentReportData = null;

async function loadScenario(scenarioId) {
    showLoading(true);
    try {
        const response = await fetch(`/api/sample-cases/${scenarioId}`);
        if (!response.ok) {
            throw new Error(`Failed to load scenario ${scenarioId}`);
        }
        const data = await response.json();
        currentReportData = data;
        renderAnalysisResult(data.report, data.raw_transactions);
    } catch (err) {
        alert(`Error: ${err.message}`);
    } finally {
        showLoading(false);
    }
}

async function handleFileSelect(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    
    const file = files[0];
    const formData = new FormData();
    formData.append('file', file);

    showLoading(true);
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Analysis failed');
        }
        const data = await response.json();
        currentReportData = data;
        renderAnalysisResult(data.report, data.raw_transactions);
    } catch (err) {
        alert(`Error: ${err.message}`);
    } finally {
        showLoading(false);
    }
}

function showLoading(isLoading) {
    const loadingState = document.getElementById('loading-state');
    const resultsContainer = document.getElementById('analysis-results');
    if (isLoading) {
        loadingState.classList.remove('hidden');
        resultsContainer.classList.add('hidden');
    } else {
        loadingState.classList.add('hidden');
        resultsContainer.classList.remove('hidden');
    }
}

function formatCitations(text) {
    if (!text) return '';
    // Replace [EVIDENCE: TXN-xxx] with interactive citation pills
    let formatted = text.replace(/\[EVIDENCE:\s*([A-Za-z0-9\-]+)\]/g, (match, txnId) => {
        return `<button class="citation-pill" onclick="inspectTxn('${txnId}')">📄 ${txnId}</button>`;
    });
    // Replace [RULE: R0x] with interactive rule citation pills
    formatted = formatted.replace(/\[RULE:\s*(R[0-9]+)\]/g, (match, ruleId) => {
        return `<button class="citation-pill" onclick="inspectRule('${ruleId}')">⚖️ ${ruleId}</button>`;
    });
    return formatted;
}

function renderAnalysisResult(report, rawTransactions) {
    // 1. Render Status Hero
    const statusPill = document.getElementById('status-pill');
    const statusIcon = document.getElementById('status-icon');
    const statusTitle = document.getElementById('status-title');
    const riskBadge = document.getElementById('risk-level-badge');
    const rulesCountBadge = document.getElementById('rules-count-badge');
    const summaryNarrative = document.getElementById('summary-narrative');
    const actionText = document.getElementById('action-text');

    statusPill.className = 'status-indicator';
    if (report.status === 'NO_ATTENTION_REQUIRED') {
        statusPill.classList.add('status-no-attention');
        statusIcon.textContent = '🟢';
        statusTitle.textContent = 'NO ATTENTION REQUIRED';
    } else if (report.status === 'ATTENTION_REQUIRED') {
        statusPill.classList.add('status-attention');
        statusIcon.textContent = '🚨';
        statusTitle.textContent = 'ATTENTION REQUIRED';
    } else {
        statusPill.classList.add('status-escalate');
        statusIcon.textContent = '⚡';
        statusTitle.textContent = report.status.replace(/_/g, ' ');
    }

    riskBadge.textContent = `Risk Level: ${report.risk_level}`;
    riskBadge.className = `badge badge-${report.risk_level === 'HIGH' ? 'danger' : (report.risk_level === 'LOW' ? 'success' : 'warning')}`;

    rulesCountBadge.textContent = `${report.rules_triggered ? report.rules_triggered.length : 0} Rules Triggered`;
    summaryNarrative.innerHTML = formatCitations(report.summary);
    actionText.innerHTML = formatCitations(report.recommended_investigator_action);

    // 2. Render Baseline
    const b = report.customer_baseline;
    document.getElementById('base-count').textContent = b.historical_count;
    document.getElementById('base-median').textContent = `₹${b.median_amount.toLocaleString()}`;
    document.getElementById('base-range').textContent = b.typical_range_str;
    document.getElementById('base-hours').textContent = b.active_hours_str;
    document.getElementById('base-channels').textContent = b.common_channels ? b.common_channels.join(', ') : 'None';
    document.getElementById('base-daily').textContent = b.avg_daily_transactions;
    document.getElementById('baseline-confidence').textContent = `Confidence: ${b.baseline_confidence}`;

    // 3. Priority List
    const priorityContainer = document.getElementById('priority-list-container');
    priorityContainer.innerHTML = '';
    if (report.priority_transactions && report.priority_transactions.length > 0) {
        document.getElementById('priority-section').classList.remove('hidden');
        report.priority_transactions.forEach(p => {
            const div = document.createElement('div');
            div.className = 'priority-item';
            div.innerHTML = `
                <div class="priority-rank">${p.rank}</div>
                <div class="priority-details">
                    <strong>Transaction ${p.transaction_id}</strong> — ₹${p.amount.toLocaleString()} to <em>${p.payee}</em> (${p.date_time})
                    <p style="margin-top:4px; color:#475569;">${formatCitations(p.reason)}</p>
                </div>
            `;
            priorityContainer.appendChild(div);
        });
    } else {
        priorityContainer.innerHTML = '<p style="font-size:13px; color:#64748b;">No transactions currently prioritized for inspection.</p>';
    }

    // 4. Rules Triggered Grid
    const rulesContainer = document.getElementById('rules-grid-container');
    rulesContainer.innerHTML = '';
    document.getElementById('rules-count-header').textContent = `${report.rules_triggered ? report.rules_triggered.length : 0} Rules`;
    
    if (report.rules_triggered && report.rules_triggered.length > 0) {
        report.rules_triggered.forEach(r => {
            const card = document.createElement('div');
            card.className = `rule-card-item ${r.severity}`;
            card.innerHTML = `
                <div class="rule-card-header">
                    <span class="rule-card-title">[${r.rule_id}] ${r.rule_name}</span>
                    <span class="badge badge-${r.severity === 'HIGH' ? 'danger' : 'warning'}">${r.severity}</span>
                </div>
                <p class="rule-reason">${formatCitations(r.reason)}</p>
                <div style="font-size:11px; color:#64748b;">
                    <strong>Flagged Txns:</strong> ${r.transaction_ids.map(tid => `<button class="citation-pill" onclick="inspectTxn('${tid}')">${tid}</button>`).join(' ')}
                </div>
            `;
            rulesContainer.appendChild(card);
        });
    } else {
        rulesContainer.innerHTML = '<p style="font-size:13px; color:#059669;">🟢 No risk rules were triggered by this customer profile.</p>';
    }

    // 5. Contradictions & Edge Cases
    const edgeSection = document.getElementById('edge-section');
    const contradictionsDiv = document.getElementById('contradictions-container');
    const unknownsDiv = document.getElementById('unknowns-container');
    
    let hasEdge = false;
    contradictionsDiv.innerHTML = '';
    unknownsDiv.innerHTML = '';

    if (report.contradictions && report.contradictions.length > 0) {
        hasEdge = true;
        contradictionsDiv.innerHTML = `
            <div style="background:#fee2e2; border:1px solid #fca5a5; padding:10px; border-radius:6px; margin-bottom:10px; font-size:13px; color:#991b1b;">
                <strong>⚡ Data Conflict Detected:</strong>
                <ul style="margin-left:20px; margin-top:4px;">
                    ${report.contradictions.map(c => `<li>${c}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    if (report.unknowns && report.unknowns.length > 0) {
        hasEdge = true;
        unknownsDiv.innerHTML = `
            <div style="background:#fef3c7; border:1px solid #fcd34d; padding:10px; border-radius:6px; font-size:13px; color:#92400e;">
                <strong>❓ Missing / Ambiguous Information:</strong>
                <span style="font-size:12px;"> ${report.unknowns.join(', ')}</span>
            </div>
        `;
    }

    if (hasEdge) {
        edgeSection.classList.remove('hidden');
    } else {
        edgeSection.classList.add('hidden');
    }

    // 6. Transaction Table
    const tableBody = document.getElementById('transaction-rows');
    tableBody.innerHTML = '';
    document.getElementById('table-count-badge').textContent = `${rawTransactions.length} Total Rows`;

    const flaggedTxnIds = new Set();
    if (report.rules_triggered) {
        report.rules_triggered.forEach(r => r.transaction_ids.forEach(tid => flaggedTxnIds.add(tid)));
    }

    rawTransactions.forEach(t => {
        const isFlagged = flaggedTxnIds.has(t.transaction_id);
        const tr = document.createElement('tr');
        if (isFlagged) tr.className = 'flagged-row';

        tr.innerHTML = `
            <td><strong>${t.transaction_id}</strong></td>
            <td>${t.date || ''} ${t.time || ''}</td>
            <td>${t.description || '-'}</td>
            <td>${t.payee || '<em style="color:#94a3b8">UNKNOWN</em>'}</td>
            <td style="font-weight:600;">₹${(t.amount || 0).toLocaleString()}</td>
            <td><span class="badge badge-neutral">${t.channel || 'UNKNOWN'}</span></td>
            <td>${t.is_historical ? '<span class="badge badge-info">HISTORICAL</span>' : '<span class="badge badge-warning">CURRENT</span>'}</td>
            <td><button class="btn btn-scenario" style="padding:2px 8px; font-size:11px;" onclick="inspectTxn('${t.transaction_id}')">Inspect</button></td>
        `;
        tableBody.appendChild(tr);
    });
}

function inspectTxn(txnId) {
    if (!currentReportData || !currentReportData.raw_transactions) return;
    const txn = currentReportData.raw_transactions.find(t => t.transaction_id === txnId);
    if (!txn) {
        alert(`Transaction ${txnId} not found.`);
        return;
    }

    const modal = document.getElementById('evidence-modal');
    document.getElementById('modal-title').textContent = `Evidence Record: ${txn.transaction_id}`;
    
    document.getElementById('modal-body').innerHTML = `
        <div style="font-size:13px; line-height:1.8;">
            <p><strong>Transaction ID:</strong> ${txn.transaction_id}</p>
            <p><strong>Date & Time:</strong> ${txn.date} ${txn.time}</p>
            <p><strong>Payee:</strong> ${txn.payee || 'UNKNOWN'}</p>
            <p><strong>Amount:</strong> ₹${(txn.amount || 0).toLocaleString()}</p>
            <p><strong>Channel:</strong> ${txn.channel}</p>
            <p><strong>Description:</strong> ${txn.description || 'N/A'}</p>
            <p><strong>Evaluation Status:</strong> ${txn.is_historical ? 'Historical Baseline' : 'Current Batch Evaluation'}</p>
            ${txn.secondary_amount_record ? `<p style="color:#dc2626;"><strong>Secondary Amount Record:</strong> ₹${txn.secondary_amount_record.toLocaleString()}</p>` : ''}
        </div>
    `;
    modal.classList.remove('hidden');
}

function inspectRule(ruleId) {
    const modal = document.getElementById('evidence-modal');
    document.getElementById('modal-title').textContent = `Rule Reference: ${ruleId}`;
    document.getElementById('modal-body').innerHTML = `
        <p style="font-size:13px;">Displaying retrieved Knowledge Base document for rule code <strong>${ruleId}</strong>.</p>
        <p style="font-size:12px; color:#475569; margin-top:8px;">Refer to data/rules/ for full criteria and objective evaluation details.</p>
    `;
    modal.classList.remove('hidden');
}

function closeModal() {
    document.getElementById('evidence-modal').classList.add('hidden');
}

// Automatically load normal customer scenario on initial startup
window.addEventListener('DOMContentLoaded', () => {
    loadScenario('normal_customer');
});
