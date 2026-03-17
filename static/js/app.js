/* DevRelOS – Main Application JS */
"use strict";

// ── State ────────────────────────────────────────────────────────────────────
const STATE = {
  sessionId:        null,
  mode:             "chat",
  currentRequest:   null,
  isLoading:        false,
  isRecording:      false,
  recognition:      null,
  schemas:          [],
  activeSection:    "chat",
  activePanelTab:   "request",
};

// ── DOM Refs ─────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

// ── Session ──────────────────────────────────────────────────────────────────
function initSession() {
  STATE.sessionId = localStorage.getItem("devrelosSession") || crypto.randomUUID();
  localStorage.setItem("devrelosSession", STATE.sessionId);
}

// ── Toast Notifications ───────────────────────────────────────────────────────
function toast(message, type = "info", duration = 3000) {
  const icons = { success: "✅", error: "❌", warning: "⚠️", info: "ℹ️" };
  const container = $("toast-container");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type] || "ℹ️"}</span><span>${message}</span>`;
  container.appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; el.style.transition = "opacity .3s"; setTimeout(() => el.remove(), 300); }, duration);
}

// ── Section Navigation ────────────────────────────────────────────────────────
function showSection(name) {
  STATE.activeSection = name;
  $$(".section").forEach(s => s.classList.remove("active"));
  $$(".sidebar-item").forEach(s => s.classList.remove("active"));

  const section = $(`section-${name}`);
  if (section) section.classList.add("active");

  const sidebarItem = document.querySelector(`[data-section="${name}"]`);
  if (sidebarItem) sidebarItem.classList.add("active");

  const navLink = document.querySelector(`.header-nav a[data-page="${name}"]`);
  $$(".header-nav a").forEach(a => a.classList.remove("active"));
  if (navLink) navLink.classList.add("active");

  if (name === "playground") loadSchemas();
  if (name === "analytics")  loadAnalytics();
}

// ── Panel Tabs ────────────────────────────────────────────────────────────────
function switchPanelTab(tab) {
  STATE.activePanelTab = tab;
  $$(".panel-tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tab));
  $$(".panel-pane").forEach(p => p.classList.toggle("active", p.id === `pane-${tab}`));
}

// ── Mode Selection ────────────────────────────────────────────────────────────
function setMode(mode) {
  STATE.mode = mode;
  $$(".mode-chip").forEach(c => c.classList.toggle("active", c.dataset.mode === mode));
  const placeholder = {
    chat:     "What do you want to build? (e.g. 'Charge $50 to a customer')",
    support:  "Ask a developer support question…",
    tutorial: "What do you want to learn? (e.g. 'How do I send an SMS with Twilio?')",
    docs:     "What API docs do you need? (e.g. 'Show Stripe payment intents docs')",
  };
  $("chat-input").placeholder = placeholder[mode] || placeholder.chat;
}

// ── Chat ──────────────────────────────────────────────────────────────────────
function appendMessage(role, content, extras = {}) {
  const container = $("chat-messages");
  const isUser    = role === "user";
  const div       = document.createElement("div");
  div.className   = `message ${role}`;

  let bubbleContent = `<div class="msg-text">${formatText(content)}</div>`;

  if (extras.timestamp) {
    bubbleContent += `<div class="msg-meta">${new Date().toLocaleTimeString()}</div>`;
  }
  if (extras.suggestions && extras.suggestions.length) {
    bubbleContent += `<div class="mt-8">${extras.suggestions.map(s =>
      `<span class="msg-suggestion" onclick="quickSend('${s.replace(/'/g,"\\'")}')">💡 ${s}</span>`
    ).join("")}</div>`;
  }

  div.innerHTML = `
    <div class="msg-avatar">${isUser ? "👤" : "🤖"}</div>
    <div class="msg-bubble">${bubbleContent}</div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function appendTypingIndicator() {
  const container = $("chat-messages");
  const div = document.createElement("div");
  div.className = "message assistant";
  div.id = "typing-indicator";
  div.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble">
      <div class="typing-indicator">
        <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
      </div>
    </div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
  const el = $("typing-indicator");
  if (el) el.remove();
}

function quickSend(text) {
  $("chat-input").value = text;
  sendChat();
}

async function sendChat() {
  const input = $("chat-input");
  const query = input.value.trim();
  if (!query || STATE.isLoading) return;

  input.value = "";
  autoResize(input);
  appendMessage("user", query, { timestamp: true });
  appendTypingIndicator();

  STATE.isLoading = true;
  $("send-btn").disabled = true;

  try {
    const res = await api("/api/chat", "POST", {
      query:      query,
      session_id: STATE.sessionId,
      mode:       STATE.mode,
    });

    removeTypingIndicator();

    if (res.error) throw new Error(res.error);

    // Display response in chat
    const explanation = res.explanation || res.documentation || "I've prepared an API request for you.";
    appendMessage("assistant", explanation, {
      timestamp:   true,
      suggestions: res.suggestions || [],
    });

    // Populate right panel
    if (res.api_request) {
      STATE.currentRequest = res.api_request;
      renderRequestPanel(res.api_request, res);
      switchPanelTab("request");
    } else if (res.tutorial) {
      renderTutorialPanel(res.tutorial);
      switchPanelTab("docs");
    } else {
      renderDocsPanel(explanation);
      switchPanelTab("docs");
    }

    if (res.cred_warning) toast(res.cred_warning, "warning", 6000);

  } catch (err) {
    removeTypingIndicator();
    appendMessage("assistant", `⚠️ Error: ${err.message}`);
    toast(err.message, "error");
  } finally {
    STATE.isLoading = false;
    $("send-btn").disabled = false;
    input.focus();
  }
}

// ── Right Panel Renderers ─────────────────────────────────────────────────────
function renderRequestPanel(req, fullRes) {
  const panel = $("pane-request");
  if (!req || !req.url) {
    panel.innerHTML = `<p class="text-muted text-sm">No API request generated yet.</p>`;
    return;
  }

  const method      = req.method || "GET";
  const url         = req.url    || "";
  const body        = req.body;
  const params      = req.params || {};
  const description = req.description || "";
  const curl        = req.curl_example || buildCurl(req);
  const credWarn    = fullRes?.cred_warning;

  panel.innerHTML = `
    <div class="api-card">
      <div class="api-card-header">
        <span class="method-badge method-${method}">${method}</span>
        <span class="endpoint-url">${url}</span>
        <span class="provider-pill">${req.provider || ""}</span>
      </div>
      <div class="api-card-body">
        ${description ? `<p class="text-sm text-muted" style="margin-bottom:10px">${description}</p>` : ""}
        ${Object.keys(params).length ? renderFields("Query Params", params) : ""}
        ${body ? renderFields("Body", body) : ""}
      </div>
      ${credWarn ? `<div class="execute-area"><div class="cred-warning">⚠️ ${credWarn}</div></div>` : ""}
      <div class="execute-area">
        <button class="btn btn-success" onclick="executeRequest()">▶ Execute Request</button>
        <button class="btn btn-outline btn-sm" onclick="copyToClipboard('${escapeAttr(JSON.stringify(req))}')">📋 Copy JSON</button>
        <button class="btn btn-outline btn-sm" onclick="copyCurl()">📋 Copy cURL</button>
      </div>
    </div>
    ${curl ? `
    <div class="api-card">
      <div class="api-card-header"><span style="font-size:.8rem;color:var(--text-muted)">cURL Example</span></div>
      <div class="api-card-body"><pre>${escapeHtml(curl)}</pre></div>
    </div>` : ""}
    <div id="response-container" style="margin-top:8px"></div>
  `;
}

function renderFields(label, obj) {
  if (!obj || typeof obj !== "object") return "";
  const rows = Object.entries(obj).map(([k, v]) =>
    `<div class="field-row">
      <span class="field-key">${k}</span>
      <span class="field-val">${typeof v === "object" ? JSON.stringify(v) : v}</span>
    </div>`
  ).join("");
  return `<div style="margin-bottom:10px">
    <div class="text-xs text-muted" style="margin-bottom:4px;text-transform:uppercase;letter-spacing:.06em">${label}</div>
    ${rows}
  </div>`;
}

function renderDocsPanel(markdown) {
  const panel = $("pane-docs");
  panel.innerHTML = `<div class="markdown-body">${parseMarkdown(markdown)}</div>`;
  switchPanelTab("docs");
}

function renderTutorialPanel(tutorial) {
  const panel = $("pane-docs");
  let html = `<div class="markdown-body">
    <h1>${tutorial.title || "Tutorial"}</h1>
    <p>${tutorial.description || ""}</p>`;

  if (tutorial.estimated_time) html += `<p class="text-sm text-muted">⏱ ${tutorial.estimated_time}</p>`;

  if (tutorial.prerequisites?.length) {
    html += `<h2>Prerequisites</h2><ul>${tutorial.prerequisites.map(p => `<li>${p}</li>`).join("")}</ul>`;
  }

  if (tutorial.steps?.length) {
    html += `<h2>Steps</h2>`;
    tutorial.steps.forEach(step => {
      html += `<h3>Step ${step.step}: ${step.title}</h3><p>${step.description}</p>`;
      if (step.code?.snippet) {
        html += `<pre>${escapeHtml(step.code.snippet)}</pre>`;
      }
    });
  }

  if (tutorial.code_examples?.length) {
    html += `<h2>Full Examples</h2>`;
    tutorial.code_examples.forEach(ex => {
      html += `<h3>${ex.title}</h3><pre>${escapeHtml(ex.code)}</pre>`;
    });
  }

  html += `</div>`;
  panel.innerHTML = html;
  switchPanelTab("docs");
}

// ── Execute ───────────────────────────────────────────────────────────────────
async function executeRequest(customReq) {
  const req = customReq || STATE.currentRequest;
  if (!req) { toast("No request to execute", "warning"); return; }

  const container = $("response-container");
  if (container) {
    container.innerHTML = `<div class="response-box"><div class="typing-indicator">
      <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
    </div></div>`;
  }

  try {
    const payload = {
      session_id:   STATE.sessionId,
      api_provider: req.provider,
      endpoint:     req.endpoint_key || req.endpoint || "",
      method:       req.method,
      url:          req.url,
      headers:      req.headers || {},
      params:       req.params  || {},
      body:         req.body    || null,
      content_type: req.content_type || null,
      original_query: req.description || "",
    };

    const res = await api("/api/execute", "POST", payload);

    const status     = res.status_code;
    const isSuccess  = res.success;
    const statusClass = isSuccess ? "status-2xx" : (status >= 500 ? "status-5xx" : "status-4xx");
    const responseStr = JSON.stringify(res.response_data, null, 2);
    const timeBadge  = res.response_time_ms ? `${res.response_time_ms}ms` : "";

    if (container) {
      container.innerHTML = `
        <div class="response-box ${isSuccess ? "response-success" : "response-error"}">
          <div class="response-header">
            <span class="status-pill ${statusClass}">${status}</span>
            <span class="text-xs text-muted">${isSuccess ? "✅ Success" : "❌ Failed"}</span>
            ${timeBadge ? `<span class="text-xs text-muted">${timeBadge}</span>` : ""}
          </div>
          <pre style="margin:0;background:transparent;border:none;padding:0;color:inherit">${escapeHtml(responseStr)}</pre>
        </div>
        ${res.explanation ? `<div class="markdown-body mt-8" style="font-size:.82rem">${parseMarkdown(res.explanation)}</div>` : ""}
        ${res.debug_info && !isSuccess ? renderDebugInfo(res.debug_info) : ""}
        ${res.retry_request ? `<div class="mt-8">
          <button class="btn btn-outline btn-sm" onclick='executeRequest(${JSON.stringify(res.retry_request)})'>🔄 Retry with suggested fix</button>
        </div>` : ""}
      `;
    }

    appendMessage("assistant",
      isSuccess
        ? `✅ API call succeeded (${status}) in ${timeBadge}`
        : `❌ API call failed (${status}): ${res.debug_info?.user_friendly_msg || "Check the response panel"}`,
      {}
    );

    if (isSuccess) toast(`Request succeeded! HTTP ${status}`, "success");
    else           toast(`Request failed: HTTP ${status}`, "error");

  } catch (err) {
    if (container) container.innerHTML = `<div class="response-box response-error">Error: ${escapeHtml(err.message)}</div>`;
    toast(err.message, "error");
  }
}

function renderDebugInfo(debug) {
  if (!debug) return "";
  const fixes = (debug.suggested_fixes || []).map(f => `<li>${f}</li>`).join("");
  return `
    <div class="api-card mt-8">
      <div class="api-card-header" style="background:rgba(239,68,68,.1);border-color:var(--error)">
        <span style="color:var(--error);font-weight:600;font-size:.85rem">🐛 Debug Analysis</span>
        <span class="text-xs text-muted">${debug.error_type || "error"}</span>
      </div>
      <div class="api-card-body">
        <p style="color:var(--error);font-size:.85rem;margin-bottom:8px">${debug.user_friendly_msg || ""}</p>
        <p class="text-sm text-muted" style="margin-bottom:8px">${debug.root_cause || ""}</p>
        ${fixes ? `<ul style="font-size:.82rem;color:var(--text-muted);padding-left:16px">${fixes}</ul>` : ""}
        ${debug.docs_link ? `<a href="${debug.docs_link}" target="_blank" class="text-sm">📖 View docs →</a>` : ""}
      </div>
    </div>`;
}

// ── Voice Input ───────────────────────────────────────────────────────────────
function initVoice() {
  if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
    $("voice-btn").title = "Speech recognition not supported in this browser";
    $("voice-btn").style.opacity = ".3";
    return;
  }
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  STATE.recognition = new SpeechRecognition();
  STATE.recognition.continuous     = false;
  STATE.recognition.interimResults = true;
  STATE.recognition.lang           = "en-US";

  STATE.recognition.onresult = event => {
    let interim = "", final = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const t = event.results[i][0].transcript;
      if (event.results[i].isFinal) final += t;
      else interim += t;
    }
    $("chat-input").value = final || interim;
    autoResize($("chat-input"));
  };

  STATE.recognition.onend = () => {
    STATE.isRecording = false;
    $("voice-btn").classList.remove("recording");
    $("voice-btn").title = "Voice input";
    const val = $("chat-input").value.trim();
    if (val) sendChat();
  };

  STATE.recognition.onerror = e => {
    STATE.isRecording = false;
    $("voice-btn").classList.remove("recording");
    toast(`Voice error: ${e.error}`, "error");
  };
}

function toggleVoice() {
  if (!STATE.recognition) { toast("Speech recognition not available", "warning"); return; }
  if (STATE.isRecording) {
    STATE.recognition.stop();
    STATE.isRecording = false;
    $("voice-btn").classList.remove("recording");
  } else {
    STATE.recognition.start();
    STATE.isRecording = true;
    $("voice-btn").classList.add("recording");
    $("voice-btn").title = "Recording… click to stop";
    toast("🎤 Listening…", "info", 2000);
  }
}

// ── API Playground Section ─────────────────────────────────────────────────────
async function loadSchemas() {
  const grid = $("providers-grid");
  if (!grid) return;
  grid.innerHTML = skeletonCards(3);
  try {
    const res = await api("/api/schemas");
    STATE.schemas = res.schemas || [];
    grid.innerHTML = STATE.schemas.map(renderProviderCard).join("") ||
      `<p class="text-muted">No schemas loaded. Add via POST /api/schemas</p>`;
  } catch (err) {
    grid.innerHTML = `<p class="text-muted">Failed to load schemas: ${err.message}</p>`;
  }
}

const PROVIDER_ICONS = { stripe: "💳", twilio: "📱", github: "🐙", default: "🔌" };

function renderProviderCard(schema) {
  const icon      = PROVIDER_ICONS[schema.provider] || PROVIDER_ICONS.default;
  const endpoints = (schema.endpoints || []).slice(0, 5);
  return `
    <div class="provider-card" onclick="openProvider('${schema.provider}')">
      <div class="provider-icon">${icon}</div>
      <div class="provider-name">${schema.name}</div>
      <div class="provider-desc">${schema.description || schema.base_url}</div>
      <div class="provider-endpoints">
        ${endpoints.map(e => `<span class="endpoint-tag">${e}</span>`).join("")}
        ${schema.endpoints.length > 5 ? `<span class="endpoint-tag">+${schema.endpoints.length - 5} more</span>` : ""}
      </div>
    </div>`;
}

async function openProvider(provider) {
  showSection("chat");
  setMode("chat");
  $("chat-input").value = `Show me how to use the ${provider} API`;
  await sendChat();
}

// ── Analytics ─────────────────────────────────────────────────────────────────
async function loadAnalytics() {
  const container = $("analytics-content");
  if (!container) return;
  container.innerHTML = skeletonCards(4);
  try {
    const data = await api("/api/analytics");
    renderAnalyticsDashboard(data, container);
  } catch (err) {
    container.innerHTML = `<p class="text-muted">Failed to load analytics: ${err.message}</p>`;
  }
}

function renderAnalyticsDashboard(data, container) {
  const cr = data.conversion_rate || 0;
  const crColor = cr >= 70 ? "var(--success)" : cr >= 40 ? "var(--warning)" : "var(--error)";

  container.innerHTML = `
    <!-- KPI Row -->
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:20px">
      ${kpiCard("📊", "Total Interactions", data.total_interactions)}
      ${kpiCard("👥", "Unique Sessions",    data.total_sessions)}
      ${kpiCard("✅", "Successful Calls",   data.successful_executions)}
      ${kpiCard("❌", "Failed Calls",       data.failed_executions)}
      ${kpiCard("🎯", "Conversion Rate",    data.conversion_rate + "%", crColor)}
      ${kpiCard("⚡", "Avg Response Time",  data.avg_response_time_ms + "ms")}
    </div>

    <!-- Charts Row -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px">
      <div class="api-card">
        <div class="api-card-header"><span>Daily Activity (14 days)</span></div>
        <div class="api-card-body">
          <canvas id="chart-daily" height="160"></canvas>
        </div>
      </div>
      <div class="api-card">
        <div class="api-card-header"><span>Provider Breakdown</span></div>
        <div class="api-card-body">
          <canvas id="chart-providers" height="160"></canvas>
        </div>
      </div>
    </div>

    <!-- Tables Row -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
      <div class="api-card">
        <div class="api-card-header"><span>Top Endpoints</span></div>
        <div class="api-card-body">
          ${renderTable(["Endpoint","Provider","Calls"], data.endpoint_usage.map(e => [e.endpoint, e.api_provider, e.cnt]))}
        </div>
      </div>
      <div class="api-card">
        <div class="api-card-header"><span>Error Frequency</span></div>
        <div class="api-card-body">
          ${data.error_frequency.length
            ? renderTable(["Error Code","Count"], data.error_frequency.map(e => [e.error_code, e.cnt]))
            : `<p class="text-sm text-muted">No errors recorded 🎉</p>`}
        </div>
      </div>
    </div>
  `;

  // Draw charts
  drawBarChart("chart-daily",
    (data.daily_activity || []).map(d => d.day?.slice(5) || ""),
    (data.daily_activity || []).map(d => d.cnt),
    "Interactions"
  );
  drawDonutChart("chart-providers",
    (data.provider_breakdown || []).map(d => d.api_provider || "unknown"),
    (data.provider_breakdown || []).map(d => d.cnt)
  );
}

function kpiCard(icon, label, value, valueColor = "var(--text)") {
  return `<div class="api-card" style="padding:16px">
    <div style="font-size:1.4rem;margin-bottom:6px">${icon}</div>
    <div class="text-xs text-muted" style="margin-bottom:4px">${label}</div>
    <div style="font-size:1.4rem;font-weight:700;color:${valueColor}">${value ?? 0}</div>
  </div>`;
}

function renderTable(headers, rows) {
  if (!rows.length) return `<p class="text-sm text-muted">No data yet</p>`;
  return `<table class="full-w" style="border-collapse:collapse">
    <thead><tr>${headers.map(h => `<th style="padding:6px 8px;text-align:left;font-size:.75rem;color:var(--text-muted);border-bottom:1px solid var(--border)">${h}</th>`).join("")}</tr></thead>
    <tbody>${rows.map(row => `<tr>${row.map(cell => `<td style="padding:6px 8px;font-size:.8rem;border-bottom:1px solid var(--border);font-family:var(--mono)">${cell ?? ""}</td>`).join("")}</tr>`).join("")}</tbody>
  </table>`;
}

// ── Canvas Charts ─────────────────────────────────────────────────────────────
function drawBarChart(canvasId, labels, values, label) {
  const canvas = $(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const W = canvas.offsetWidth || 300, H = canvas.height || 160;
  canvas.width = W; canvas.height = H;

  const max     = Math.max(...values, 1);
  const pad     = { top: 20, right: 10, bottom: 30, left: 30 };
  const chartW  = W - pad.left - pad.right;
  const chartH  = H - pad.top  - pad.bottom;
  const barW    = labels.length ? (chartW / labels.length) * .7 : 20;
  const gap     = labels.length ? (chartW / labels.length) * .3 : 5;

  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = "#1a1d28";
  ctx.fillRect(0, 0, W, H);

  // Grid lines
  ctx.strokeStyle = "#2a2e3f"; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (chartH / 4) * i;
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
    ctx.fillStyle = "#64748b"; ctx.font = "10px Inter";
    ctx.fillText(Math.round(max - (max / 4) * i), 2, y + 4);
  }

  // Bars
  labels.forEach((lbl, i) => {
    const x    = pad.left + i * (barW + gap);
    const barH = values[i] ? (values[i] / max) * chartH : 0;
    const y    = pad.top + chartH - barH;

    const grad = ctx.createLinearGradient(0, y, 0, y + barH);
    grad.addColorStop(0, "#6366f1"); grad.addColorStop(1, "#4f52c9");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.roundRect?.(x, y, barW, barH, [3, 3, 0, 0]);
    ctx.fill();

    ctx.fillStyle = "#64748b"; ctx.font = "9px Inter"; ctx.textAlign = "center";
    ctx.fillText(lbl, x + barW / 2, H - 4);
  });
}

function drawDonutChart(canvasId, labels, values) {
  const canvas = $(canvasId);
  if (!canvas) return;
  const ctx   = canvas.getContext("2d");
  const W     = canvas.offsetWidth || 300, H = canvas.height || 160;
  canvas.width = W; canvas.height = H;

  const total  = values.reduce((a, b) => a + b, 0) || 1;
  const cx     = W * .4, cy = H / 2, r = Math.min(cx, cy) - 20, inner = r * .55;
  const colors = ["#6366f1", "#22d3ee", "#f59e0b", "#22c55e", "#ef4444", "#a78bfa"];

  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = "#1a1d28"; ctx.fillRect(0, 0, W, H);

  if (!values.length || total === 0) {
    ctx.fillStyle = "#64748b"; ctx.font = "12px Inter"; ctx.textAlign = "center";
    ctx.fillText("No data", cx, cy); return;
  }

  let angle = -Math.PI / 2;
  values.forEach((val, i) => {
    const slice = (val / total) * 2 * Math.PI;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r, angle, angle + slice);
    ctx.closePath();
    ctx.fillStyle = colors[i % colors.length];
    ctx.fill();
    angle += slice;
  });

  // Donut hole
  ctx.beginPath(); ctx.arc(cx, cy, inner, 0, 2 * Math.PI);
  ctx.fillStyle = "#1a1d28"; ctx.fill();
  ctx.fillStyle = "#e2e8f0"; ctx.font = "bold 14px Inter"; ctx.textAlign = "center";
  ctx.fillText(total, cx, cy + 5);

  // Legend
  const legendX = W * .62;
  labels.slice(0, 5).forEach((lbl, i) => {
    const ly = 30 + i * 24;
    ctx.fillStyle = colors[i % colors.length];
    ctx.fillRect(legendX, ly, 12, 12);
    ctx.fillStyle = "#94a3b8"; ctx.font = "11px Inter"; ctx.textAlign = "left";
    ctx.fillText(`${lbl} (${values[i]})`, legendX + 16, ly + 10);
  });
}

// ── Utilities ─────────────────────────────────────────────────────────────────
async function api(url, method = "GET", body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);
  const res  = await fetch(url, opts);
  const data = await res.json().catch(() => ({ error: res.statusText }));
  if (!res.ok && !data.success) {
    throw new Error(data.detail || data.error || `HTTP ${res.status}`);
  }
  return data;
}

function formatText(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br>");
}

function parseMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/^### (.+)$/gm,  "<h3>$1</h3>")
    .replace(/^## (.+)$/gm,   "<h2>$1</h2>")
    .replace(/^# (.+)$/gm,    "<h1>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g,     "<em>$1</em>")
    .replace(/`([^`\n]+)`/g,   "<code>$1</code>")
    .replace(/```[\s\S]*?```/g, m => {
      const inner = m.slice(3, -3).replace(/^[a-z]+\n/, "");
      return `<pre>${inner}</pre>`;
    })
    .replace(/^[-*] (.+)$/gm,  "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
    .replace(/\n\n/g, "</p><p>")
    .replace(/^(?!<[hup])/gm, "")
    .trim();
}

function escapeHtml(str) {
  if (typeof str !== "string") str = JSON.stringify(str, null, 2);
  return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function escapeAttr(str) {
  return str.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function buildCurl(req) {
  if (!req || !req.url) return "";
  const method  = req.method || "GET";
  const headers = Object.entries(req.headers || {})
    .filter(([k]) => k.toLowerCase() !== "authorization")
    .map(([k, v]) => `-H "${k}: ${v}"`).join(" \\\n  ");
  const body    = req.body ? `-d '${JSON.stringify(req.body)}'` : "";
  const params  = Object.keys(req.params || {}).length
    ? "?" + new URLSearchParams(req.params).toString() : "";
  return `curl -X ${method} "${req.url}${params}" \\\n  -H "Authorization: <YOUR_API_KEY>" \\\n  ${headers} \\\n  ${body}`.trim();
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(typeof text === "string" ? text : JSON.stringify(text, null, 2))
    .then(() => toast("Copied to clipboard!", "success"))
    .catch(() => toast("Copy failed", "error"));
}

function copyCurl() {
  if (!STATE.currentRequest) return;
  copyToClipboard(buildCurl(STATE.currentRequest));
}

function autoResize(el) {
  el.style.height = "44px";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

function skeletonCards(n) {
  return Array(n).fill(`<div class="api-card" style="padding:16px">
    <div class="skeleton" style="width:60%;height:16px"></div>
    <div class="skeleton" style="width:80%;height:12px"></div>
    <div class="skeleton" style="width:40%;height:12px"></div>
  </div>`).join("");
}

// ── Integration Modal ─────────────────────────────────────────────────────────
async function sendIntegration(channel) {
  const msg = prompt(`Message to send via ${channel}:`);
  if (!msg) return;
  const subject  = channel === "email" ? prompt("Email subject:") || "DevRelOS" : null;
  const to_email = channel === "email" ? prompt("Recipient email:") : null;

  try {
    const res = await api("/api/integrations/send", "POST", {
      channel, message: msg, subject, to_email, session_id: STATE.sessionId
    });
    if (res.success) toast(`✅ ${channel} message sent!`, "success");
    else             toast(`❌ ${channel} failed: ${res.error}`, "error");
  } catch (err) {
    toast(err.message, "error");
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initSession();
  initVoice();
  showSection("chat");
  setMode("chat");

  // Chat input auto-resize + enter to send
  const chatInput = $("chat-input");
  if (chatInput) {
    chatInput.addEventListener("input",   () => autoResize(chatInput));
    chatInput.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); }
    });
  }

  // Welcome message
  appendMessage("assistant",
    "👋 Welcome to **DevRelOS** — your AI DevRel platform!\n\nTell me what you want to build and I'll generate the exact API request, handle authentication, and let you execute it instantly.\n\n**Try:** \"Charge $50 to a customer\" or \"Send an SMS to +1234567890\"",
    { suggestions: [
      "Charge $50 to a customer",
      "Create a GitHub repository",
      "Send SMS to +1234567890",
      "List all Stripe customers",
    ]}
  );
});
