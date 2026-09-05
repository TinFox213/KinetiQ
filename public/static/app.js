/**
 * KinetiQ Retail Sales & Inventory Copilot — Client Application
 * Communicates with FastAPI backend on Port 8000 via asynchronous fetch.
 */

const API_BASE = window.location.origin;

let currentStoreId = "STORE_01";
let currentTriage = null;
let activeTab = "stockouts";

// Lightweight Markdown to HTML Converter
function formatMarkdown(text) {
  if (!text) return "";
  let html = text
    .replace(/^### (.*$)/gim, "<h3>$1</h3>")
    .replace(/^## (.*$)/gim, "<h2>$1</h2>")
    .replace(/^# (.*$)/gim, "<h1>$1</h1>")
    .replace(/\*\*(.*?)\*\*/gim, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/gim, "<em>$1</em>")
    .replace(/`([^`]+)`/gim, "<code>$1</code>")
    .replace(/\n\n/gim, "<br><br>")
    .replace(/^\s*-\s(.*$)/gim, "<li>$1</li>");

  // Wrap list items in <ul>
  if (html.includes("<li>")) {
    html = html.replace(/(<li>.*?<\/li>)+/gis, (match) => `<ul>${match}</ul>`);
  }
  return html;
}

// Toast Notification
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerHTML = `<span>${type === "success" ? "✅" : "ℹ️"}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

// Initial Bootstrapper
document.addEventListener("DOMContentLoaded", async () => {
  setupEventListeners();
  await loadStores();
  await refreshDashboard();
});

function setupEventListeners() {
  // Store Selector
  const storeSelect = document.getElementById("storeSelect");
  storeSelect.addEventListener("change", (e) => {
    currentStoreId = e.target.value;
    refreshDashboard();
  });

  // Tab Buttons
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      e.target.classList.add("active");
      activeTab = e.target.dataset.tab;
      renderActiveTab();
    });
  });

  // Chat Form
  const chatForm = document.getElementById("chatForm");
  const chatInput = document.getElementById("chatInput");
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = chatInput.value.trim();
    if (!msg) return;
    chatInput.value = "";
    await handleUserMessage(msg);
  });

  // Prompt Chips
  document.querySelectorAll(".chip-btn").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.dataset.prompt;
      if (prompt) handleUserMessage(prompt);
    });
  });

  // Simulation Controls
  const simSlider = document.getElementById("simDiscountSlider");
  const simDiscountVal = document.getElementById("simDiscountVal");
  simSlider.addEventListener("input", (e) => {
    simDiscountVal.textContent = `${e.target.value}%`;
    triggerSimulation();
  });

  const simSkuSelect = document.getElementById("simSkuSelect");
  simSkuSelect.addEventListener("change", () => {
    triggerSimulation();
  });

  const simDurationSelect = document.getElementById("simDurationSelect");
  simDurationSelect.addEventListener("change", () => {
    triggerSimulation();
  });
}

// Load Stores Directory
async function loadStores() {
  try {
    const res = await fetch(`${API_BASE}/api/stores`);
    if (!res.ok) return;
    const stores = await res.json();
    const select = document.getElementById("storeSelect");
    select.innerHTML = "";
    stores.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.store_id;
      opt.textContent = `${s.store_id} — ${s.name} (${s.store_type})`;
      select.appendChild(opt);
    });
    select.value = currentStoreId;
  } catch (err) {
    console.error("Failed to load stores:", err);
  }
}

// Refresh Dashboard Data
async function refreshDashboard() {
  try {
    const res = await fetch(`${API_BASE}/api/triage/today?store_id=${currentStoreId}`);
    if (!res.ok) throw new Error("Failed to fetch triage");
    currentTriage = await res.json();
    renderScorecard(currentTriage);
    renderActiveTab();
    populateSimulatorSkus();
    triggerSimulation();
  } catch (err) {
    console.error("Dashboard refresh error:", err);
    showToast("Error loading morning triage data", "error");
  }
}

// Render Executive Scorecard
function renderScorecard(data) {
  document.getElementById("scoreDate").textContent = data.date || "Today";
  document.getElementById("managerName").textContent = data.manager_name || "Manager";

  // Health Score
  const healthEl = document.getElementById("healthScore");
  healthEl.textContent = `${data.health_score}/100`;
  healthEl.style.color = data.health_score >= 80 ? "var(--accent-emerald)" : data.health_score >= 60 ? "var(--accent-amber)" : "var(--accent-rose)";

  // Cards
  document.getElementById("statActiveSkus").textContent = data.total_active_skus;
  document.getElementById("statHealthySkus").textContent = `${data.healthy_skus_count} healthy`;

  document.getElementById("statStockouts").textContent = data.imminent_stockouts_count;
  document.getElementById("statStockoutsLoss").textContent = `$${data.potential_revenue_loss_at_risk.toLocaleString()} at risk`;

  document.getElementById("statDeadStock").textContent = data.dead_capital_skus_count;
  document.getElementById("statDeadCapital").textContent = `$${data.total_dead_capital_locked.toLocaleString()} locked ($${data.monthly_holding_cost_drag}/mo)`;

  document.getElementById("statTransfers").textContent = data.available_transfers_count;
  document.getElementById("statAnomalies").textContent = `${data.velocity_anomalies_count} demand spikes/drops`;
}

// Render the Active Queue Tab
function renderActiveTab() {
  const container = document.getElementById("queueContainer");
  container.innerHTML = "";

  if (!currentTriage) return;

  if (activeTab === "stockouts") {
    const items = currentTriage.top_imminent_stockouts || [];
    if (items.length === 0) {
      container.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 2rem;">No imminent stockouts detected. All runways healthy.</div>`;
      return;
    }
    items.forEach((item) => {
      const card = document.createElement("div");
      card.className = "queue-card";
      const isCritical = item.urgency_level === "CRITICAL";

      // Check if there is an inter-store transfer candidate for this SKU
      const matchingTransfer = (currentTriage.recommended_transfers || []).find((t) => t.sku_id === item.sku_id);

      card.innerHTML = `
        <div class="queue-card-header">
          <div>
            <div class="item-name">${item.product_name}</div>
            <div class="item-sku">${item.sku_id} &bull; ${item.category}</div>
          </div>
          <span class="pill ${isCritical ? "pill-critical" : "pill-warning"}">${item.urgency_level}: ${item.doi_days}d runway</span>
        </div>
        <div class="metrics-row">
          <span>On Hand: <strong class="metric-highlight">${item.on_hand} units</strong></span>
          <span>Velocity: <strong class="metric-highlight">${item.velocity_7d} u/day</strong></span>
          <span>Lead Time: <strong class="metric-highlight">${item.lead_time_days} days</strong></span>
          <span>Deficit: <strong class="metric-highlight">${item.deficit_units} units</strong></span>
        </div>
        <div class="action-row">
          <span style="color: var(--text-muted); font-size: 0.75rem;">Projected Stockout: <strong>${item.projected_stockout_date}</strong></span>
          <div style="display: flex; gap: 0.5rem;">
            ${matchingTransfer ? `
              <button class="btn-action" onclick="approveTransfer('${matchingTransfer.manifest_id}', '${matchingTransfer.from_store_id}', '${matchingTransfer.to_store_id}', '${matchingTransfer.sku_id}', ${matchingTransfer.quantity})">
                🔄 Transfer ${matchingTransfer.quantity} from ${matchingTransfer.from_store_id} (+$${matchingTransfer.net_savings})
              </button>
            ` : `
              <button class="btn-action btn-secondary" onclick="triggerAsk('Reorder recommendation for ${item.sku_id}')">
                📦 Order ${item.recommended_order_qty} Units
              </button>
            `}
          </div>
        </div>
      `;
      container.appendChild(card);
    });
  } else if (activeTab === "deadstock") {
    const items = currentTriage.top_dead_stock_items || [];
    if (items.length === 0) {
      container.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 2rem;">No dead capital detected.</div>`;
      return;
    }
    items.forEach((item) => {
      const card = document.createElement("div");
      card.className = "queue-card";
      card.innerHTML = `
        <div class="queue-card-header">
          <div>
            <div class="item-name">${item.product_name}</div>
            <div class="item-sku">${item.sku_id} &bull; ${item.category}</div>
          </div>
          <span class="pill pill-warning">${item.days_since_last_sale} Days Idle</span>
        </div>
        <div class="metrics-row">
          <span>Stock: <strong class="metric-highlight">${item.on_hand} units</strong></span>
          <span>Cost Price: <strong class="metric-highlight">$${item.unit_cost}</strong></span>
          <span>Locked Cash: <strong class="metric-highlight" style="color: var(--accent-amber);">$${item.locked_capital}</strong></span>
          <span>Holding Drag: <strong class="metric-highlight">$${item.monthly_holding_cost_drag}/mo</strong></span>
        </div>
        <div class="action-row">
          <span style="color: var(--text-muted); font-size: 0.75rem;">${item.recommended_action}</span>
          <button class="btn-action btn-secondary" onclick="selectForSimulation('${item.sku_id}', ${item.suggested_discount_pct})">
            📉 Simulate -${item.suggested_discount_pct}%
          </button>
        </div>
      `;
      container.appendChild(card);
    });
  } else if (activeTab === "anomalies") {
    const items = currentTriage.top_velocity_anomalies || [];
    const phantoms = currentTriage.phantom_inventory_alerts || [];
    if (items.length === 0 && phantoms.length === 0) {
      container.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 2rem;">No unusual velocity shifts detected.</div>`;
      return;
    }

    phantoms.forEach((p) => {
      const card = document.createElement("div");
      card.className = "queue-card";
      card.style.borderColor = "rgba(244, 63, 94, 0.4)";
      card.innerHTML = `
        <div class="queue-card-header">
          <div>
            <div class="item-name">👻 ${p.product_name} (Phantom Stock Alert)</div>
            <div class="item-sku">${p.sku_id} &bull; ${p.category}</div>
          </div>
          <span class="pill pill-critical">Audit Required</span>
        </div>
        <div style="font-size: 0.8rem; color: #fca5a5;">${p.rationale}</div>
        <div class="action-row">
          <span style="color: var(--text-muted); font-size: 0.75rem;">System On Hand: ${p.on_hand} units</span>
          <button class="btn-action" onclick="showToast('Shelf audit ticket dispatched to store staff', 'success')">
            📋 Dispatch Shelf Audit
          </button>
        </div>
      `;
      container.appendChild(card);
    });

    items.forEach((a) => {
      const card = document.createElement("div");
      card.className = "queue-card";
      const isSpike = a.anomaly_type === "SPIKE";
      card.innerHTML = `
        <div class="queue-card-header">
          <div>
            <div class="item-name">${isSpike ? "📈" : "📉"} ${a.product_name}</div>
            <div class="item-sku">${a.sku_id} &bull; ${a.category}</div>
          </div>
          <span class="pill ${isSpike ? "pill-info" : "pill-warning"}">${a.anomaly_type} (Z=${a.z_score})</span>
        </div>
        <div class="metrics-row">
          <span>Yesterday: <strong class="metric-highlight">${a.yesterday_sales} units</strong></span>
          <span>14d Baseline: <strong class="metric-highlight">${a.baseline_mean_14d} units</strong></span>
          <span>Shift: <strong class="metric-highlight">${a.percent_change_vs_baseline > 0 ? "+" : ""}${a.percent_change_vs_baseline}%</strong></span>
          <span>On Hand: <strong class="metric-highlight">${a.on_hand}</strong></span>
        </div>
        <div class="action-row">
          <span style="color: var(--text-muted); font-size: 0.75rem;">${a.recommended_action}</span>
          <button class="btn-action btn-secondary" onclick="triggerAsk('Investigate anomaly for ${a.sku_id}')">
            🔍 Investigate
          </button>
        </div>
      `;
      container.appendChild(card);
    });
  } else if (activeTab === "transfers") {
    const items = currentTriage.recommended_transfers || [];
    if (items.length === 0) {
      container.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 2rem;">No network transfer arbitrage opportunities available today.</div>`;
      return;
    }
    items.forEach((t) => {
      const card = document.createElement("div");
      card.className = "queue-card";
      card.innerHTML = `
        <div class="queue-card-header">
          <div>
            <div class="item-name">🚚 ${t.product_name}</div>
            <div class="item-sku">${t.manifest_id} &bull; ${t.sku_id}</div>
          </div>
          <span class="pill pill-success">+${t.net_savings} Net Profit</span>
        </div>
        <div class="metrics-row">
          <span>Route: <strong class="metric-highlight">${t.from_store_id} &rarr; ${t.to_store_id}</strong></span>
          <span>Quantity: <strong class="metric-highlight">${t.quantity} units</strong></span>
          <span>Transit: <strong class="metric-highlight">${t.estimated_transit_hours} hrs</strong></span>
          <span>Courier Cost: <strong class="metric-highlight">$${t.estimated_courier_cost}</strong></span>
        </div>
        <div class="action-row">
          <span style="color: var(--text-muted); font-size: 0.75rem;">Source store retains ${t.source_remaining_runway_days}d safe buffer</span>
          <button class="btn-action" onclick="approveTransfer('${t.manifest_id}', '${t.from_store_id}', '${t.to_store_id}', '${t.sku_id}', ${t.quantity})">
            ✅ Approve Stock Transfer Note
          </button>
        </div>
      `;
      container.appendChild(card);
    });
  }
}

// Inter-Store Transfer Approval
window.approveTransfer = async function (manifestId, fromStore, toStore, skuId, qty) {
  try {
    const res = await fetch(`${API_BASE}/api/actions/transfer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        manifest_id: manifestId,
        from_store_id: fromStore,
        to_store_id: toStore,
        sku_id: skuId,
        quantity: qty,
      }),
    });
    if (!res.ok) throw new Error("Failed to commit transfer");
    showToast(`Transfer Note ${manifestId} approved and recorded! Courier scheduled.`, "success");
    await refreshDashboard();
  } catch (err) {
    console.error("Transfer commit error:", err);
    showToast("Failed to approve transfer.", "error");
  }
};

// Conversational Copilot
async function handleUserMessage(message) {
  const history = document.getElementById("chatHistory");

  // Append user message
  const userMsgEl = document.createElement("div");
  userMsgEl.className = "chat-msg user";
  userMsgEl.innerHTML = `<div class="msg-bubble">${message}</div>`;
  history.appendChild(userMsgEl);
  history.scrollTop = history.scrollHeight;

  // Append loading indicator
  const loadingEl = document.createElement("div");
  loadingEl.className = "chat-msg copilot";
  loadingEl.innerHTML = `<div class="msg-bubble" style="color: var(--text-muted);"><span class="status-dot" style="display:inline-block; margin-right:6px;"></span>Consulting deterministic kernel & Gemini 2.5 Flash...</div>`;
  history.appendChild(loadingEl);
  history.scrollTop = history.scrollHeight;

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message, store_id: currentStoreId }),
    });
    const data = await res.json();
    loadingEl.remove();

    const copilotMsgEl = document.createElement("div");
    copilotMsgEl.className = "chat-msg copilot";
    const formattedBody = formatMarkdown(data.response);
    const sourceLabel = data.source === "gemini-2.5-flash" ? "Google Gemini 2.5 Flash" : data.source === "epistemic-refusal" ? "Epistemic Guardrail" : "Deterministic Analytics Engine";

    copilotMsgEl.innerHTML = `
      <div class="msg-bubble">
        ${formattedBody}
      </div>
      <div class="msg-source-tag">
        <span>⚡ Verified Source: ${sourceLabel}</span>
        ${data.tools_executed && data.tools_executed.length > 0 ? `<span>&bull; Tools: [${data.tools_executed.join(", ")}]</span>` : ""}
      </div>
    `;
    history.appendChild(copilotMsgEl);
    history.scrollTop = history.scrollHeight;
  } catch (err) {
    loadingEl.remove();
    console.error("Chat error:", err);
    showToast("Error communicating with Copilot", "error");
  }
}

window.triggerAsk = function (msg) {
  handleUserMessage(msg);
};

// Simulation Controls
function populateSimulatorSkus() {
  const select = document.getElementById("simSkuSelect");
  if (select.children.length > 0) return;

  const sampleSkus = [
    { id: "SKU_1080", name: "SKU_1080: Truffle Vinegar (Dead Stock)" },
    { id: "SKU_1020", name: "SKU_1020: Organic A2 Milk (Fast Moving)" },
    { id: "SKU_1001", name: "SKU_1001: Classic White Bread (Staple)" },
    { id: "SKU_1042", name: "SKU_1042: Greek Yogurt (Perishable)" },
    { id: "SKU_1050", name: "SKU_1050: Roasted Makhana (Snacks)" },
  ];

  sampleSkus.forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s.id;
    opt.textContent = s.name;
    select.appendChild(opt);
  });
}

window.selectForSimulation = function (skuId, discount) {
  const skuSelect = document.getElementById("simSkuSelect");
  skuSelect.value = skuId;
  const slider = document.getElementById("simDiscountSlider");
  slider.value = discount;
  document.getElementById("simDiscountVal").textContent = `${discount}%`;
  triggerSimulation();
  document.getElementById("simulatorSection").scrollIntoView({ behavior: "smooth" });
};

async function triggerSimulation() {
  const skuId = document.getElementById("simSkuSelect").value || "SKU_1080";
  const discount = parseFloat(document.getElementById("simDiscountSlider").value) || 20.0;
  const duration = parseInt(document.getElementById("simDurationSelect").value) || 14;

  try {
    const res = await fetch(`${API_BASE}/api/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sku_id: skuId,
        store_id: currentStoreId,
        discount_percent: discount,
        duration_days: duration,
      }),
    });
    if (!res.ok) return;
    const sim = await res.json();
    renderSimulationResults(sim);
  } catch (err) {
    console.error("Simulation error:", err);
  }
}

function renderSimulationResults(sim) {
  document.getElementById("simBasePrice").textContent = `$${sim.base_retail_price}`;
  document.getElementById("simNewPrice").textContent = `$${sim.discounted_price}`;
  document.getElementById("simDemandLift").textContent = `+${sim.velocity_lift_percent}%`;
  document.getElementById("simNewVelocity").textContent = `${sim.projected_velocity} u/day`;

  document.getElementById("simRunwayDays").textContent = `${sim.projected_clearance_days} days`;
  document.getElementById("simOldRunway").textContent = `vs ${sim.base_clearance_days} days baseline`;

  const profitEl = document.getElementById("simProfitDelta");
  profitEl.textContent = `${sim.gross_profit_delta >= 0 ? "+" : ""}$${sim.gross_profit_delta}`;
  profitEl.style.color = sim.gross_profit_delta >= 0 ? "var(--accent-emerald)" : "var(--accent-rose)";

  const revEl = document.getElementById("simRevenueDelta");
  revEl.textContent = `${sim.revenue_delta >= 0 ? "+" : ""}$${sim.revenue_delta}`;

  // Risk Banner
  const banner = document.getElementById("simRiskBanner");
  const isHigh = sim.inventory_exhaustion_risk.includes("HIGH");
  banner.className = `risk-banner ${isHigh ? "risk-high" : "risk-low"}`;
  banner.innerHTML = `<span>${isHigh ? "🚨" : "🛡️"}</span> <span>${sim.inventory_exhaustion_risk}</span>`;
}
